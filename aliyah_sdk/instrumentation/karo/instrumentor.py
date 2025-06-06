"""
Karo Agent Framework Instrumentation Module for Ops.

This module provides the main instrumentor class and wrapping functions for Karo.
It traces agents, tools, and memory operations.
"""

from typing import Collection, List, Optional, Any, Tuple, Dict
import logging
import time
from opentelemetry import trace
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer, SpanKind, Tracer
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.metrics import get_meter, Histogram, Counter, Meter
from wrapt import wrap_function_wrapper, ObjectProxy # Import ObjectProxy for potential stream wrappers

from aliyah_sdk.logging import logger
from aliyah_sdk.instrumentation.common.wrappers import WrapConfig, wrap, unwrap # Keep generic wrap/unwrap for reference
from aliyah_sdk.instrumentation.karo import LIBRARY_NAME, LIBRARY_VERSION # Use instrumentation's version info
from aliyah_sdk.instrumentation.karo.attributes import (
    get_agent_run_attributes,
    get_tool_run_attributes,
    get_memory_add_attributes,
    get_memory_query_attributes,
    get_provider_generate_attributes,
    get_common_instrumentation_attributes # Keep for consistency if needed
)
from aliyah_sdk.semconv import (
    SpanAttributes,
    AaliyahSpanKindValues,
    Meters,
    CoreAttributes,
    ToolAttributes # For tool status attribute
)

logger = logging.getLogger(__name__)

# Ensure Karo is importable before defining wrapper targets
try:
    from karo.core.base_agent import BaseAgent, AgentErrorSchema
    from karo.tools.base_tool import BaseTool, BaseToolOutputSchema # Import BaseToolOutputSchema for success status
    from karo.memory.memory_manager import MemoryManager
    from karo.providers.base_provider import BaseProvider
    KARO_AVAILABLE = True
except ImportError:
    logger.warning("Karo framework not found. Karo instrumentation will be disabled.")
    KARO_AVAILABLE = False

# Define methods to wrap IF Karo is available
# Note: We won't use the generic `wrap` helper for all of these anymore
# because the wrappers need to accept metrics. We'll use wrap_function_wrapper
# directly with wrapper factories that accept metrics.
if KARO_AVAILABLE:
    # This list is for reference and potential future use with the generic `wrap` helper
    # if metrics didn't need to be passed, or if we modify `wrap` to accept metrics.
    # For now, specific wrappers are defined below.
    WRAPPED_METHOD_CONFIGS: List[WrapConfig] = [
        WrapConfig(
            trace_name="karo.agent.run",
            package="karo.core.base_agent",
            class_name="BaseAgent",
            method_name="run",
            handler=get_agent_run_attributes,
            span_kind=SpanKind.INTERNAL
        ),
        WrapConfig(
            trace_name="karo.tool.run",
            package="karo.tools.base_tool",
            class_name="BaseTool",
            method_name="run",
            handler=get_tool_run_attributes,
            span_kind=SpanKind.CLIENT
        ),
        WrapConfig(
            trace_name="karo.memory.add",
            package="karo.memory.memory_manager",
            class_name="MemoryManager",
            method_name="add_memory",
            handler=get_memory_add_attributes,
            span_kind=SpanKind.CLIENT
        ),
         WrapConfig(
            trace_name="karo.memory.query",
            package="karo.memory.memory_manager",
            class_name="MemoryManager",
            method_name="retrieve_relevant_memories",
            handler=get_memory_query_attributes,
            span_kind=SpanKind.CLIENT
        ),
        WrapConfig(
            trace_name="karo.provider.generate_response",
            package="karo.providers.base_provider",
            class_name="BaseProvider",
            method_name="generate_response",
            handler=get_provider_generate_attributes,
            span_kind=SpanKind.CLIENT
        ),
        # TODO: If specific providers *within Karo* had streaming methods (like `AnthropicProvider._stream`),
        # you would add specific WrapConfig entries here for those methods and implement custom wrappers
        # and attribute handlers similar to how AgentOps handles streaming in its built-in instrumentors.
        # Example (commented out as these methods don't exist in the provided Karo code):
        # WrapConfig(
        #     trace_name="karo.provider.anthropic.stream",
        #     package="karo.providers.anthropic_provider",
        #     class_name="AnthropicProvider",
        #     method_name="_stream_messages", # Example internal streaming method
        #     handler=get_anthropic_stream_attributes, # You would need to implement this
        #     is_async=True, # Or False depending on the method
        #     span_kind=SpanKind.CLIENT
        # ),
    ]
else:
     WRAPPED_METHOD_CONFIGS = [] # No methods to wrap if Karo isn't available


class KaroInstrumentor(BaseInstrumentor):
    """
    AgentOps Instrumentor for the Karo Agent Framework.

    This instrumentor provides automatic tracing for Karo agents, tools,
    and memory interactions using OpenTelemetry.
    """

    _instrumented_methods = [] # Keep track of what was successfully instrumented
    _enabled_instrumentors = []  # Track which instrumentors enabled

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        return [f"{LIBRARY_NAME} >= 0.1.0"] # Assuming a minimum version

    def _instrument(self, **kwargs):
        """Instrument the Karo framework."""
        if not KARO_AVAILABLE:
            logger.warning("Karo framework not found. Instrumentation skipped.")
            return
        
        # Auto-enable provider instrumentors first
        self._auto_enable_provider_instrumentors(kwargs)

        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider)

        meter_provider = kwargs.get("meter_provider")
        meter = get_meter(LIBRARY_NAME, LIBRARY_VERSION, meter_provider)

        # TODO: Add metrics creation here if needed
        # Define and create metrics relevant to Karo (e.g., tool calls count, memory operations duration)
        # LLM metrics are generally handled by specific provider instrumentors
        try:
            agent_run_counter = meter.create_counter(
                name="karo.agent.runs",
                unit="run",
                description="Number of Karo agent runs",
            )
            tool_run_counter = meter.create_counter(
                name="karo.tool.runs",
                unit="run",
                description="Number of Karo tool executions",
            )
            tool_error_counter = meter.create_counter(
                 name="karo.tool.errors",
                 unit="call",
                 description="Number of failed Karo tool executions",
            )
            memory_add_counter = meter.create_counter(
                 name="karo.memory.adds",
                 unit="add",
                 description="Number of Karo memory additions",
            )
            memory_query_counter = meter.create_counter(
                 name="karo.memory.queries",
                 unit="query",
                 description="Number of Karo memory queries",
            )

            agent_run_duration = meter.create_histogram(
                name="karo.agent.run.duration",
                unit="s",
                description="Duration of Karo agent runs",
            )
            tool_run_duration = meter.create_histogram(
                name="karo.tool.run.duration",
                unit="s",
                description="Duration of Karo tool executions",
            )
            memory_add_duration = meter.create_histogram(
                 name="karo.memory.add.duration",
                 unit="s",
                 description="Duration of Karo memory additions",
            )
            memory_query_duration = meter.create_histogram(
                 name="karo.memory.query.duration",
                 unit="s",
                 description="Duration of Karo memory queries",
            )

            karo_metrics = {
                 "agent_run_counter": agent_run_counter,
                 "tool_run_counter": tool_run_counter,
                 "tool_error_counter": tool_error_counter,
                 "memory_add_counter": memory_add_counter,
                 "memory_query_counter": memory_query_counter,
                 "agent_run_duration": agent_run_duration,
                 "tool_run_duration": tool_run_duration,
                 "memory_add_duration": memory_add_duration,
                 "memory_query_duration": memory_query_duration,
            }

            logger.debug("Karo metrics created.")

        except Exception as e:
            logger.error(f"Error creating Karo metrics: {e}", exc_info=True)
            karo_metrics = {} # Use empty dict if metrics creation fails

        # Wrap the identified methods using direct wrap_function_wrapper
        # We define wrapper factories that accept tracer and metrics
        # Note: For BaseTool and BaseProvider, we wrap the *base* class method.
        # This will apply to all subclasses unless they override the method
        # without calling super().
        self._instrument_method(
            "karo.core.base_agent", "BaseAgent", "run",
            _create_agent_run_wrapper(tracer, karo_metrics),
            get_agent_run_attributes
        )
        self._instrument_method(
            "karo.providers.base_provider", "BaseProvider", "generate_response",
            _create_provider_generate_wrapper(tracer, karo_metrics),
            get_provider_generate_attributes
        )
        self._instrument_method(
            "karo.tools.base_tool", "BaseTool", "run",
            _create_tool_run_wrapper(tracer, karo_metrics),
            get_tool_run_attributes
        )
        self._instrument_method(
            "karo.memory.memory_manager", "MemoryManager", "add_memory",
            _create_memory_add_wrapper(tracer, karo_metrics),
            get_memory_add_attributes
        )
        self._instrument_method(
            "karo.memory.memory_manager", "MemoryManager", "retrieve_relevant_memories",
            _create_memory_query_wrapper(tracer, karo_metrics),
            get_memory_query_attributes
        )
    


    def _instrument_method(self, package, class_name, method_name, wrapper_factory, attribute_handler):
        """Helper to apply instrumentation wrapper and track success."""
        full_path = f"{package}.{class_name}.{method_name}"
        try:
            # The wrapper_factory returns the actual wrapper function
            wrapper = wrapper_factory(attribute_handler)
            wrap_function_wrapper(package, f"{class_name}.{method_name}", wrapper)
            self._instrumented_methods.append((package, class_name, method_name))
            logger.debug(f"Wrapped {full_path}")
        except (AttributeError, ModuleNotFoundError) as e:
            logger.debug(
                f"Could not wrap {full_path}: {e}"
            )
        except Exception as e:
            logger.error(f"Error wrapping {full_path}: {e}", exc_info=True)

    def _auto_enable_provider_instrumentors(self, kwargs):
        """Automatically enable LLM provider instrumentors for Karo providers."""
        tracer_provider = kwargs.get("tracer_provider")
        meter_provider = kwargs.get("meter_provider")
        
        # Map of instrumentors to try enabling
        instrumentors_to_enable = [
            ("opentelemetry.instrumentation.openai", "OpenAIInstrumentor"),
            ("opentelemetry.instrumentation.anthropic", "AnthropicInstrumentor"), 
            ("opentelemetry.instrumentation.google_generativeai", "GoogleGenerativeAIInstrumentor"),
            # Add more as they become available
        ]
        
        for module_name, class_name in instrumentors_to_enable:
            try:
                module = __import__(module_name, fromlist=[class_name])
                instrumentor_class = getattr(module, class_name)
                instrumentor = instrumentor_class()
                
                if not instrumentor.is_instrumented_by_opentelemetry:
                    instrumentor.instrument(
                        tracer_provider=tracer_provider,
                        meter_provider=meter_provider
                    )
                    self._enabled_instrumentors.append(instrumentor)
                    provider_name = class_name.replace("Instrumentor", "")
                    logger.debug(f"✅ {provider_name} instrumentation enabled for Karo providers")
                    
            except ImportError:
                provider_name = class_name.replace("Instrumentor", "")
                logger.debug(f"📦 {provider_name} instrumentation not available - install with: pip install opentelemetry-instrumentation-{provider_name.lower()}")
            except Exception as e:
                provider_name = class_name.replace("Instrumentor", "")
                logger.warning(f"⚠️ Could not enable {provider_name} instrumentation: {e}")


    def _uninstrument(self, **kwargs):
        """Remove instrumentation from the Karo framework."""
        if not KARO_AVAILABLE:
            return # Nothing to uninstrument

        # Unwrap the methods that were successfully instrumented
        from opentelemetry.instrumentation.utils import unwrap as otel_unwrap # Use OTel's unwrap

        for package, class_name, method_name in self._instrumented_methods:
            try:
                otel_unwrap(getattr(__import__(package, fromlist=[class_name]), class_name), method_name)
                logger.debug(f"Unwrapped {package}.{class_name}.{method_name}")
            except Exception as e:
                logger.debug(
                    f"Failed to unwrap {package}.{class_name}.{method_name}: {e}"
                )

        self._instrumented_methods = [] # Clear the list
        logger.info("Successfully removed Karo framework instrumentation")

         # Also uninstrument provider instrumentors we enabled
        for instrumentor in self._enabled_instrumentors:
            try:
                instrumentor.uninstrument()
                logger.debug(f"Uninstrumented {instrumentor.__class__.__name__}")
            except Exception as e:
                logger.debug(f"Failed to uninstrument {instrumentor.__class__.__name__}: {e}")
        
        self._enabled_instrumentors = []


# --- Wrapper Factories (passed to _instrument_method) ---
# Each factory creates a wrapper function that takes (wrapped, instance, args, kwargs)
# and has access to tracer and metrics from its closure. It also needs the attribute handler.


def _create_agent_run_wrapper(tracer: Tracer, metrics: Dict[str, Any]):
    """Factory for the BaseAgent.run wrapper."""
    agent_run_counter: Counter = metrics.get("agent_run_counter")
    agent_run_duration: Histogram = metrics.get("agent_run_duration")

    def wrapper(attribute_handler): # Accepts the attribute handler
        def _wrapper(wrapped, instance, args, kwargs):
            
            span_name = f"karo.agent.{getattr(instance.config, 'name', instance.__class__.__name__)}.run" if hasattr(instance, 'config') else f"karo.agent.{instance.__class__.__name__}.run"
            
            
            attributes = {SpanAttributes.AALIYAH_SPAN_KIND: AaliyahSpanKindValues.AGENT.value}
            status_code = StatusCode.OK
            error_type = None
            error_message = None

            with tracer.start_as_current_span(span_name, kind=SpanKind.INTERNAL, attributes=attributes) as span:
                start_time = time.time()
                try:
                    input_attrs = attribute_handler(args=args, kwargs=kwargs, instance=instance)

                    
                    for k, v in input_attrs.items():
                        span.set_attribute(k, v)

                    # Record metric count
                    if agent_run_counter:
                        agent_run_counter.add(1)

                    return_value = wrapped(*args, **kwargs)


                    # 🔍 DEBUG: Check output attribute handler
                    output_attrs = attribute_handler(return_value=return_value, instance=instance)
                    
                    for k, v in output_attrs.items():
                        span.set_attribute(k, v)

                    # Check success status
                    if isinstance(return_value, AgentErrorSchema):
                        status_code = StatusCode.ERROR
                        error_type = return_value.error_type
                        error_message = return_value.error_message
                        
                    else:
                        print(f"🔍 KARO: Agent succeeded")

                except Exception as e:
                    status_code = StatusCode.ERROR
                    error_type = e.__class__.__name__
                    error_message = str(e)


                    span.record_exception(e)
                    span.set_attribute(CoreAttributes.ERROR_TYPE, error_type)
                    span.set_attribute(CoreAttributes.ERROR_MESSAGE, error_message)
                    raise
                finally:

                    span.set_status(Status(status_code, error_message))

            return return_value
       
        return _wrapper
    return wrapper

def _create_tool_run_wrapper(tracer: Tracer, metrics: Dict[str, Any]):
    """Factory for the BaseTool.run wrapper."""
    tool_run_counter: Counter = metrics.get("tool_run_counter")
    tool_error_counter: Counter = metrics.get("tool_error_counter")
    tool_run_duration: Histogram = metrics.get("tool_run_duration")

    def wrapper(attribute_handler): # Accepts the attribute handler
        def _wrapper(wrapped, instance, args, kwargs):
            # Span name from instance type or instance.name
            tool_name = getattr(instance, 'name', instance.__class__.__name__)
            span_name = f"karo.tool.{tool_name}.run"
            attributes = {
                SpanAttributes.AALIYAH_SPAN_KIND: AaliyahSpanKindValues.TOOL.value,
                ToolAttributes.TOOL_NAME: tool_name # Add specific tool name attribute
            }
            status_code = StatusCode.OK
            error_message = None
            tool_succeeded = False # Track success from tool's output schema

            with tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT, attributes=attributes) as span:
                start_time = time.time()
                try:
                    # Set input attributes before execution
                    input_attrs = attribute_handler(args=args, kwargs=kwargs, instance=instance)
                    for k, v in input_attrs.items():
                         span.set_attribute(k, v)

                    # Record metric count
                    if tool_run_counter:
                         tool_run_counter.add(1)

                    # Call the original method
                    return_value = wrapped(*args, **kwargs)

                    # Set output attributes after execution
                    output_attrs = attribute_handler(return_value=return_value, instance=instance)
                    for k, v in output_attrs.items():
                         span.set_attribute(k, v)

                    # Check success based on BaseToolOutputSchema
                    if isinstance(return_value, BaseToolOutputSchema):
                         tool_succeeded = return_value.success
                         error_message = return_value.error_message # Capture message even on success for details

                    if not tool_succeeded:
                         status_code = StatusCode.ERROR
                         # If not succeeded, error_message should be in the output schema
                         if tool_error_counter:
                             tool_error_counter.add(1)

                except Exception as e:
                    status_code = StatusCode.ERROR
                    error_message = str(e)
                    tool_succeeded = False # Ensure status is failed on exception

                    # Record exception on span
                    span.record_exception(e)
                    span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
                    span.set_attribute(CoreAttributes.ERROR_MESSAGE, error_message)

                    # Attempt to set input/output attributes even on error
                    try:
                        attrs_on_error = attribute_handler(args=args, kwargs=kwargs, return_value=None, instance=instance)
                        for k, v in attrs_on_error.items():
                             span.set_attribute(k, v)
                    except Exception as handler_e:
                         logger.debug(f"Error setting attributes on error for tool run: {handler_e}")

                    # Record error metric
                    if tool_error_counter:
                         tool_error_counter.add(1)

                    # Re-raise the exception
                    raise
                finally:
                    # Record duration metric
                    end_time = time.time()
                    duration = end_time - start_time
                    if tool_run_duration:
                         duration_attributes = {"status": status_code.name.lower(), "tool.name": tool_name}
                         if error_message: # Include error message in metric attributes for detail
                             duration_attributes["karo.error_message"] = error_message
                         # Add specific tool success/failure attribute to duration metric
                         duration_attributes["tool.success"] = tool_succeeded
                         tool_run_duration.record(duration, attributes=duration_attributes)

                    # Set final span status
                    span.set_status(Status(status_code, error_message))
                    # Span is automatically ended by the 'with' statement

            return return_value # Return the original result

        return _wrapper
    return wrapper


def _create_memory_add_wrapper(tracer: Tracer, metrics: Dict[str, Any]):
    """Factory for the MemoryManager.add_memory wrapper."""
    memory_add_counter: Counter = metrics.get("memory_add_counter")
    memory_add_duration: Histogram = metrics.get("memory_add_duration")

    def wrapper(attribute_handler): # Accepts the attribute handler
        def _wrapper(wrapped, instance, args, kwargs):
            span_name = "karo.memory.add"
            attributes = {SpanAttributes.AALIYAH_SPAN_KIND: "memory", "karo.operation.type": "memory_add"}
            status_code = StatusCode.OK
            error_message = None
            success = False # Track success from return value (ID or None)

            with tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT, attributes=attributes) as span:
                start_time = time.time()
                try:
                    # Set input attributes before execution
                    input_attrs = attribute_handler(args=args, kwargs=kwargs, instance=instance)
                    for k, v in input_attrs.items():
                         span.set_attribute(k, v)

                    # Record metric count
                    if memory_add_counter:
                         memory_add_counter.add(1)

                    # Call the original method
                    return_value = wrapped(*args, **kwargs)

                    # Set output attributes after execution (includes success status)
                    output_attrs = attribute_handler(return_value=return_value, instance=instance)
                    for k, v in output_attrs.items():
                         span.set_attribute(k, v)

                    # Check success based on return value (ID or None)
                    success = return_value is not None
                    if not success:
                         status_code = StatusCode.ERROR
                         # Error message is often logged internally, not returned by the method itself.
                         # We might need to capture logging or exceptions for specific errors.
                         # For now, if success is False but no exception, error_message is None.

                except Exception as e:
                    status_code = StatusCode.ERROR
                    error_message = str(e)
                    success = False # Ensure status is failed on exception

                    # Record exception on span
                    span.record_exception(e)
                    span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
                    span.set_attribute(CoreAttributes.ERROR_MESSAGE, error_message)

                    # Attempt to set input/output attributes even on error
                    try:
                        attrs_on_error = attribute_handler(args=args, kwargs=kwargs, return_value=None, instance=instance)
                        for k, v in attrs_on_error.items():
                             span.set_attribute(k, v)
                    except Exception as handler_e:
                         logger.debug(f"Error setting attributes on error for memory add: {handler_e}")

                    # Re-raise the exception
                    raise
                finally:
                    # Record duration metric
                    end_time = time.time()
                    duration = end_time - start_time
                    if memory_add_duration:
                         duration_attributes = {"status": status_code.name.lower(), "success": success}
                         if error_message:
                             duration_attributes["karo.error_message"] = error_message
                         memory_add_duration.record(duration, attributes=duration_attributes)

                    # Set final span status
                    span.set_status(Status(status_code, error_message))
                    # Span is automatically ended by the 'with' statement

            return return_value # Return the original result

        return _wrapper
    return wrapper

def _create_memory_query_wrapper(tracer: Tracer, metrics: Dict[str, Any]):
    """Factory for the MemoryManager.retrieve_relevant_memories wrapper."""
    memory_query_counter: Counter = metrics.get("memory_query_counter")
    memory_query_duration: Histogram = metrics.get("memory_query_duration")

    def wrapper(attribute_handler): # Accepts the attribute handler
        def _wrapper(wrapped, instance, args, kwargs):
            span_name = "karo.memory.query"
            attributes = {SpanAttributes.AALIYAH_SPAN_KIND: "memory", "karo.operation.type": "memory_query"}
            status_code = StatusCode.OK
            error_message = None
            success = False # Track success

            with tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT, attributes=attributes) as span:
                start_time = time.time()
                try:
                    # Set input attributes before execution
                    input_attrs = attribute_handler(args=args, kwargs=kwargs, instance=instance)
                    for k, v in input_attrs.items():
                         span.set_attribute(k, v)

                    # Record metric count
                    if memory_query_counter:
                         memory_query_counter.add(1)

                    # Call the original method
                    return_value = wrapped(*args, **kwargs)

                    # Set output attributes after execution (includes success status based on list return)
                    output_attrs = attribute_handler(return_value=return_value, instance=instance)
                    for k, v in output_attrs.items():
                         span.set_attribute(k, v)

                    # Check success based on list return (empty list is success=True with 0 results)
                    success = isinstance(return_value, list) # Success if a list is returned
                    if not success:
                         status_code = StatusCode.ERROR
                         # Error message is often logged internally, not returned.
                         # If return_value is not a list, the attribute handler should set an error message.
                         error_message = output_attrs.get(CoreAttributes.ERROR_MESSAGE) # Try to get error message from attributes


                except Exception as e:
                    status_code = StatusCode.ERROR
                    error_message = str(e)
                    success = False # Ensure status is failed on exception

                    # Record exception on span
                    span.record_exception(e)
                    span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
                    span.set_attribute(CoreAttributes.ERROR_MESSAGE, error_message)

                    # Attempt to set input/output attributes even on error
                    try:
                        attrs_on_error = attribute_handler(args=args, kwargs=kwargs, return_value=None, instance=instance)
                        for k, v in attrs_on_error.items():
                             span.set_attribute(k, v)
                    except Exception as handler_e:
                         logger.debug(f"Error setting attributes on error for memory query: {handler_e}")

                    # Re-raise the exception
                    raise
                finally:
                    # Record duration metric
                    end_time = time.time()
                    duration = end_time - start_time
                    if memory_query_duration:
                         duration_attributes = {"status": status_code.name.lower(), "success": success}
                         if error_message:
                             duration_attributes["karo.error_message"] = error_message
                         memory_query_duration.record(duration, attributes=duration_attributes)

                    # Set final span status
                    span.set_status(Status(status_code, error_message))
                    # Span is automatically ended by the 'with' statement

            return return_value # Return the original result

        return _wrapper
    return wrapper


def _create_provider_generate_wrapper(tracer: Tracer, metrics: Dict[str, Any]):
    """Factory for the BaseProvider.generate_response wrapper."""
    
    def wrapper(attribute_handler):
        def _wrapper(wrapped, instance, args, kwargs):
            # Detect the specific provider type from the instance
            provider_class_name = instance.__class__.__name__
            model_name = instance.get_model_name() if hasattr(instance, 'get_model_name') else 'unknown'
            
            # Map Karo providers to their underlying LLM library instrumentors
            karo_provider_map = {
                "OpenAIProvider": {
                    "instrumentor_module": "opentelemetry.instrumentation.openai",
                    "instrumentor_class": "OpenAIInstrumentor",
                    "llm_system": "openai",
                    "skip_instrumentation": True  # Let OpenAI instrumentor handle it
                },
                "AnthropicProvider": {
                    "instrumentor_module": "opentelemetry.instrumentation.anthropic", 
                    "instrumentor_class": "AnthropicInstrumentor",
                    "llm_system": "anthropic",
                    "skip_instrumentation": True  # Let Anthropic instrumentor handle it
                },
                "GeminiProvider": {
                    "instrumentor_module": "opentelemetry.instrumentation.google_generativeai",
                    "instrumentor_class": "GoogleGenerativeAIInstrumentor", 
                    "llm_system": "google_generativeai",
                    "skip_instrumentation": True  # Let Google instrumentor handle it
                },
                "OllamaProvider": {
                    "instrumentor_module": "opentelemetry.instrumentation.openai",
                    "instrumentor_class": "OpenAIInstrumentor",
                    "llm_system": "ollama", 
                    "skip_instrumentation": True  # Uses OpenAI client, so OpenAI instrumentor handles it
                }
            }
            
            provider_info = karo_provider_map.get(provider_class_name)
            
            if provider_info and provider_info.get("skip_instrumentation"):
                # Provider has dedicated instrumentor - create lightweight parent span
                span_name = f"karo.provider.{provider_class_name}.generate_response"
                attributes = {
                    SpanAttributes.AALIYAH_SPAN_KIND: "llm",
                    "karo.operation.type": "provider_generate_response",
                    "karo.provider.class": provider_class_name,
                    "karo.provider.system": provider_info["llm_system"],
                    "karo.provider.model": model_name
                }
                
                logger.debug(f"Creating lightweight Karo span for {provider_class_name}, "
                           f"delegating LLM instrumentation to {provider_info['instrumentor_class']}")
                
                with tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT, attributes=attributes) as span:
                    try:
                        # Set Karo-specific input attributes
                        input_attrs = attribute_handler(args=args, kwargs=kwargs, instance=instance)
                        for k, v in input_attrs.items():
                            span.set_attribute(k, v)
                        
                        # Call original method - provider's instrumentor creates detailed child spans
                        return_value = wrapped(*args, **kwargs)
                        
                        # Set Karo-specific output attributes
                        output_attrs = attribute_handler(return_value=return_value, instance=instance)
                        for k, v in output_attrs.items():
                            span.set_attribute(k, v)
                            
                        span.set_status(Status(StatusCode.OK))
                        return return_value
                        
                    except Exception as e:
                        span.record_exception(e)
                        span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
                        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise
            else:
                # Unknown/custom provider - do full instrumentation
                logger.debug(f"Fully instrumenting unknown provider: {provider_class_name}")
                span_name = f"karo.provider.{provider_class_name}.generate_response"
                attributes = {
                    SpanAttributes.AALIYAH_SPAN_KIND: "llm",
                    "karo.operation.type": "provider_generate_response",
                    "karo.provider.class": provider_class_name,
                    "karo.provider.system": "custom",
                    "karo.provider.model": model_name
                }
                
                with tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT, attributes=attributes) as span:
                    start_time = time.time()
                    try:
                        # Set input attributes
                        input_attrs = attribute_handler(args=args, kwargs=kwargs, instance=instance)
                        for k, v in input_attrs.items():
                            span.set_attribute(k, v)
                        
                        # Call original method
                        return_value = wrapped(*args, **kwargs)
                        
                        # Set output attributes
                        output_attrs = attribute_handler(return_value=return_value, instance=instance)
                        for k, v in output_attrs.items():
                            span.set_attribute(k, v)
                            
                        # Record custom metrics for unknown providers
                        duration = time.time() - start_time
                        # Could add custom duration metrics here
                        
                        span.set_status(Status(StatusCode.OK))
                        return return_value
                        
                    except Exception as e:
                        span.record_exception(e)
                        span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
                        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise
        
        return _wrapper
    return wrapper

