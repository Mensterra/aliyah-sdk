# aliyah_sdk/aliyah_sdk/config.py
import os
import logging
import json
import sys
from typing import List, Optional, Set, Union

# Check if pytest is imported globally (simplistic check)
TESTING = "pytest" in sys.modules

# Import helper functions from within the SDK package
try:
    from .exceptions import InvalidApiKeyException
except ImportError:
    class InvalidApiKeyException(Exception):
        def __init__(self, api_key, endpoint):
            super().__init__(f"Invalid API key: {api_key} for endpoint: {endpoint}")

try:
    from .helpers.serialization import AaliyahJSONEncoder
except ImportError:
    # Define a fallback only if the local import fails
    class AaliyahJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, set):
                return list(obj)
            # Fallback to default JSONEncoder for other types
            return super().default(obj)

# Map string log level from environment to logging integer level
LOG_LEVEL_STR = os.getenv("ALIYAH_LOG_LEVEL", "").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO) # Default to INFO if not set or invalid

class Config:
    """Client-side Configuration for the Aaliyah SDK"""

    # === Testing flag ===
    TESTING = TESTING

    # === Core API Endpoint Configuration ===
    # These are critical for the SDK to know where to send data
    api_key: Optional[str] = os.getenv("ALIYAH_API_KEY") or os.getenv("AALIYAH_API_KEY") # Prioritize ALIYAH_ standard env
    endpoint: str = os.getenv("ALIYAH_API_ENDPOINT") or os.getenv("AALIYAH_API_ENDPOINT", "https://api.mensterra.com")


    # === Dashboard URL ===
    # Where users can view traces (used for logging URL)
    app_url: str = os.getenv("ALIYAH_APP_URL") or os.getenv("AALIYAH_APP_URL", "https://app.mensterra.com")


    # === Agent Configuration === 🔥 ADD THIS SECTION
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None

    # === OTLP endpoints for OpenTelemetry ===
    # These are where traces and metrics are sent directly.
    # Default to the backend's standard OTLP paths relative to the main endpoint,
    # but allow overriding.
    EXPORTER_ENDPOINT: str = os.getenv("ALIYAH_EXPORTER_ENDPOINT") or os.getenv("AALIYAH_EXPORTER_ENDPOINT", f"{endpoint}/v1/traces")
    METRICS_ENDPOINT: str = os.getenv("ALIYAH_METRICS_ENDPOINT") or os.getenv("AALIYAH_METRICS_ENDPOINT", f"{endpoint}/v1/metrics")
    LOGS_ENDPOINT: str = os.getenv("ALIYAH_LOGS_ENDPOINT") or os.getenv("AALIYAH_LOGS_ENDPOINT", f"{endpoint}/v1/logs/upload/")  # Add this

    # === Monitoring/Telemetry Configuration ===
    # Settings for the OpenTelemetry SDK within the agent's process
    MAX_QUEUE_SIZE: int = int(os.getenv("ALIYAH_MAX_QUEUE_SIZE") or os.getenv("AALIYAH_MAX_QUEUE_SIZE", "512"))
    MAX_WAIT_TIME: int = int(os.getenv("ALIYAH_MAX_WAIT_TIME") or os.getenv("AALIYAH_MAX_WAIT_TIME", "5000")) # in milliseconds
    EXPORT_FLUSH_INTERVAL: int = int(os.getenv("ALIYAH_EXPORT_FLUSH_INTERVAL") or os.getenv("AALIYAH_EXPORT_FLUSH_INTERVAL", "1000")) # in milliseconds

    INSTRUMENT_LLM_CALLS: bool = (os.getenv("ALIYAH_INSTRUMENT_LLM_CALLS") or os.getenv("AALIYAH_INSTRUMENT_LLM_CALLS", "True")).lower() == "true"

    # === Session Configuration ===
    AUTO_START_SESSION: bool = (os.getenv("ALIYAH_AUTO_START_SESSION") or os.getenv("AALIYAH_AUTO_START_SESSION", "True")).lower() == "true"
    AUTO_INIT: bool = (os.getenv("ALIYAH_AUTO_INIT") or os.getenv("AALIYAH_AUTO_INIT", "True")).lower() == "true" # Should the SDK auto-initialize on import?
    SKIP_AUTO_END_SESSION: bool = (os.getenv("ALIYAH_SKIP_AUTO_END_SESSION") or os.getenv("AALIYAH_SKIP_AUTO_END_SESSION", "False")).lower() == "true"
    ENV_DATA_OPT_OUT: bool = (os.getenv("ALIYAH_ENV_DATA_OPT_OUT") or os.getenv("AALIYAH_ENV_DATA_OPT_OUT", "False")).lower() == "true"
    FAIL_SAFE: bool = (os.getenv("ALIYAH_FAIL_SAFE") or os.getenv("AALIYAH_FAIL_SAFE", "False")).lower() == "true"
    PREFETCH_JWT_TOKEN: bool = (os.getenv("ALIYAH_PREFETCH_JWT_TOKEN") or os.getenv("AALIYAH_PREFETCH_JWT_TOKEN", "True")).lower() == "true"

    # === Default Tags ===
    _default_tags_str = os.getenv("ALIYAH_DEFAULT_TAGS", "")
    DEFAULT_TAGS: Set[str] = set(_default_tags_str.split(",")) if _default_tags_str else set()

    # === Logging Configuration ===
    # Use the logging level determined above
    LOG_LEVEL = LOG_LEVEL # <-- Assign the class attribute
    log_level = LOG_LEVEL  # Add instance-style access for compatibility
    logs_endpoint = LOGS_ENDPOINT 

    # === OpenTelemetry Configuration (Advanced) ===
    # Allow users to provide custom OTel components if needed
    exporter = None  # Custom span exporter instance
    processor = None  # Custom span processor instance

    # === Instance-style access for compatibility ===
    max_queue_size = MAX_QUEUE_SIZE
    max_wait_time = MAX_WAIT_TIME
    export_flush_interval = EXPORT_FLUSH_INTERVAL
    instrument_llm_calls = INSTRUMENT_LLM_CALLS
    auto_start_session = AUTO_START_SESSION
    auto_init = AUTO_INIT
    skip_auto_end_session = SKIP_AUTO_END_SESSION
    env_data_opt_out = ENV_DATA_OPT_OUT
    fail_safe = FAIL_SAFE
    prefetch_jwt_token = PREFETCH_JWT_TOKEN
    default_tags = DEFAULT_TAGS
    exporter_endpoint = EXPORTER_ENDPOINT
    metrics_endpoint = METRICS_ENDPOINT

    # Update your Config.configure method in aliyah_sdk/config.py

    @classmethod
    def configure(
        cls,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        app_url: Optional[str] = None,
        max_wait_time: Optional[int] = None,
        export_flush_interval: Optional[int] = None,
        max_queue_size: Optional[int] = None,
        default_tags: Optional[List[str]] = None,
        instrument_llm_calls: Optional[bool] = None,
        auto_start_session: Optional[bool] = None,
        auto_init: Optional[bool] = None,
        skip_auto_end_session: Optional[bool] = None,
        env_data_opt_out: Optional[bool] = None,
        log_level: Optional[Union[str, int]] = None,
        fail_safe: Optional[bool] = None,
        prefetch_jwt_token: Optional[bool] = None,
        exporter = None,
        processor = None,
        exporter_endpoint: Optional[str] = None,
        metrics_endpoint: Optional[str] = None,
        logs_endpoint: Optional[str] = None,
        agent_id: Optional[int] = None,
        agent_name: Optional[str] = None,
        **kwargs
    ):
        """Configure settings from kwargs, overriding environment variables and defaults"""

        if api_key is not None:
            cls.api_key = api_key
            if not cls.TESTING:
                try:
                    if not isinstance(api_key, str) or len(api_key) < 10 or not api_key.startswith("aliyah_"):
                        raise InvalidApiKeyException(api_key, cls.endpoint)
                except Exception:
                    raise InvalidApiKeyException(api_key, cls.endpoint)

        if endpoint is not None:
            cls.endpoint = endpoint

        if app_url is not None:
            cls.app_url = app_url

        # 🔥 ADD AGENT CONFIGURATION
        if agent_id is not None:
            cls.agent_id = agent_id

        if agent_name is not None:
            cls.agent_name = agent_name

        if exporter_endpoint is not None:
            cls.EXPORTER_ENDPOINT = exporter_endpoint
            cls.exporter_endpoint = exporter_endpoint

        if metrics_endpoint is not None:
            cls.METRICS_ENDPOINT = metrics_endpoint
            cls.metrics_endpoint = metrics_endpoint

        if logs_endpoint is not None:
            cls.LOGS_ENDPOINT = logs_endpoint
            cls.logs_endpoint = logs_endpoint

        if max_wait_time is not None:
            cls.MAX_WAIT_TIME = max_wait_time
            cls.max_wait_time = max_wait_time

        if export_flush_interval is not None:
            cls.EXPORT_FLUSH_INTERVAL = export_flush_interval
            cls.export_flush_interval = export_flush_interval

        if max_queue_size is not None:
            cls.MAX_QUEUE_SIZE = max_queue_size
            cls.max_queue_size = max_queue_size

        if default_tags is not None:
            cls.DEFAULT_TAGS = set(default_tags)
            cls.default_tags = set(default_tags)

        if instrument_llm_calls is not None:
            cls.INSTRUMENT_LLM_CALLS = instrument_llm_calls
            cls.instrument_llm_calls = instrument_llm_calls

        if auto_start_session is not None:
            cls.AUTO_START_SESSION = auto_start_session
            cls.auto_start_session = auto_start_session

        if auto_init is not None:
            cls.AUTO_INIT = auto_init
            cls.auto_init = auto_init

        if skip_auto_end_session is not None:
            cls.SKIP_AUTO_END_SESSION = skip_auto_end_session
            cls.skip_auto_end_session = skip_auto_end_session

        if env_data_opt_out is not None:
            cls.ENV_DATA_OPT_OUT = env_data_opt_out
            cls.env_data_opt_out = env_data_opt_out

        if log_level is not None:
            # Convert log_level parameter (string or int) to the appropriate logging integer
            if isinstance(log_level, str):
                log_level_str = log_level.upper()
                if hasattr(logging, log_level_str):
                    cls.LOG_LEVEL = getattr(logging, log_level_str)
                    cls.log_level = getattr(logging, log_level_str)
                else:
                    cls.LOG_LEVEL = logging.INFO
                    cls.log_level = logging.INFO
            else:
                cls.LOG_LEVEL = log_level
                cls.log_level = log_level

        if fail_safe is not None:
            cls.FAIL_SAFE = fail_safe
            cls.fail_safe = fail_safe

        if prefetch_jwt_token is not None:
            cls.PREFETCH_JWT_TOKEN = prefetch_jwt_token
            cls.prefetch_jwt_token = prefetch_jwt_token

        if exporter is not None:
            cls.exporter = exporter

        if processor is not None:
            cls.processor = processor

        # 🔥 UPDATE THE UNKNOWN KWARGS CHECK
        unknown_kwargs = set(kwargs.keys()) - {
            'api_key', 'endpoint', 'app_url', 'max_wait_time', 'export_flush_interval',
            'max_queue_size', 'default_tags', 'instrument_llm_calls', 'auto_start_session',
            'auto_init', 'skip_auto_end_session', 'env_data_opt_out', 'log_level',
            'fail_safe', 'prefetch_jwt_token', 'exporter', 'processor',
            'exporter_endpoint', 'metrics_endpoint', 'logs_endpoint',
            'agent_id', 'agent_name'  # 🔥 ADD THESE
        }
        if unknown_kwargs:
            try:
                from .logging import logger as sdk_logger
                sdk_logger.warning(f"Unknown configuration parameters passed to Config.configure: {list(unknown_kwargs)}")
            except ImportError:
                logging.warning(f"Unknown configuration parameters passed to Config.configure: {list(unknown_kwargs)}")

    @classmethod
    def dict(cls):
        """Return a dictionary representation of the config"""
        # Include only relevant fields for dictionary representation
        return {
            "api_key": cls.api_key,
            "endpoint": cls.endpoint,
            "app_url": cls.app_url,
            "max_wait_time": cls.MAX_WAIT_TIME,
            "export_flush_interval": cls.EXPORT_FLUSH_INTERVAL,
            "max_queue_size": cls.MAX_QUEUE_SIZE,
            "default_tags": list(cls.DEFAULT_TAGS),
            "instrument_llm_calls": cls.INSTRUMENT_LLM_CALLS,
            "auto_start_session": cls.AUTO_START_SESSION,
            "auto_init": cls.AUTO_INIT,
            "skip_auto_end_session": cls.SKIP_AUTO_END_SESSION,
            "env_data_opt_out": cls.ENV_DATA_OPT_OUT,
            # Convert log level int to string name for representation
            "log_level": logging.getLevelName(cls.LOG_LEVEL), # Use the class attribute LOG_LEVEL
            "fail_safe": cls.FAIL_SAFE,
            "prefetch_jwt_token": cls.PREFETCH_JWT_TOKEN,
            # Exporter/processor are objects, representing them as strings or None
            "exporter": str(cls.exporter) if cls.exporter else None,
            "processor": str(cls.processor) if cls.processor else None,
            "exporter_endpoint": cls.EXPORTER_ENDPOINT,
            "metrics_endpoint": cls.METRICS_ENDPOINT,
        }