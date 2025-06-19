"""
Session management for Aliyah SDK.

Provides manual session control for grouping related operations and workflows.
"""

from typing import Optional, Any, Dict, List, Union

from aliyah_sdk.logging import logger
from aliyah_sdk.sdk.core import TracingCore
from aliyah_sdk.semconv.span_kinds import SpanKind

_current_session: Optional["Session"] = None


class Session:
    """
    Represents an active tracing session that groups related operations together.
    
    Sessions are automatically created by start_session() and should be ended
    with end_session() to properly close the tracing span.
    """

    def __init__(self, span: Any, token: Any):
        self.span = span
        self.token = token

    def __del__(self):
        """Cleanup fallback to ensure spans are properly ended."""
        try:
            if self.span is not None:
                self.span.end()
        except:
            pass


def _create_session_span(tags: Union[Dict[str, Any], List[str], None] = None) -> tuple:
    """
    Create a session span with optional tags.

    Args:
        tags: Optional tags to attach to the span for filtering in the dashboard.

    Returns:
        A tuple of (span, context, token) for session management.
    """
    from aliyah_sdk.sdk.decorators.utility import _make_span

    attributes = {}
    if tags:
        attributes["tags"] = tags
    return _make_span("session", span_kind=SpanKind.SESSION, attributes=attributes)


def start_session(tags: Union[Dict[str, Any], List[str], None] = None) -> Session:
    """
    Start a new tracing session to group related operations.

    Sessions allow you to organize traces by logical workflows, user interactions,
    or any other meaningful grouping. All operations performed while a session
    is active will be associated with that session.

    Args:
        tags: Optional tags to attach to the session for filtering and organization
             in the Aliyah dashboard. Can be a list of strings or dict of key-value pairs.
             
             Examples:
             - ["user_request", "production"]
             - {"user_id": "123", "workflow": "data_processing"}

    Returns:
        A Session object that should be passed to end_session() when complete.

    Example:
        ```python
        import aliyah_sdk
        
        # Initialize the SDK
        aliyah_sdk.init(agent_id=123, instrument_llm_calls=True)
        
        # Start a session for a user workflow
        session = aliyah_sdk.start_session(tags=["user_workflow", "data_analysis"])
        
        # Perform your operations - they'll be traced under this session
        result = your_ai_function()
        
        # End the session
        aliyah_sdk.end_session(session)
        ```

    Raises:
        Exception: If the TracingCore is not initialized. Will attempt auto-initialization.
    """
    global _current_session

    if not TracingCore.get_instance().initialized:
        from aliyah_sdk import Client

        try:
            Client().init(auto_start_session=False)
            if not TracingCore.get_instance().initialized:
                logger.warning(
                    "Aliyah client initialization failed. Creating a dummy session that will not send data."
                )
                dummy_session = Session(None, None)
                _current_session = dummy_session
                return dummy_session
        except Exception as e:
            logger.warning(
                f"Aliyah client initialization failed: {str(e)}. Creating a dummy session that will not send data."
            )
            dummy_session = Session(None, None)
            _current_session = dummy_session
            return dummy_session

    span, ctx, token = _create_session_span(tags)
    session = Session(span, token)

    # Track the current session globally
    _current_session = session

    # Register with the client for consistency
    try:
        import aliyah_sdk.client.client
        aliyah_sdk.client.client._active_session = session
    except Exception:
        pass

    return session


def _set_span_attributes(span: Any, attributes: Dict[str, Any]) -> None:
    """
    Set attributes on a span for additional metadata.

    Args:
        span: The span to set attributes on
        attributes: Dictionary of attributes to set
    """
    if span is None:
        return

    for key, value in attributes.items():
        span.set_attribute(f"aliyah.session.{key}", str(value))


def _flush_span_processors() -> None:
    """
    Force flush all span processors to ensure data is sent immediately.
    """
    try:
        from opentelemetry.trace import get_tracer_provider
        tracer_provider = get_tracer_provider()
        tracer_provider.force_flush()  # type: ignore
    except Exception as e:
        logger.warning(f"Failed to force flush span processor: {e}")


def end_session(session: Session, **kwargs) -> None:
    """
    End a previously started session and finalize the trace.

    This properly closes the session span and ensures all trace data is flushed
    to the Aliyah platform.

    Args:
        session: The Session object returned by start_session()
        **kwargs: Optional attributes to set on the session before ending.
                 Common attributes:
                 - end_state: "success", "error", "cancelled"
                 - end_reason: Description of why the session ended
                 - result_summary: Brief summary of session results

    Example:
        ```python
        session = aliyah_sdk.start_session(tags=["data_processing"])
        
        try:
            # Your operations here
            process_data()
            aliyah_sdk.end_session(session, end_state="success", end_reason="Processing completed")
        except Exception as e:
            aliyah_sdk.end_session(session, end_state="error", end_reason=str(e))
        ```
    """
    global _current_session

    from aliyah_sdk.sdk.decorators.utility import _finalize_span
    from aliyah_sdk.sdk.core import TracingCore

    if not TracingCore.get_instance().initialized:
        logger.debug("Ignoring end_session call - TracingCore not initialized")
        return

    if not hasattr(session, "span") or not hasattr(session, "token"):
        logger.warning("Invalid session object provided to end_session")
        return

    # Clear client active session reference if this is the active session
    try:
        import aliyah_sdk.client.client
        if session is aliyah_sdk.client.client._active_session:
            aliyah_sdk.client.client._active_session = None
    except Exception:
        pass

    try:
        # Set any final attributes on the session
        if session.span is not None and kwargs:
            _set_span_attributes(session.span, kwargs)
        
        # Finalize the span with proper cleanup
        if session.span is not None:
            _finalize_span(session.span, session.token)
            _flush_span_processors()

        # Clear global session reference if this is the current session
        if _current_session is session:
            _current_session = None

    except Exception as e:
        logger.warning(f"Error ending session: {e}")
        # Fallback: try direct span ending
        try:
            if hasattr(session.span, "end"):
                session.span.end()
                if _current_session is session:
                    _current_session = None
        except:
            pass


def get_current_session() -> Optional[Session]:
    """
    Get the currently active session, if any.
    
    Returns:
        The current Session object, or None if no session is active.
    """
    return _current_session


__all__ = [
    "Session",
    "start_session", 
    "end_session",
    "get_current_session"
]