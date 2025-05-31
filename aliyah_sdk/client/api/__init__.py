"""
API client for the Aaliyah Ops API.

This module provides the client for the Aaliyah Ops API.
"""

from typing import Dict, Type, TypeVar, cast

from aliyah_sdk.client.api.base import BaseApiClient
from aliyah_sdk.client.api.types import AuthTokenResponse
from aliyah_sdk.client.api.versions.v1 import V1Client

# Define a type variable for client classes
T = TypeVar("T", bound=BaseApiClient)

__all__ = ["ApiClient", "BaseApiClient", "AuthTokenResponse"]


class ApiClient:
    """
    Master API client that contains all version-specific clients.

    This client provides a unified interface for accessing different API versions.
    It lazily initializes version-specific clients when they are first accessed.
    """

    def __init__(self, endpoint: str = "https://api.mensterra.com"):
        """
        Initialize the master API client.

        Args:
            endpoint: The base URL for the API
        """
        self.endpoint = endpoint
        self._clients: Dict[str, BaseApiClient] = {}

    @property
    def v1(self) -> V1Client:
        """
        Get the V1 API client.

        Returns:
            The V1 API client
        """
        return self._get_client("v1", V1Client)

    def _get_client(self, version: str, client_class: Type[T]) -> T:
        """
        Get or create a version-specific client.

        Args:
            version: The API version
            client_class: The client class to instantiate

        Returns:
            The version-specific client
        """
        if version not in self._clients:
            self._clients[version] = client_class(self.endpoint)
        return cast(T, self._clients[version])
