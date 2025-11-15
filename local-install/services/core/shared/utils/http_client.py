import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class HTTPClient:
    """HTTP client with retry logic and error handling"""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def post(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """POST request with error handling"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=json, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {url}: {e}")
            raise

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """GET request with error handling"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {url}: {e}")
            raise

    async def put(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """PUT request with error handling"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(url, json=json, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {url}: {e}")
            raise

    async def delete(
        self,
        endpoint: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """DELETE request with error handling"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(url, **kwargs)
                response.raise_for_status()

                # DELETE might return empty response
                if response.status_code == 204:
                    return None

                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {url}: {e}")
            raise