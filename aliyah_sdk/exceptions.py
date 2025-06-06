class MultiSessionException(Exception):
    def __init__(self, message):
        super().__init__(message)


class NoSessionException(Exception):
    def __init__(self, message="No session found"):
        super().__init__(message)


class NoApiKeyException(Exception):
    def __init__(
        self,
        message="Could not initialize Aaliyah client - API Key is missing."
        + "\n\t    Find your API key at https://app.mensterra.com/api-keys",
    ):
        super().__init__(message)


class InvalidApiKeyException(Exception):
    def __init__(self, api_key, endpoint):
        message = f"API Key is invalid: {{{api_key}}}.\n\t    Find your API key at {endpoint}/api-keys"
        super().__init__(message)


class ApiServerException(Exception):
    def __init__(self, message):
        super().__init__(message)


class AaliyahClientNotInitializedException(RuntimeError):
    def __init__(self, message="Aaliyah client must be initialized before using this feature"):
        super().__init__(message)


class AaliyahApiJwtExpiredException(Exception):
    def __init__(self, message="JWT token has expired"):
        super().__init__(message)
