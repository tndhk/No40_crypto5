"""Freqtrade API client module.

Provides a common API communication layer for scripts that interact
with the Freqtrade REST API (check_dryrun_criteria.py, daily_report.py,
diagnose_bot.py, etc.).

All external HTTP communication is done via the requests library.
Configuration is loaded from environment variables or provided directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class ApiClientConfig:
    """Configuration for the Freqtrade API client.

    Attributes:
        base_url: Base URL of the Freqtrade API server.
        username: Username for API authentication.
        password: Password for API authentication. Empty string means no auth.
        timeout: Request timeout in seconds.

    """

    base_url: str = "http://127.0.0.1:8081"
    username: str = "freqtrader"
    password: str = ""
    timeout: int = 10


@dataclass(frozen=True)
class ApiResponse:
    """Standardized response from the Freqtrade API.

    Attributes:
        success: Whether the request succeeded.
        data: Response data (dict, list, or None on error).
        error: Error message (empty string on success).
        status_code: HTTP status code (0 if no response received).

    """

    success: bool
    data: dict | list | None
    error: str
    status_code: int


def load_api_config_from_env(env_vars: dict | None = None) -> ApiClientConfig:
    """Load API client configuration from environment variables.

    Reads FT_API_URL, FT_API_USERNAME, and FT_API_PASSWORD from the
    provided env_vars dict (or os.environ if None). Falls back to
    default values for any missing keys.

    Args:
        env_vars: Dictionary of environment variables. Uses os.environ if None.

    Returns:
        ApiClientConfig populated from environment variables.

    """
    if env_vars is None:
        env_vars = os.environ

    return ApiClientConfig(
        base_url=env_vars.get("FT_API_URL", "http://127.0.0.1:8081"),
        username=env_vars.get("FT_API_USERNAME", "freqtrader"),
        password=env_vars.get("FT_API_PASSWORD", ""),
    )


def _get_auth_token(config: ApiClientConfig) -> str | None:
    """Obtain a JWT token from the Freqtrade API via Basic Auth.

    Posts credentials to /api/v1/token/login using HTTP Basic Auth.
    If the password is empty, authentication is skipped and None is returned.

    Args:
        config: API client configuration.

    Returns:
        JWT access token string, or None if password is empty or on error.

    """
    if not config.password:
        return None

    url = f"{config.base_url}/api/v1/token/login"
    try:
        response = requests.post(
            url,
            auth=(config.username, config.password),
            timeout=config.timeout,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
    except (requests.ConnectionError, requests.Timeout):
        pass

    return None


def make_authenticated_request(
    config: ApiClientConfig,
    endpoint: str,
    method: str = "GET",
    params: dict | None = None,
) -> ApiResponse:
    """Make an authenticated request to the Freqtrade API.

    If a password is configured, obtains a JWT token first and includes
    it as a Bearer token. If no password is set, makes an unauthenticated
    request (works on localhost without auth).

    Handles ConnectionError, Timeout, and HTTPError gracefully by returning
    an ApiResponse with success=False and the error message.

    Args:
        config: API client configuration.
        endpoint: API endpoint path (e.g., "/api/v1/ping").
        method: HTTP method (default "GET").
        params: Query parameters to include in the request.

    Returns:
        ApiResponse with the result of the request.

    """
    url = f"{config.base_url}{endpoint}"
    headers: dict[str, str] = {}

    # Obtain auth token if password is set
    if config.password:
        token = _get_auth_token(config)
        if token:
            headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            timeout=config.timeout,
        )
        response.raise_for_status()
        return ApiResponse(
            success=True,
            data=response.json(),
            error="",
            status_code=response.status_code,
        )
    except requests.ConnectionError as exc:
        return ApiResponse(
            success=False,
            data=None,
            error=str(exc),
            status_code=0,
        )
    except requests.Timeout as exc:
        return ApiResponse(
            success=False,
            data=None,
            error=str(exc),
            status_code=0,
        )
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 0
        return ApiResponse(
            success=False,
            data=None,
            error=str(exc),
            status_code=status_code,
        )


# ---------------------------------------------------------------------------
# Endpoint convenience functions
# ---------------------------------------------------------------------------


def fetch_ping(config: ApiClientConfig) -> ApiResponse:
    """Fetch /api/v1/ping to check API health."""
    return make_authenticated_request(config, "/api/v1/ping")


def fetch_trades(config: ApiClientConfig) -> ApiResponse:
    """Fetch /api/v1/trades to get trade history."""
    return make_authenticated_request(config, "/api/v1/trades")


def fetch_profit(config: ApiClientConfig) -> ApiResponse:
    """Fetch /api/v1/profit to get profit summary."""
    return make_authenticated_request(config, "/api/v1/profit")


def fetch_status(config: ApiClientConfig) -> ApiResponse:
    """Fetch /api/v1/status to get open trade status."""
    return make_authenticated_request(config, "/api/v1/status")


def fetch_balance(config: ApiClientConfig) -> ApiResponse:
    """Fetch /api/v1/balance to get wallet balance."""
    return make_authenticated_request(config, "/api/v1/balance")


def fetch_stats(config: ApiClientConfig) -> ApiResponse:
    """Fetch /api/v1/stats to get trading statistics."""
    return make_authenticated_request(config, "/api/v1/stats")


def fetch_show_config(config: ApiClientConfig) -> ApiResponse:
    """Fetch /api/v1/show_config to get current configuration."""
    return make_authenticated_request(config, "/api/v1/show_config")


def fetch_logs(config: ApiClientConfig, limit: int = 100) -> ApiResponse:
    """Fetch /api/v1/logs to get recent log entries.

    Args:
        config: API client configuration.
        limit: Maximum number of log entries to return (default 100).

    Returns:
        ApiResponse with log data.

    """
    return make_authenticated_request(config, "/api/v1/logs", params={"limit": limit})
