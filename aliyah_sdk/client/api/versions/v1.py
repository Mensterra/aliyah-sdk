"""
API client for the Aaliyah Ops API.

This module provides the client for the V1 version of the Aaliyah Ops API.
"""

from typing import Optional, Union, Dict

import logging
logger = logging.getLogger(__name__)

from aliyah_sdk.client.api.base import BaseApiClient
from aliyah_sdk.exceptions import ApiServerException
from aliyah_sdk.client.api.types import AuthTokenResponse, UploadedObjectResponse


class V1Client(BaseApiClient):
    """Client for the Aaliyah Ops V1 API"""

    auth_token: str

    def __init__(self, *args, **kwargs):
        """Initialize V1Client with flexible arguments"""
        super().__init__(*args, **kwargs)  # Pass all arguments to parent
        self.auth_token = None

    def fetch_auth_token(self, api_key: str) -> AuthTokenResponse:
        path = "/v1/auth/token"
        data = {"api_key": api_key}
        headers = self.prepare_headers()

        r = self.post(path, data, headers)

        try:
            if r.status_code != 200:
                error_msg = f"Authentication failed: {r.status_code}"
                try:
                    error_data = r.json()
                    if "error" in error_data:
                        error_msg = f"{error_data['error']}"
                except Exception:
                    pass
                raise ApiServerException(error_msg)

            try:
                jr = r.json()
                token = jr.get("token")
                if not token:
                    raise ApiServerException("No token in authentication response")

                return jr
            except Exception as e:
                raise ApiServerException(f"Failed to process authentication response: {str(e)}")
        except Exception as e:
            logger.error(f"{str(e)} - Perhaps an invalid API key?")
            return None

    def set_auth_token(self, token: str):
        """
        Set the authentication token for API requests.

        Args:
            token: The authentication token to set
        """
        self.auth_token = token

    def prepare_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare headers for API requests using direct API key"""
        headers = {}
        if self.auth_token:
            # Use X-API-Key header instead of Bearer token
            headers["X-API-Key"] = self.auth_token
        
        if custom_headers:
            headers.update(custom_headers)
        return headers

    # def prepare_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    #     """
    #     Prepare headers for API requests.

    #     Args:
    #         custom_headers: Additional headers to include
    #     Returns:
    #         Headers dictionary with standard headers and any custom headers
    #     """
    #     headers = {}
    #     if self.auth_token:
    #         headers["Authorization"] = f"Bearer {self.auth_token}"
        
    #     if custom_headers:
    #         headers.update(custom_headers)
    #     return headers

    def upload_object(self, body: Union[str, bytes]) -> UploadedObjectResponse:
        """
        Upload an object to the API and return the response.

        Args:
            body: The object to upload, either as a string or bytes.
        Returns:
            UploadedObjectResponse: The response from the API after upload.
        """
        if isinstance(body, bytes):
            body = body.decode("utf-8")

        response = self.post("/v1/objects/upload/", body, self.prepare_headers())

        if response.status_code != 200:
            error_msg = f"Upload failed: {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = error_data["error"]
            except Exception:
                pass
            raise ApiServerException(error_msg)

        try:
            response_data = response.json()
            return UploadedObjectResponse(**response_data)
        except Exception as e:
            raise ApiServerException(f"Failed to process upload response: {str(e)}")

    def upload_logfile(self, body: Union[str, bytes], trace_id: int) -> UploadedObjectResponse:
        """
        Upload an log file to the API and return the response.

        Args:
            body: The log file to upload, either as a string or bytes.
        Returns:
            UploadedObjectResponse: The response from the API after upload.
        """
        if isinstance(body, bytes):
            body = body.decode("utf-8")

        response = self.post("/v1/logs/upload/", body, {**self.prepare_headers(), "Trace-Id": str(trace_id)})

        if response.status_code != 200:
            error_msg = f"Upload failed: {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = error_data["error"]
            except Exception:
                pass
            raise ApiServerException(error_msg)

        try:
            response_data = response.json()
            return UploadedObjectResponse(**response_data)
        except Exception as e:
            raise ApiServerException(f"Failed to process upload response: {str(e)}")