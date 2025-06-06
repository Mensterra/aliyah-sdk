
from aliyah_sdk.legacy import (
        start_session,
    end_session,
    track_agent,
    track_tool,
    end_all_sessions,
    Session,
    ToolEvent,
    ErrorEvent,
    ActionEvent,
    LLMEvent,
)

from typing import List, Optional, Union
from aliyah_sdk.client import Client


# Client global instance; one per process runtime
_client = Client()


def get_client() -> Client:
    """Get the singleton client instance"""
    global _client

    return _client


def record(event):
    """
    Legacy function to record an event. This is kept for backward compatibility.

    In the current version, this simply sets the end_timestamp on the event.

    Args:
        event: The event to record
    """
    from aliyah_sdk.helpers.time import get_ISO_time

    # TODO: Manual timestamp assignment is a temporary fix; should use proper event lifecycle
    if event and hasattr(event, "end_timestamp"):
        event.end_timestamp = get_ISO_time()

    return event


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
    Initializes the Aaliyah SDK.
    
    Args:
        base_url (str, optional): Base URL for all endpoints. Defaults to 'https://api.mensterra.com'.
        metrics_endpoint (str, optional): Endpoint for metrics. Auto-constructed from base_url if not provided.
        logs_endpoint (str, optional): Endpoint for logs. Auto-constructed from base_url if not provided.
        # ... rest of your existing docstring
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
    """Update client configuration

    Args:
        **kwargs: Configuration parameters. Supported parameters include:
            - api_key: API Key for Aaliyah services
            - endpoint: The endpoint for the Aaliyah service
            - app_url: The dashboard URL for the Aaliyah app
            - max_wait_time: Maximum time to wait in milliseconds before flushing the queue
            - max_queue_size: Maximum size of the event queue
            - default_tags: Default tags for the sessions
            - instrument_llm_calls: Whether to instrument LLM calls
            - auto_start_session: Whether to start a session automatically
            - skip_auto_end_session: Don't automatically end session
            - env_data_opt_out: Whether to opt out of collecting environment data
            - log_level: The log level to use for the client
            - fail_safe: Whether to suppress errors and continue execution
            - exporter: Custom span exporter for OpenTelemetry trace data
            - processor: Custom span processor for OpenTelemetry trace data
            - exporter_endpoint: Endpoint for the exporter
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


__all__ = [
    "init",
    "configure",
    "get_client",
    "record",
    "start_session",
    "end_session",
    "track_agent",
    "track_tool",
    "end_all_sessions",
    "Session",
    "ToolEvent",
    "ErrorEvent",
    "ActionEvent",
    "LLMEvent",
]
