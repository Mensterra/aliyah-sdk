from typing import Dict, Optional

import requests

from aliyah_sdk.client.http.http_adapter import BaseHTTPAdapter
from aliyah_sdk.logging import logger


class HttpClient:
    """Base HTTP client with connection pooling and session management"""

    _session: Optional[requests.Session] = None
    _project_id: Optional[str] = None

    @classmethod
    def get_project_id(cls) -> Optional[str]:
        """Get the stored project ID"""
        return cls._project_id

    @classmethod
    def get_session(cls) -> requests.Session:
        """Get or create the global session with optimized connection pooling"""
        if cls._session is None:
            cls._session = requests.Session()

            # Configure connection pooling
            adapter = BaseHTTPAdapter()

            # Mount adapter for both HTTP and HTTPS
            cls._session.mount("http://", adapter)
            cls._session.mount("https://", adapter)

            # Set default headers
            cls._session.headers.update(
                {
                    "Connection": "keep-alive",
                    "Keep-Alive": "timeout=10, max=1000",
                    "Content-Type": "application/json",
                }
            )

        return cls._session

    @classmethod
    def request(
        cls,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: int = 30,
        max_redirects: int = 5,
    ) -> requests.Response:
        """
        Make a generic HTTP request

        Args:
            method: HTTP method (e.g., 'get', 'post', 'put', 'delete')
            url: Full URL for the request
            data: Request payload (for POST, PUT methods)
            headers: Request headers
            timeout: Request timeout in seconds
            max_redirects: Maximum number of redirects to follow (default: 5)

        Returns:
            Response from the API

        Raises:
            requests.RequestException: If the request fails
            ValueError: If the redirect limit is exceeded or an unsupported HTTP method is used
        """
        session = cls.get_session()
        method = method.lower()
        redirect_count = 0

        while redirect_count <= max_redirects:
            # Make the request with allow_redirects=False
            if method == "get":
                response = session.get(url, headers=headers, timeout=timeout, allow_redirects=False)
            elif method == "post":
                response = session.post(url, json=data, headers=headers, timeout=timeout, allow_redirects=False)
            elif method == "put":
                response = session.put(url, json=data, headers=headers, timeout=timeout, allow_redirects=False)
            elif method == "delete":
                response = session.delete(url, headers=headers, timeout=timeout, allow_redirects=False)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Check if we got a redirect response
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_count += 1

                if redirect_count > max_redirects:
                    raise ValueError(f"Exceeded maximum number of redirects ({max_redirects})")

                # Get the new location
                if "location" not in response.headers:
                    # No location header, can't redirect
                    return response

                # Update URL to the redirect location
                url = response.headers["location"]

                # For 303 redirects, always use GET for the next request
                if response.status_code == 303:
                    method = "get"
                    data = None

                logger.debug(f"Following redirect ({redirect_count}/{max_redirects}) to: {url}")

                # Continue the loop to make the next request
                continue

            # Not a redirect, return the response
            return response

        # This should never be reached due to the max_redirects check above
        return response
