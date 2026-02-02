"""Tests for Freqtrade API client module."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from scripts.freqtrade_api_client import (
    ApiClientConfig,
    ApiResponse,
    _get_auth_token,
    fetch_balance,
    fetch_logs,
    fetch_ping,
    fetch_profit,
    fetch_show_config,
    fetch_stats,
    fetch_status,
    fetch_trades,
    load_api_config_from_env,
    make_authenticated_request,
)


class TestApiClientConfig:
    """Test ApiClientConfig dataclass."""

    def test_default_values(self):
        """ApiClientConfig should have sensible defaults."""
        config = ApiClientConfig()
        assert config.base_url == "http://127.0.0.1:8081"
        assert config.username == "freqtrader"
        assert config.password == ""
        assert config.timeout == 10

    def test_custom_values(self):
        """ApiClientConfig should accept custom values."""
        config = ApiClientConfig(
            base_url="http://localhost:9090",
            username="admin",
            password="secret",
            timeout=30,
        )
        assert config.base_url == "http://localhost:9090"
        assert config.username == "admin"
        assert config.password == "secret"
        assert config.timeout == 30

    def test_immutability(self):
        """ApiClientConfig should be immutable (frozen dataclass)."""
        config = ApiClientConfig()
        with pytest.raises(Exception):
            config.base_url = "http://other:8080"


class TestApiResponse:
    """Test ApiResponse dataclass."""

    def test_success_response(self):
        """ApiResponse should store success state."""
        resp = ApiResponse(success=True, data={"status": "ok"}, error="", status_code=200)
        assert resp.success is True
        assert resp.data == {"status": "ok"}
        assert resp.error == ""
        assert resp.status_code == 200

    def test_error_response(self):
        """ApiResponse should store error state."""
        resp = ApiResponse(success=False, data=None, error="Connection refused", status_code=0)
        assert resp.success is False
        assert resp.data is None
        assert resp.error == "Connection refused"
        assert resp.status_code == 0

    def test_immutability(self):
        """ApiResponse should be immutable (frozen dataclass)."""
        resp = ApiResponse(success=True, data={}, error="", status_code=200)
        with pytest.raises(Exception):
            resp.success = False


class TestLoadApiConfigFromEnv:
    """Test load_api_config_from_env function."""

    def test_loads_from_env_vars(self):
        """Should load config from provided env_vars dict."""
        env = {
            "FT_API_URL": "http://remote:8082",
            "FT_API_USERNAME": "myuser",
            "FT_API_PASSWORD": "mypass",
        }
        config = load_api_config_from_env(env_vars=env)
        assert config.base_url == "http://remote:8082"
        assert config.username == "myuser"
        assert config.password == "mypass"

    def test_defaults_when_env_vars_empty(self):
        """Should use defaults when env_vars has no relevant keys."""
        config = load_api_config_from_env(env_vars={})
        assert config.base_url == "http://127.0.0.1:8081"
        assert config.username == "freqtrader"
        assert config.password == ""

    def test_partial_env_vars(self):
        """Should use defaults for missing keys."""
        env = {"FT_API_PASSWORD": "onlypass"}
        config = load_api_config_from_env(env_vars=env)
        assert config.base_url == "http://127.0.0.1:8081"
        assert config.username == "freqtrader"
        assert config.password == "onlypass"

    def test_uses_os_environ_when_none(self):
        """Should use os.environ when env_vars is None."""
        with patch.dict(
            "os.environ",
            {"FT_API_URL": "http://env:1234"},
            clear=False,
        ):
            config = load_api_config_from_env(env_vars=None)
            assert config.base_url == "http://env:1234"


class TestGetAuthToken:
    """Test _get_auth_token function."""

    def test_returns_none_when_password_empty(self):
        """Should return None when password is empty."""
        config = ApiClientConfig(password="")
        result = _get_auth_token(config)
        assert result is None

    @patch("scripts.freqtrade_api_client.requests.post")
    def test_returns_token_on_success(self, mock_post):
        """Should return JWT token on successful login."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "jwt-token-123"}
        mock_post.return_value = mock_response

        config = ApiClientConfig(password="mypassword")
        token = _get_auth_token(config)

        assert token == "jwt-token-123"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/api/v1/token/login" in call_args[0][0] or "/api/v1/token/login" in str(call_args)

    @patch("scripts.freqtrade_api_client.requests.post")
    def test_returns_none_on_connection_error(self, mock_post):
        """Should return None on connection error."""
        mock_post.side_effect = requests.ConnectionError("Connection refused")

        config = ApiClientConfig(password="mypassword")
        token = _get_auth_token(config)

        assert token is None


class TestMakeAuthenticatedRequest:
    """Test make_authenticated_request function."""

    @patch("scripts.freqtrade_api_client.requests.request")
    def test_unauthenticated_request_success(self, mock_request):
        """Should make request without auth when password is empty."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "pong"}
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        config = ApiClientConfig(password="")
        result = make_authenticated_request(config, "/api/v1/ping")

        assert result.success is True
        assert result.data == {"status": "pong"}
        assert result.status_code == 200
        assert result.error == ""

        # Verify no Authorization header
        call_kwargs = mock_request.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert "Authorization" not in headers

    @patch("scripts.freqtrade_api_client._get_auth_token")
    @patch("scripts.freqtrade_api_client.requests.request")
    def test_authenticated_request_success(self, mock_request, mock_get_token):
        """Should include Bearer token when password is set."""
        mock_get_token.return_value = "jwt-token-abc"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"trades": []}
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        config = ApiClientConfig(password="secret")
        result = make_authenticated_request(config, "/api/v1/trades")

        assert result.success is True
        assert result.data == {"trades": []}

        # Verify Authorization header
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer jwt-token-abc"

    @patch("scripts.freqtrade_api_client.requests.request")
    def test_connection_error(self, mock_request):
        """Should return error ApiResponse on ConnectionError."""
        mock_request.side_effect = requests.ConnectionError("Connection refused")

        config = ApiClientConfig(password="")
        result = make_authenticated_request(config, "/api/v1/ping")

        assert result.success is False
        assert "Connection refused" in result.error
        assert result.status_code == 0
        assert result.data is None

    @patch("scripts.freqtrade_api_client.requests.request")
    def test_timeout_error(self, mock_request):
        """Should return error ApiResponse on Timeout."""
        mock_request.side_effect = requests.Timeout("Request timed out")

        config = ApiClientConfig(password="")
        result = make_authenticated_request(config, "/api/v1/ping")

        assert result.success is False
        assert "timed out" in result.error.lower() or "Timeout" in result.error
        assert result.status_code == 0

    @patch("scripts.freqtrade_api_client.requests.request")
    def test_http_error(self, mock_request):
        """Should return error ApiResponse on HTTPError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        http_error = requests.HTTPError("401 Unauthorized")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_request.return_value = mock_response

        config = ApiClientConfig(password="")
        result = make_authenticated_request(config, "/api/v1/ping")

        assert result.success is False
        assert result.status_code == 401
        assert "401" in result.error or "Unauthorized" in result.error

    @patch("scripts.freqtrade_api_client.requests.request")
    def test_request_with_params(self, mock_request):
        """Should pass params to the request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"logs": []}
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        config = ApiClientConfig(password="")
        result = make_authenticated_request(config, "/api/v1/logs", params={"limit": 50})

        assert result.success is True
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"] == {"limit": 50}


class TestEndpointFunctions:
    """Test endpoint convenience functions."""

    @patch("scripts.freqtrade_api_client.make_authenticated_request")
    def test_fetch_ping(self, mock_req):
        """fetch_ping should call /api/v1/ping."""
        mock_req.return_value = ApiResponse(
            success=True, data={"status": "pong"}, error="", status_code=200
        )
        config = ApiClientConfig()
        result = fetch_ping(config)

        assert result.success is True
        mock_req.assert_called_once_with(config, "/api/v1/ping")

    @patch("scripts.freqtrade_api_client.make_authenticated_request")
    def test_fetch_trades(self, mock_req):
        """fetch_trades should call /api/v1/trades."""
        mock_req.return_value = ApiResponse(
            success=True, data={"trades": []}, error="", status_code=200
        )
        config = ApiClientConfig()
        result = fetch_trades(config)

        assert result.success is True
        mock_req.assert_called_once_with(config, "/api/v1/trades")

    @patch("scripts.freqtrade_api_client.make_authenticated_request")
    def test_fetch_profit(self, mock_req):
        """fetch_profit should call /api/v1/profit."""
        mock_req.return_value = ApiResponse(
            success=True, data={"profit": 1000}, error="", status_code=200
        )
        config = ApiClientConfig()
        result = fetch_profit(config)

        assert result.success is True
        mock_req.assert_called_once_with(config, "/api/v1/profit")

    @patch("scripts.freqtrade_api_client.make_authenticated_request")
    def test_fetch_status(self, mock_req):
        """fetch_status should call /api/v1/status."""
        mock_req.return_value = ApiResponse(success=True, data=[], error="", status_code=200)
        config = ApiClientConfig()
        result = fetch_status(config)

        assert result.success is True
        mock_req.assert_called_once_with(config, "/api/v1/status")

    @patch("scripts.freqtrade_api_client.make_authenticated_request")
    def test_fetch_balance(self, mock_req):
        """fetch_balance should call /api/v1/balance."""
        mock_req.return_value = ApiResponse(
            success=True, data={"currencies": []}, error="", status_code=200
        )
        config = ApiClientConfig()
        result = fetch_balance(config)

        assert result.success is True
        mock_req.assert_called_once_with(config, "/api/v1/balance")

    @patch("scripts.freqtrade_api_client.make_authenticated_request")
    def test_fetch_stats(self, mock_req):
        """fetch_stats should call /api/v1/stats."""
        mock_req.return_value = ApiResponse(success=True, data={}, error="", status_code=200)
        config = ApiClientConfig()
        result = fetch_stats(config)

        assert result.success is True
        mock_req.assert_called_once_with(config, "/api/v1/stats")

    @patch("scripts.freqtrade_api_client.make_authenticated_request")
    def test_fetch_show_config(self, mock_req):
        """fetch_show_config should call /api/v1/show_config."""
        mock_req.return_value = ApiResponse(
            success=True, data={"trading_mode": "spot"}, error="", status_code=200
        )
        config = ApiClientConfig()
        result = fetch_show_config(config)

        assert result.success is True
        mock_req.assert_called_once_with(config, "/api/v1/show_config")

    @patch("scripts.freqtrade_api_client.make_authenticated_request")
    def test_fetch_logs_default_limit(self, mock_req):
        """fetch_logs should call /api/v1/logs with default limit=100."""
        mock_req.return_value = ApiResponse(
            success=True, data={"logs": []}, error="", status_code=200
        )
        config = ApiClientConfig()
        result = fetch_logs(config)

        assert result.success is True
        mock_req.assert_called_once_with(config, "/api/v1/logs", params={"limit": 100})

    @patch("scripts.freqtrade_api_client.make_authenticated_request")
    def test_fetch_logs_custom_limit(self, mock_req):
        """fetch_logs should pass custom limit parameter."""
        mock_req.return_value = ApiResponse(
            success=True, data={"logs": []}, error="", status_code=200
        )
        config = ApiClientConfig()
        result = fetch_logs(config, limit=50)

        assert result.success is True
        mock_req.assert_called_once_with(config, "/api/v1/logs", params={"limit": 50})
