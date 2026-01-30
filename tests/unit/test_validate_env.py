"""Tests for environment variable validation."""

import pytest

from scripts.validate_env import EnvValidationResult, validate_env


class TestValidateEnv:
    """Test environment variable validation."""

    def test_valid_env_passes(self):
        """All required variables set should pass validation."""
        env_vars = {
            "BINANCE_API_KEY": "test_api_key",
            "BINANCE_API_SECRET": "test_api_secret",
            "TELEGRAM_TOKEN": "123456:ABC-DEF",
            "TELEGRAM_CHAT_ID": "123456789",
            "JWT_SECRET_KEY": "jwt_secret_key",
            "API_PASSWORD": "api_password",
            "HEARTBEAT_URL": "https://heartbeat.example.com",
            "ENVIRONMENT": "live",
        }
        result = validate_env(env_vars, mode="live")
        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_binance_key_fails(self):
        """Missing BINANCE_API_KEY should fail in live mode."""
        env_vars = {
            "BINANCE_API_SECRET": "test_api_secret",
            "TELEGRAM_TOKEN": "123456:ABC-DEF",
            "TELEGRAM_CHAT_ID": "123456789",
            "JWT_SECRET_KEY": "jwt_secret_key",
            "API_PASSWORD": "api_password",
            "HEARTBEAT_URL": "https://heartbeat.example.com",
            "ENVIRONMENT": "live",
        }
        result = validate_env(env_vars, mode="live")
        assert result.valid is False
        assert any("BINANCE_API_KEY" in err for err in result.errors)

    def test_placeholder_value_fails(self):
        """Placeholder values should fail validation."""
        env_vars = {
            "BINANCE_API_KEY": "your_api_key_here",
            "BINANCE_API_SECRET": "test_api_secret",
            "TELEGRAM_TOKEN": "123456:ABC-DEF",
            "TELEGRAM_CHAT_ID": "123456789",
            "JWT_SECRET_KEY": "jwt_secret_key",
            "API_PASSWORD": "api_password",
            "HEARTBEAT_URL": "https://heartbeat.example.com",
            "ENVIRONMENT": "live",
        }
        result = validate_env(env_vars, mode="live")
        assert result.valid is False
        assert any("BINANCE_API_KEY" in err and "placeholder" in err for err in result.errors)

    def test_dry_run_mode_skips_binance_keys(self):
        """Binance API keys are optional in dry_run mode."""
        env_vars = {
            "TELEGRAM_TOKEN": "123456:ABC-DEF",
            "TELEGRAM_CHAT_ID": "123456789",
            "JWT_SECRET_KEY": "jwt_secret_key",
            "API_PASSWORD": "api_password",
            "HEARTBEAT_URL": "https://heartbeat.example.com",
            "ENVIRONMENT": "dry_run",
        }
        result = validate_env(env_vars, mode="dry_run")
        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_telegram_token_fails(self):
        """Missing TELEGRAM_TOKEN should fail."""
        env_vars = {
            "BINANCE_API_KEY": "test_api_key",
            "BINANCE_API_SECRET": "test_api_secret",
            "TELEGRAM_CHAT_ID": "123456789",
            "JWT_SECRET_KEY": "jwt_secret_key",
            "API_PASSWORD": "api_password",
            "HEARTBEAT_URL": "https://heartbeat.example.com",
            "ENVIRONMENT": "live",
        }
        result = validate_env(env_vars, mode="live")
        assert result.valid is False
        assert any("TELEGRAM_TOKEN" in err for err in result.errors)

    def test_multiple_missing_vars_reports_all(self):
        """Multiple missing variables should all be reported."""
        env_vars = {
            "BINANCE_API_KEY": "test_api_key",
            "BINANCE_API_SECRET": "test_api_secret",
            "ENVIRONMENT": "live",
        }
        result = validate_env(env_vars, mode="live")
        assert result.valid is False
        assert len(result.errors) >= 4

    def test_warnings_for_optional_vars(self):
        """Optional variables should generate warnings if missing."""
        env_vars = {
            "BINANCE_API_KEY": "test_api_key",
            "BINANCE_API_SECRET": "test_api_secret",
            "TELEGRAM_TOKEN": "123456:ABC-DEF",
            "TELEGRAM_CHAT_ID": "123456789",
            "JWT_SECRET_KEY": "jwt_secret_key",
            "API_PASSWORD": "api_password",
            "ENVIRONMENT": "live",
        }
        result = validate_env(env_vars, mode="live")
        assert result.valid is True
        assert len(result.warnings) >= 1
        assert any("HEARTBEAT_URL" in warn for warn in result.warnings)


class TestEnvValidationResult:
    """Test EnvValidationResult dataclass."""

    def test_env_validation_result_is_immutable(self):
        """EnvValidationResult should be immutable."""
        result = EnvValidationResult(valid=True, errors=(), warnings=())
        with pytest.raises(Exception):
            result.valid = False

    def test_errors_is_tuple(self):
        """Errors should be stored as tuple."""
        result = EnvValidationResult(valid=False, errors=("error1", "error2"), warnings=())
        assert isinstance(result.errors, tuple)
        assert len(result.errors) == 2

    def test_warnings_is_tuple(self):
        """Warnings should be stored as tuple."""
        result = EnvValidationResult(valid=True, errors=(), warnings=("warn1",))
        assert isinstance(result.warnings, tuple)
        assert len(result.warnings) == 1
