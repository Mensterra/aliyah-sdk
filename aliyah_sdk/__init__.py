from typing import List, Optional, Union
from aliyah_sdk.client import Client

# Client global instance; one per process runtime
_client = Client()


def get_client() -> Client:
    """Get the singleton client instance"""
    global _client
    return _client


def init(
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    app_url: Optional[str] = None,
    base_url: Optional[str] = None, 
    max_wait_time: Optional[int] = None,
    max_queue_size: Optional[int] = None,
    tags: Optional[List[str]] = None,
    default_tags: Optional[List[str]] = None,
    instrument_llm_calls: Optional[bool] = None,
    auto_start_session: Optional[bool] = None,
    auto_init: Optional[bool] = None,
    skip_auto_end_session: Optional[bool] = None,
    env_data_opt_out: Optional[bool] = None,
    log_level: Optional[Union[str, int]] = None,
    fail_safe: Optional[bool] = None,
    exporter_endpoint: Optional[str] = None,
    metrics_endpoint: Optional[str] = None,  
    logs_endpoint: Optional[str] = None,     
    agent_id: Optional[int] = None,
    agent_name: Optional[str] = None,
    **kwargs,
):
    """
    Initializes the Aliyah SDK.
    
    Args:
        api_key (str, optional): API Key for Aliyah services. Can also be set via ALIYAH_API_KEY env var.
        base_url (str, optional): Base URL for all endpoints. Defaults to 'https://api.mensterra.com'.
        endpoint (str, optional): Main API endpoint. Auto-constructed from base_url if not provided.
        app_url (str, optional): Dashboard URL. Auto-constructed from base_url if not provided.
        exporter_endpoint (str, optional): Traces endpoint. Auto-constructed from base_url if not provided.
        metrics_endpoint (str, optional): Metrics endpoint. Auto-constructed from base_url if not provided.
        logs_endpoint (str, optional): Logs endpoint. Auto-constructed from base_url if not provided.
        agent_id (int, optional): Unique identifier for your agent/application.
        agent_name (str, optional): Human-readable name for your agent/application.
        instrument_llm_calls (bool, optional): Enable automatic LLM call tracing. Defaults to True.
        auto_start_session (bool, optional): Automatically start a session on init. Defaults to False.
        default_tags (List[str], optional): Default tags to apply to all sessions.
        max_wait_time (int, optional): Maximum time to wait before flushing traces (ms).
        max_queue_size (int, optional): Maximum number of traces to queue.
        log_level (str|int, optional): Logging level for the SDK.
        fail_safe (bool, optional): Suppress errors and continue execution if True.
        **kwargs: Additional configuration parameters.
        
    Returns:
        Session object if auto_start_session=True, None otherwise.
    """
    global _client

    # Set default base URL if not provided
    if base_url is None:
        base_url = "https://api.mensterra.com"
    
    # Construct endpoints from base_url if not explicitly provided
    if endpoint is None:
        endpoint = base_url
    
    if app_url is None:
        app_url = base_url.replace("api.", "app.")
    
    if exporter_endpoint is None:
        exporter_endpoint = f"{base_url}/v1/traces"
    
    if metrics_endpoint is None:
        metrics_endpoint = f"{base_url}/v1/metrics"
    
    if logs_endpoint is None:
        logs_endpoint = f"{base_url}/v1/logs/upload/"

    # Merge tags and default_tags if both are provided
    merged_tags = None
    if tags and default_tags:
        merged_tags = list(set(tags + default_tags))
    elif tags:
        merged_tags = tags
    elif default_tags:
        merged_tags = default_tags

    return _client.init(
        api_key=api_key,
        endpoint=endpoint,
        app_url=app_url,
        max_wait_time=max_wait_time,
        max_queue_size=max_queue_size,
        default_tags=merged_tags,
        instrument_llm_calls=instrument_llm_calls,
        auto_start_session=auto_start_session,
        auto_init=auto_init,
        skip_auto_end_session=skip_auto_end_session,
        env_data_opt_out=env_data_opt_out,
        log_level=log_level,
        fail_safe=fail_safe,
        exporter_endpoint=exporter_endpoint,
        metrics_endpoint=metrics_endpoint,  
        logs_endpoint=logs_endpoint,        
        agent_id=agent_id,
        agent_name=agent_name,
        **kwargs,
    )


def configure(**kwargs):
    """
    Update client configuration after initialization.

    Args:
        **kwargs: Configuration parameters. Supported parameters include:
            - api_key: API Key for Aliyah services
            - endpoint: The endpoint for the Aliyah service
            - app_url: The dashboard URL for the Aliyah app
            - base_url: Base URL that auto-constructs other endpoints
            - max_wait_time: Maximum time to wait in milliseconds before flushing the queue
            - max_queue_size: Maximum size of the event queue
            - default_tags: Default tags for the sessions
            - instrument_llm_calls: Whether to instrument LLM calls
            - auto_start_session: Whether to start a session automatically
            - skip_auto_end_session: Don't automatically end session
            - env_data_opt_out: Whether to opt out of collecting environment data
            - log_level: The log level to use for the client
            - fail_safe: Whether to suppress errors and continue execution
            - exporter_endpoint: Endpoint for trace data
            - metrics_endpoint: Endpoint for metrics data
            - logs_endpoint: Endpoint for logs data
            - agent_id: Agent identifier
            - agent_name: Agent name
    """
    global _client

    # List of valid parameters that can be passed to configure
    valid_params = {
        "api_key",
        "endpoint", 
        "app_url",
        "base_url",           
        "max_wait_time",
        "max_queue_size",
        "default_tags",
        "instrument_llm_calls",
        "auto_start_session",
        "skip_auto_end_session",
        "env_data_opt_out",
        "log_level",
        "fail_safe",
        "exporter",
        "processor",
        "exporter_endpoint",
        "metrics_endpoint",   
        "logs_endpoint",      
        "agent_id",          
        "agent_name",        
    }

    # Handle base_url logic if provided
    if "base_url" in kwargs:
        base_url = kwargs.pop("base_url")
        
        # Auto-construct missing endpoints
        if "endpoint" not in kwargs:
            kwargs["endpoint"] = base_url
        if "app_url" not in kwargs:
            kwargs["app_url"] = base_url.replace("api.", "app.")
        if "exporter_endpoint" not in kwargs:
            kwargs["exporter_endpoint"] = f"{base_url}/v1/traces"
        if "metrics_endpoint" not in kwargs:
            kwargs["metrics_endpoint"] = f"{base_url}/v1/metrics"
        if "logs_endpoint" not in kwargs:
            kwargs["logs_endpoint"] = f"{base_url}/v1/logs/upload/"

    # Check for invalid parameters
    invalid_params = set(kwargs.keys()) - valid_params
    if invalid_params:
        from .logging.config import logger
        logger.warning(f"Invalid configuration parameters: {invalid_params}")

    _client.configure(**kwargs)


# Optional session management for advanced use cases
def start_session(tags: Optional[List[str]] = None):
    """
    Start a new tracing session (optional - use for granular session control).
    
    Most users should use auto_start_session=True in init() instead.
    
    Args:
        tags: Optional tags to attach to the session for filtering
        
    Returns:
        Session object that should be passed to end_session()
    """
    from aliyah_sdk.sessions import start_session as _start_session
    return _start_session(tags=tags)


def end_session(session=None, **kwargs):
    """
    End a tracing session (optional - use with start_session()).
    
    Args:
        session: Session object returned by start_session()
        **kwargs: Additional session metadata (end_state, end_state_reason, etc.)
    """
    from aliyah_sdk.sessions import end_session as _end_session
    return _end_session(session, **kwargs)


# Export only the modern, non-deprecated API
__all__ = [
    "init",
    "configure", 
    "get_client",
    "start_session",
    "end_session",
]