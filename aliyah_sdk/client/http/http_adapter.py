from typing import Optional

from requests.adapters import HTTPAdapter
from urllib3.util import Retry


class BaseHTTPAdapter(HTTPAdapter):
    """Base HTTP adapter with enhanced connection pooling and retry logic"""

    def __init__(
        self,
        pool_connections: int = 15,
        pool_maxsize: int = 256,
        max_retries: Optional[Retry] = None,
    ):
        """
        Initialize the base HTTP adapter.

        Args:
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections to save in the pool
            max_retries: Retry configuration for failed requests
        """
        if max_retries is None:
            max_retries = Retry(
                total=3,
                backoff_factor=0.1,
                status_forcelist=[500, 502, 503, 504],
            )

        super().__init__(pool_connections=pool_connections, pool_maxsize=pool_maxsize, max_retries=max_retries)

