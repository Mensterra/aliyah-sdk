import atexit

from aliyah_sdk.client.api import ApiClient
from aliyah_sdk.exceptions import NoApiKeyException
from aliyah_sdk.logging import logger
from aliyah_sdk.logging.config import configure_logging, intercept_opentelemetry_logging
from aliyah_sdk.sdk.core import TracingCore
from aliyah_sdk.config import Config

# Global registry for active session
_active_session = None

# Single atexit handler registered flag
_atexit_registered = False


def _end_active_session():
    """Global handler to end the active session during shutdown"""
    global _active_session
    if _active_session is not None:
        logger.debug("Auto-ending active session during shutdown")
        try:
            from aliyah_sdk.legacy import end_session

            end_session(_active_session)
        except Exception as e:
            logger.warning(f"Error ending active session during shutdown: {e}")
            # Final fallback: try to end the span directly
            try:
                if hasattr(_active_session, "span") and hasattr(_active_session.span, "end"):
                    _active_session.span.end()
            except:
                pass


class Client:
    """Singleton client for AgentOps service"""

    config: Config
    _initialized: bool
    __instance = None  # Class variable for singleton pattern

    api: ApiClient

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(Client, cls).__new__(cls)
        return cls.__instance

    def __init__(self):
        # Only initialize once
        self._initialized = False
        self.config = Config()

    def init(self, **kwargs):
        try:
            self.config = Config()
        
            # Extract agent_id and agent_name before passing to Config.configure
            agent_id = kwargs.pop('agent_id', None)
            agent_name = kwargs.pop('agent_name', None)
            
            # Store them in the config instance
            if agent_id is not None:
                self.config.agent_id = agent_id
            if agent_name is not None:
                self.config.agent_name = agent_name
            
            # Configure with remaining kwargs (including instrument_llm_calls)
            Config.configure(**kwargs)
            
            if not Config.api_key:
                raise NoApiKeyException

            configure_logging(Config)
            intercept_opentelemetry_logging()

            self.api = ApiClient(Config.endpoint)
            self.api.v1.set_auth_token(Config.api_key)
            
            project_response = {
                "token": Config.api_key,
                "project_id": "default"
            }

            # 🔥 IMPORTANT: Pass the config instance, not just individual params
            # This ensures instrument_llm_calls gets picked up
            TracingCore.initialize_from_config(
                self.config,  # Pass the entire config
                jwt=project_response["token"], 
                project_id=project_response.get("project_id"),
                agent_id=agent_id,
                agent_name=agent_name
            )

            self._initialized = True  

            global _atexit_registered
            if not _atexit_registered:
                atexit.register(self.shutdown)
                _atexit_registered = True

            session = None
            if self.config.auto_start_session:
                from aliyah_sdk.legacy import start_session  # Fixed import

                # Include agent_id and agent_name in session tags
                session_tags = list(self.config.default_tags) if self.config.default_tags else []
                if agent_id:
                    session_tags.append(f"agent_id:{agent_id}")
                if agent_name:
                    session_tags.append(f"agent_name:{agent_name}")
                    
                session = start_session(tags=session_tags)

                global _active_session
                _active_session = session

            return session

        except Exception as e:
            self._initialized = False
            raise e

    def configure(self, **kwargs):
        """Update client configuration"""
        self.config.configure(**kwargs)

    def shutdown(self):
        print("DEBUG Client.shutdown: Shutting down TracingCore...") # Debug print
        TracingCore.get_instance().shutdown()
        # Add any other client-level cleanup here
        print("DEBUG Client.shutdown: Client shutdown complete.") # Debug print

    @property
    def initialized(self) -> bool:
        return self._initialized

    @initialized.setter
    def initialized(self, value: bool):
        if self._initialized and self._initialized != value:
            raise ValueError("Client already initialized")
        self._initialized = value

    # ------------------------------------------------------------
    __instance = None
