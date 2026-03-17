"""Tests for Freqtrade API client env loading."""

from unittest.mock import patch

from scripts.freqtrade_api_client import load_api_config_from_env


class TestLoadApiConfigFromEnv:
    """Test environment variable loading for API client."""

    def test_prefers_ft_api_variables(self):
        env = {
            "FT_API_URL": "http://10.0.0.2:9999",
            "FT_API_USERNAME": "alice",
            "FT_API_PASSWORD": "secret",
            "FREQTRADE__API_SERVER__PASSWORD": "ignored",
        }

        config = load_api_config_from_env(env)

        assert config.base_url == "http://10.0.0.2:9999"
        assert config.username == "alice"
        assert config.password == "secret"

    def test_falls_back_to_freqtrade_env_variables(self):
        env = {
            "FREQTRADE__API_SERVER__LISTEN_IP_ADDRESS": "0.0.0.0",
            "FREQTRADE__API_SERVER__LISTEN_PORT": "8081",
            "FREQTRADE__API_SERVER__USERNAME": "freqtrader",
            "FREQTRADE__API_SERVER__PASSWORD": "pw-from-freqtrade",
        }

        config = load_api_config_from_env(env)

        assert config.base_url == "http://127.0.0.1:8081"
        assert config.username == "freqtrader"
        assert config.password == "pw-from-freqtrade"

    def test_uses_defaults_when_env_missing(self):
        config = load_api_config_from_env({})

        assert config.base_url == "http://127.0.0.1:8081"
        assert config.username == "freqtrader"
        assert config.password == ""

    def test_loads_freqtrade_api_password_from_dotenv_when_env_missing(self):
        dotenv_values = {
            "FREQTRADE__API_SERVER__PASSWORD": "dotenv-pass",
            "FREQTRADE__API_SERVER__USERNAME": "dotenv-user",
            "FREQTRADE__API_SERVER__LISTEN_PORT": "8089",
        }

        with patch("scripts.freqtrade_api_client._load_dotenv_candidates", return_value=dotenv_values), patch.dict(
            "os.environ", {}, clear=True
        ):
            config = load_api_config_from_env()

        assert config.base_url == "http://127.0.0.1:8089"
        assert config.username == "dotenv-user"
        assert config.password == "dotenv-pass"
