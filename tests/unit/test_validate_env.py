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


class TestFreqtradeEnvVars:
    """Test FREQTRADE__ environment variable validation."""

    def test_freqtrade_env_vars_present_passes(self):
        """FREQTRADE__環境変数が設定されている場合はパス"""
        env_vars = {
            "TELEGRAM_TOKEN": "123456:ABC-DEF",
            "TELEGRAM_CHAT_ID": "123456789",
            "JWT_SECRET_KEY": "jwt_secret",
            "API_PASSWORD": "api_pass",
            "FREQTRADE__TELEGRAM__TOKEN": "123456:ABC-DEF",
            "FREQTRADE__TELEGRAM__CHAT_ID": "123456789",
            "FREQTRADE__API_SERVER__JWT_SECRET_KEY": "jwt_secret",
            "FREQTRADE__API_SERVER__PASSWORD": "api_pass",
            "FREQTRADE__API_SERVER__WS_TOKEN": "ws_token",
        }

        result = validate_env(env_vars, mode="dry_run")

        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_freqtrade_env_vars_warns(self):
        """FREQTRADE__環境変数が欠落している場合は警告"""
        env_vars = {
            "TELEGRAM_TOKEN": "123456:ABC-DEF",
            "TELEGRAM_CHAT_ID": "123456789",
            "JWT_SECRET_KEY": "jwt_secret",
            "API_PASSWORD": "api_pass",
        }

        result = validate_env(env_vars, mode="dry_run")

        assert result.valid is True
        assert len(result.warnings) > 0
        assert any("FREQTRADE__" in warn for warn in result.warnings)

    def test_config_hardcoded_secret_with_env_cross_check_fails(self):
        """config内のハードコード秘密とenv変数の整合性チェック"""
        import json
        import tempfile
        from pathlib import Path

        config = {
            "telegram": {
                "token": "hardcoded_token_12345",
                "chat_id": "987654321"
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            env_vars = {
                "TELEGRAM_TOKEN": "123456:ABC-DEF",
                "TELEGRAM_CHAT_ID": "123456789",
                "JWT_SECRET_KEY": "jwt_secret",
                "API_PASSWORD": "api_pass",
            }

            from scripts.validate_env import validate_config_env_consistency
            errors = validate_config_env_consistency(config, env_vars)

            assert len(errors) > 0
            assert any("hardcoded" in error.lower() for error in errors)
        finally:
            Path(config_path).unlink()

    def test_empty_config_with_freqtrade_env_override_passes(self):
        """configが空文字列でFREQTRADE__変数がある場合はパス"""
        import json
        import tempfile
        from pathlib import Path

        config = {
            "telegram": {
                "token": "",
                "chat_id": ""
            },
            "api_server": {
                "jwt_secret_key": "",
                "password": "",
                "ws_token": ""
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            env_vars = {
                "TELEGRAM_TOKEN": "123456:ABC-DEF",
                "TELEGRAM_CHAT_ID": "123456789",
                "JWT_SECRET_KEY": "jwt_secret",
                "API_PASSWORD": "api_pass",
                "FREQTRADE__TELEGRAM__TOKEN": "123456:ABC-DEF",
                "FREQTRADE__TELEGRAM__CHAT_ID": "123456789",
            }

            from scripts.validate_env import validate_config_env_consistency
            errors = validate_config_env_consistency(config, env_vars)

            assert len(errors) == 0
        finally:
            Path(config_path).unlink()
