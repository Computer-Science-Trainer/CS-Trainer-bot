"""
Shared API client and helper functions for HTTP requests.
"""
import httpx
import os
import logging
from httpx import HTTPStatusError

BASE_URL = os.getenv("BACKEND_URL", "https://cs-trainer.ru/api/")

client = httpx.AsyncClient(base_url=BASE_URL, timeout=10)


async def api_post(endpoint: str, data: dict, jwt_token: str = None) -> dict:
    """Helper to call backend POST endpoints with optional JWT token."""
    headers = {"Authorization": f"Bearer {jwt_token}"} if jwt_token else {}
    try:
        response = await client.post(endpoint, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except HTTPStatusError as exc:
        logging.error(
            "API POST failed for %s (token %s): %s",
            endpoint,
            jwt_token,
            exc)
        raise


async def api_get(endpoint: str, params: dict = None,
                  jwt_token: str = None) -> dict:
    """Helper to call backend GET endpoints with optional JWT token."""
    headers = {"Authorization": f"Bearer {jwt_token}"} if jwt_token else {}
    try:
        response = await client.get(endpoint, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except HTTPStatusError as exc:
        logging.error(
            "API GET failed for %s (token %s): %s",
            endpoint,
            jwt_token,
            exc)
        raise
