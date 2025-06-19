from __future__ import annotations

import atexit
import threading
import platform
import sys
import os
import time
import psutil
from typing import Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry import context as context_api
import requests


from aliyah_sdk.config import Config
from aliyah_sdk.exceptions import AaliyahClientNotInitializedException
from aliyah_sdk.logging import logger, setup_print_logger
from aliyah_sdk.sdk.processors import InternalSpanProcessor
from aliyah_sdk.sdk.types import TracingConfig
from aliyah_sdk.semconv import ResourceAttributes

# No need to create shortcuts since we're using our own ResourceAttributes class now

class ShutdownMonitoringProcessor(BatchSpanProcessor):
    """
    Custom span processor that monitors HTTP responses for shutdown signals.
    This wraps the existing OTLP exporter to intercept responses.
    """
    
    def __init__(self, span_exporter, **kwargs):
        try:
            # Call parent constructor with the span_exporter
            super().__init__(span_exporter, **kwargs)
            self._shutdown_detected = False
            
            # Store reference to the exporter
            self.span_exporter = span_exporter
            self._original_export = span_exporter.export
            
            # Wrap the exporter's export method
            span_exporter.export = self._export_with_monitoring
            
            logger.debug("ShutdownMonitoringProcessor initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing ShutdownMonitoringProcessor: {e}")
            raise
    
    def _export_with_monitoring(self, spans):
        """Export spans and monitor response for shutdown signals"""
        try:
            # Call the original export method
            result = self._original_export(spans)
            
            # Try to access the HTTP response if available
            # This is a bit hacky but works with the current OTLP exporter structure
            if hasattr(self.span_exporter, '_session'):
                session = self.span_exporter._session
                
                # Check if there's a recent response
                if hasattr(session, 'last_response') and session.last_response:
                    response = session.last_response
                    self._check_response_for_shutdown(response)
                
                # Alternative: monkey patch the session to capture responses
                elif not hasattr(session, '_shutdown_monitoring_patched'):
                    self._patch_session_for_monitoring(session)
            
            return result
            
        except Exception as e:
            logger.debug(f"Error in shutdown monitoring: {e}")
            return self._original_export(spans)
    
    def _patch_session_for_monitoring(self, session):
        """Patch the requests session to capture responses"""
        try:
            original_request = session.request
            
            def monitored_request(*args, **kwargs):
                response = original_request(*args, **kwargs)
                session.last_response = response
                self._check_response_for_shutdown(response)
                return response
            
            session.request = monitored_request
            session._shutdown_monitoring_patched = True
            
        except Exception as e:
            logger.debug(f"Error patching session: {e}")
    
    def _check_response_for_shutdown(self, response):
        """Check HTTP response for shutdown signals"""
        try:
            if not hasattr(response, 'headers'):
                return
                
            agent_status = response.headers.get('X-Agent-Status', '').lower()
            agent_action = response.headers.get('X-Agent-Action', '').lower()
            
            # Check for shutdown signals
            if (agent_status == 'shutdown' or 
                agent_action == 'terminate' or 
                response.status_code == 202):
                
                if not self._shutdown_detected:
                    self._shutdown_detected = True
                    logger.critical("🛑 AGENT SHUTDOWN SIGNAL RECEIVED FROM BACKEND")
                    
                    # Trigger immediate shutdown in a separate thread to avoid blocking
                    import threading
                    shutdown_thread = threading.Thread(
                        target=self._handle_shutdown_signal,
                        daemon=True
                    )
                    shutdown_thread.start()
                    
        except Exception as e:
            logger.debug(f"Error checking response for shutdown: {e}")
    
    def _handle_shutdown_signal(self):
        """Handle shutdown signal from backend"""
        try:
            # End any active sessions immediately
            self._emergency_cleanup()
            
            # Force terminate the application
            logger.critical("🛑 TERMINATING APPLICATION DUE TO BACKEND SHUTDOWN SIGNAL")
            time.sleep(0.1)  # Brief moment for logs
            os._exit(1)  # Immediate termination
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            os._exit(1)  # Force exit even if cleanup fails
    
    def _emergency_cleanup(self):
        """Emergency cleanup before shutdown"""
        try:
            # Import here to avoid circular imports
            import aliyah_sdk.client.client as client_module
            
            if hasattr(client_module, '_active_session') and client_module._active_session:
                from aliyah_sdk.sessions import end_session
                end_session(
                    client_module._active_session,
                    end_state="Shutdown",
                    end_state_reason="Backend shutdown signal received"
                )
        except Exception as e:
            logger.error(f"Error during emergency cleanup: {e}")

def get_imported_libraries():
    """
    Get the top-level imported libraries in the current script.

    Returns:
        list: List of imported libraries
    """
    user_libs = []

    builtin_modules = {
        "builtins",
        "sys",
        "os",
        "_thread",
        "abc",
        "io",
        "re",
        "types",
        "collections",
        "enum",
        "math",
        "datetime",
        "time",
        "warnings",
    }

    try:
        main_module = sys.modules.get("__main__")
        if main_module and hasattr(main_module, "__dict__"):
            for name, obj in main_module.__dict__.items():
                if isinstance(obj, type(sys)) and hasattr(obj, "__name__"):
                    mod_name = obj.__name__.split(".")[0]
                    if mod_name and not mod_name.startswith("_") and mod_name not in builtin_modules:
                        user_libs.append(mod_name)
    except Exception as e:
        logger.debug(f"Error getting imports: {e}")

    return user_libs


def get_system_stats():
    """
    Get basic system stats including CPU and memory information.

    Returns:
        dict: Dictionary with system information
    """
    system_info = {
        ResourceAttributes.HOST_MACHINE: platform.machine(),
        ResourceAttributes.HOST_NAME: platform.node(),
        ResourceAttributes.HOST_NODE: platform.node(),
        ResourceAttributes.HOST_PROCESSOR: platform.processor(),
        ResourceAttributes.HOST_SYSTEM: platform.system(),
        ResourceAttributes.HOST_VERSION: platform.version(),
        ResourceAttributes.HOST_OS_RELEASE: platform.release(),
    }

    # Add CPU stats
    try:
        system_info[ResourceAttributes.CPU_COUNT] = os.cpu_count() or 0
        system_info[ResourceAttributes.CPU_PERCENT] = psutil.cpu_percent(interval=0.1)
    except Exception as e:
        logger.debug(f"Error getting CPU stats: {e}")

    # Add memory stats
    try:
        memory = psutil.virtual_memory()
        system_info[ResourceAttributes.MEMORY_TOTAL] = memory.total
        system_info[ResourceAttributes.MEMORY_AVAILABLE] = memory.available
        system_info[ResourceAttributes.MEMORY_USED] = memory.used
        system_info[ResourceAttributes.MEMORY_PERCENT] = memory.percent
    except Exception as e:
        logger.debug(f"Error getting memory stats: {e}")

    return system_info


def setup_telemetry(
    service_name: str = "aaliyah",
    project_id: Optional[str] = None,
    exporter_endpoint: str = Config.EXPORTER_ENDPOINT,
    metrics_endpoint: str = Config.METRICS_ENDPOINT,
    max_queue_size: int = Config.MAX_QUEUE_SIZE,
    max_wait_time: int = Config.MAX_WAIT_TIME, 
    export_flush_interval: int = Config.EXPORT_FLUSH_INTERVAL,
    jwt: Optional[str] = None,
    agent_id: Optional[int] = None,     # ADD THIS
    agent_name: Optional[str] = None,   # ADD THIS
) -> tuple[TracerProvider, MeterProvider]:
    """Setup telemetry with enhanced monitoring"""
    
    # Create resource attributes dictionary
    resource_attrs = {ResourceAttributes.SERVICE_NAME: service_name}

    if project_id:
        resource_attrs[ResourceAttributes.PROJECT_ID] = project_id
        logger.debug(f"Including project_id in resource attributes: {project_id}")

    if agent_id is not None:
        resource_attrs["agent.id"] = str(agent_id)
        logger.debug(f"Including agent_id in resource attributes: {agent_id}")
        print(f"DEBUG setup_telemetry: Adding agent.id to resource: {agent_id}")

    if agent_name:
        resource_attrs["agent.name"] = agent_name
        logger.debug(f"Including agent_name in resource attributes: {agent_name}")
        print(f"DEBUG setup_telemetry: Adding agent.name to resource: {agent_name}")

    # Add system information
    system_stats = get_system_stats()
    resource_attrs.update(system_stats)

    # Add imported libraries
    imported_libraries = get_imported_libraries()
    resource_attrs[ResourceAttributes.IMPORTED_LIBRARIES] = imported_libraries

    resource = Resource(resource_attrs)
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    try:
        # Use regular OTLP exporter
        logger.debug(f"Creating OTLP exporter for endpoint: {exporter_endpoint}")
        exporter = OTLPSpanExporter(
            endpoint=exporter_endpoint, 
            headers={"X-API-Key": jwt} if jwt else {}
        )
        logger.debug("OTLP exporter created successfully")

        # Use enhanced processor that monitors responses
        logger.debug("Creating ShutdownMonitoringProcessor...")
        processor = ShutdownMonitoringProcessor(
            exporter,
            max_export_batch_size=max_queue_size,
            schedule_delay_millis=export_flush_interval,
        )
        logger.debug("ShutdownMonitoringProcessor created successfully")
        
        provider.add_span_processor(processor)
        provider.add_span_processor(InternalSpanProcessor())
        
    except Exception as e:
        logger.error(f"Error setting up shutdown monitoring processor: {e}")
        # Fallback to regular processor if monitoring fails
        logger.warning("Falling back to regular BatchSpanProcessor without shutdown monitoring")
        
        exporter = OTLPSpanExporter(
            endpoint=exporter_endpoint, 
            headers={"X-API-Key": jwt} if jwt else {}
        )
        
        processor = BatchSpanProcessor(
            exporter,
            max_export_batch_size=max_queue_size,
            schedule_delay_millis=export_flush_interval,
        )
        provider.add_span_processor(processor)
        provider.add_span_processor(InternalSpanProcessor())

    # Setup metrics (regular OTLP exporter)
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=metrics_endpoint, headers={"X-API-Key": jwt} if jwt else {})
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    setup_print_logger()
    context_api.get_current()
    logger.debug("Telemetry system initialized with shutdown monitoring")

    return provider, meter_provider


class TracingCore:
    """
    Central component for tracing in Aaliyah.

    This class manages the creation, processing, and export of spans.
    It handles provider management, span creation, and context propagation.
    """

    _instance: Optional[TracingCore] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> TracingCore:
        """Get the singleton instance of TracingCore."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance


    def __init__(self):
        """Initialize the tracing core."""
        print("DEBUG TracingCore.__init__: Start") # Debug print
        self._provider = None
        self._meter_provider = None # Also store meter provider
        self._initialized = False
        self._config: Optional[Config] = None # Store the Config *instance*

        # Don't register atexit here, Client does it once for shutdown()
        # atexit.register(self.shutdown)
        print("DEBUG TracingCore.__init__: Finish") # Debug print


    def initialize(self, config_instance: Config, jwt: Optional[str] = None, project_id: Optional[str] = None, agent_id: Optional[int] = None, agent_name: Optional[str] = None):
        """
        Initialize the tracing core with the given configuration instance.
        """
        
        if self._initialized:
        
            return

        with self._lock:
            if self._initialized:
         
                return

           
            if hasattr(config_instance, 'api_key'):
                print(f"DEBUG TracingCore.initialize: config_instance.api_key type: {type(config_instance.api_key)}")
            
            if hasattr(config_instance, 'exporter_endpoint'):
                print(f"DEBUG TracingCore.initialize: config_instance.exporter_endpoint: '{config_instance.exporter_endpoint}'")

            self._config = config_instance

            # Use attributes from the config instance for setup_telemetry
            service_name = getattr(config_instance, 'service_name', 'aliyah')
            exporter_endpoint = getattr(config_instance, 'exporter_endpoint', Config.EXPORTER_ENDPOINT)
            metrics_endpoint = getattr(config_instance, 'metrics_endpoint', Config.METRICS_ENDPOINT)
            max_queue_size = getattr(config_instance, 'max_queue_size', Config.MAX_QUEUE_SIZE)
            max_wait_time = getattr(config_instance, 'max_wait_time', Config.MAX_WAIT_TIME)
            export_flush_interval = getattr(config_instance, 'export_flush_interval', Config.EXPORT_FLUSH_INTERVAL)


            self._provider, self._meter_provider = setup_telemetry(
                service_name=service_name,
                project_id=project_id,
                exporter_endpoint=exporter_endpoint,
                metrics_endpoint=metrics_endpoint,
                max_queue_size=max_queue_size,
                max_wait_time=max_wait_time,
                export_flush_interval=export_flush_interval,
                jwt=jwt,
                agent_id=agent_id,
                agent_name=agent_name
            )

            # 🔥 NEW: Enable instrumentors if instrument_llm_calls is True
            if getattr(config_instance, 'instrument_llm_calls', False):
                
                self._enable_llm_instrumentors()
            else:
                print("DEBUG TracingCore.initialize: instrument_llm_calls=False, skipping instrumentors")

            self._initialized = True
            

    def _enable_llm_instrumentors(self):
        """Enable LLM framework instrumentors when instrument_llm_calls=True."""
        
        # List of instrumentors to try enabling (order matters - Karo first for smart detection)
        instrumentors_to_enable = [
            # Karo framework instrumentor (highest priority - provides smart provider detection)
            ("aliyah_sdk.instrumentation.karo", "KaroInstrumentor"),
            # Direct LLM provider instrumentors (fallback for non-Karo usage)
            ("opentelemetry.instrumentation.openai", "OpenAIInstrumentor"),
            ("opentelemetry.instrumentation.anthropic", "AnthropicInstrumentor"),
            ("opentelemetry.instrumentation.google_generativeai", "GoogleGenerativeAIInstrumentor"),
        ]
        
        enabled_count = 0
        
        for module_name, class_name in instrumentors_to_enable:
            try:
                # Dynamic import of the instrumentor
                module = __import__(module_name, fromlist=[class_name])
                instrumentor_class = getattr(module, class_name)
                instrumentor = instrumentor_class()
                
                # Check if already instrumented
                if not instrumentor.is_instrumented_by_opentelemetry:
                    instrumentor.instrument(
                        tracer_provider=self._provider,
                        meter_provider=self._meter_provider
                    )
                    provider_name = class_name.replace("Instrumentor", "")
                    
                    logger.debug(f"Successfully enabled {provider_name} instrumentor")
                    enabled_count += 1
                else:
                    provider_name = class_name.replace("Instrumentor", "")
                    
                    logger.debug(f"{provider_name} instrumentor was already enabled")
                    
            except ImportError:
                provider_name = class_name.replace("Instrumentor", "")
                
                logger.debug(f"{provider_name} instrumentation package not found")
            except Exception as e:
                provider_name = class_name.replace("Instrumentor", "")
                
                logger.warning(f"Failed to enable {provider_name} instrumentation: {e}")
        
        if enabled_count > 0:
            
            logger.info(f"Successfully enabled {enabled_count} LLM instrumentors")
        else:

            logger.warning("No LLM instrumentors were enabled - check package installations")


    @property
    def initialized(self) -> bool:
        """Check if the tracing core is initialized."""
        return self._initialized

    @property
    def config(self) -> Config:
        """Get the tracing configuration instance."""
        if self._config is None:
             # This shouldn't happen if initialized is True, but add check
             raise AaliyahClientNotInitializedException("Tracing core configuration not set.")
        return self._config

    def shutdown(self) -> None:
        """Shutdown the tracing core."""
       
        with self._lock:
            if not self._initialized or self._config is None:
                
                return
            
            self._provider._active_span_processor.force_flush(self._config.max_wait_time) # type: ignore

            
            if self._provider:
                try:
                    self._provider.shutdown()
                    self._provider = None # Clear reference
                except Exception as e:
                    logger.warning(f"Error shutting down provider: {e}")

            
            if self._meter_provider:
                 try:
                      self._meter_provider.shutdown()
                      self._meter_provider = None # Clear reference
                 except Exception as e:
                      logger.warning(f"Error shutting down meter provider: {e}")


            self._initialized = False
            

            

    @classmethod
    def initialize_from_config(cls, config_instance: Config, **kwargs):
        """
        Initialize the tracing core from a Config *instance*.
        """
        instance = cls.get_instance()

        # Ensure config_instance is indeed a Config object
        if not isinstance(config_instance, Config):
            logger.error(f"TracingCore.initialize_from_config: Received config of type {type(config_instance)}, expected Config.")
            raise TypeError(f"Expected config to be an instance of Config, but received {type(config_instance)}")

        # Call the instance initialize method, passing the config instance and kwargs
        instance.initialize(config_instance, **kwargs)  # This will now pass agent_id and agent_name

    def get_tracer(self, name: str = "aaliyah") -> trace.Tracer:
        """
        Get a tracer with the given name.

        Args:
            name: Name of the tracer

        Returns:
            A tracer with the given name
        """
        if not self._initialized:
            raise AaliyahClientNotInitializedException

        return trace.get_tracer(name)

    # @classmethod
    # def initialize_from_config(cls, config, **kwargs):
    #     """
    #     Initialize the tracing core from a configuration object.

    #     Args:
    #         config: Configuration object (dict or object with dict method)
    #         **kwargs: Additional keyword arguments to pass to initialize
    #     """
    #     instance = cls.get_instance()

    #     # Extract tracing-specific configuration
    #     # For TracingConfig, we can directly pass it to initialize
    #     if isinstance(config, dict):
    #         # If it's already a dict (TracingConfig), use it directly
    #         tracing_kwargs = config.copy()
    #     else:
    #         # For backward compatibility with old Config object
    #         # Extract tracing-specific configuration from the Config object
    #         # Use getattr with default values to ensure we don't pass None for required fields
    #         tracing_kwargs = {
    #             k: v
    #             for k, v in {
    #                 "exporter": getattr(config, "exporter", None),
    #                 "processor": getattr(config, "processor", None),
    #                 "exporter_endpoint": getattr(config, "exporter_endpoint", None),
    #                 "max_queue_size": getattr(config, "max_queue_size", 512),
    #                 "max_wait_time": getattr(config, "max_wait_time", 5000),
    #                 "export_flush_interval": getattr(config, "export_flush_interval", 1000),
    #                 "api_key": getattr(config, "api_key", None),
    #                 "project_id": getattr(config, "project_id", None),
    #                 "endpoint": getattr(config, "endpoint", None),
    #             }.items()
    #             if v is not None
    #         }
    #     # Update with any additional kwargs
    #     tracing_kwargs.update(kwargs)

    #     # Initialize with the extracted configuration
    #     instance.initialize(**tracing_kwargs)

    #     # Span types are registered in the constructor
    #     # No need to register them here anymore


