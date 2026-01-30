"""
設定ファイル検証のユニットテスト
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

from scripts.validate_config import (
    ValidationResult,
    check_hardcoded_secrets,
    load_and_validate_config,
    main,
    validate_config,
)


class TestValidationResult:
    """ValidationResultのテストスイート"""

    def test_validation_result_is_immutable(self):
        """ValidationResultはイミュータブル"""
        result = ValidationResult(is_valid=True, errors=(), warnings=())

        with pytest.raises(Exception):
            result.is_valid = False


class TestValidateConfig:
    """validate_config()のテストスイート"""

    def test_valid_dry_run_config_passes(self):
        """正常なDry Run設定は検証をパス"""
        config = {
            "max_open_trades": 2,
            "stake_currency": "JPY",
            "stake_amount": 10000,
            "dry_run": True,
        }

        result = validate_config(config)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_valid_backtest_config_passes(self):
        """正常なバックテスト設定は検証をパス"""
        config = {
            "max_open_trades": 2,
            "stake_currency": "JPY",
            "stake_amount": 10000,
            "dry_run": True,
            "fee": 0.0005,
        }

        result = validate_config(config)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_missing_required_fields_fails(self):
        """必須フィールド欠落時はエラー"""
        # max_open_tradesが欠落
        config = {
            "stake_currency": "JPY",
            "stake_amount": 10000,
            "dry_run": True,
        }

        result = validate_config(config)

        assert result.is_valid is False
        assert any("max_open_trades" in error for error in result.errors)

    def test_negative_stake_amount_fails(self):
        """負のステーク額はエラー"""
        config = {
            "max_open_trades": 2,
            "stake_currency": "JPY",
            "stake_amount": -10000,
            "dry_run": True,
        }

        result = validate_config(config)

        assert result.is_valid is False
        assert any("stake_amount" in error for error in result.errors)

    def test_zero_max_open_trades_fails(self):
        """最大オープントレード数が0はエラー"""
        config = {
            "max_open_trades": 0,
            "stake_currency": "JPY",
            "stake_amount": 10000,
            "dry_run": True,
        }

        result = validate_config(config)

        assert result.is_valid is False
        assert any("max_open_trades" in error for error in result.errors)

    def test_empty_pair_whitelist_fails(self):
        """空のペアホワイトリストはエラー"""
        config = {
            "max_open_trades": 2,
            "stake_currency": "JPY",
            "stake_amount": 10000,
            "dry_run": True,
            "exchange": {
                "pair_whitelist": []
            }
        }

        result = validate_config(config)

        assert result.is_valid is False
        assert any("pair_whitelist" in error for error in result.errors)

    def test_live_mode_high_stake_returns_warning(self):
        """ライブモードで高額ステークは警告"""
        config = {
            "max_open_trades": 2,
            "stake_currency": "JPY",
            "stake_amount": 100000,  # > 50000
            "dry_run": False,
        }

        result = validate_config(config)

        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("stake_amount" in warning for warning in result.warnings)


class TestLoadAndValidateConfig:
    """load_and_validate_config()のテストスイート"""

    def test_nonexistent_file_returns_error(self):
        """存在しないファイルはエラー"""
        result = load_and_validate_config("/nonexistent/path/config.json")

        assert result.is_valid is False
        assert any("not found" in error.lower() for error in result.errors)

    def test_invalid_json_returns_error(self):
        """不正なJSON構文はエラー"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{invalid json")
            temp_path = f.name

        try:
            result = load_and_validate_config(temp_path)

            assert result.is_valid is False
            assert any("json" in error.lower() for error in result.errors)
        finally:
            Path(temp_path).unlink()

    def test_loads_valid_config_file(self):
        """正常な設定ファイルを読み込み"""
        config = {
            "max_open_trades": 2,
            "stake_currency": "JPY",
            "stake_amount": 10000,
            "dry_run": True,
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            result = load_and_validate_config(temp_path)

            assert result.is_valid is True
            assert len(result.errors) == 0
        finally:
            Path(temp_path).unlink()


class TestValidateConfigMain:
    """Validate Config CLIメイン関数のテストスイート"""

    def test_main_with_valid_config(self, monkeypatch, capsys):
        """正常な設定ファイルで成功（終了コード0）"""
        config = {
            "max_open_trades": 2,
            "stake_currency": "JPY",
            "stake_amount": 10000,
            "dry_run": True,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            monkeypatch.setattr(sys, "argv", ["validate_config.py", temp_path])
            exit_code = main()

            assert exit_code == 0
            captured = capsys.readouterr()
            assert "is valid" in captured.out
        finally:
            Path(temp_path).unlink()

    def test_main_with_invalid_config(self, monkeypatch, capsys):
        """不正な設定ファイルで失敗（終了コード1）"""
        config = {
            "max_open_trades": 0,  # 不正な値
            "stake_currency": "JPY",
            "stake_amount": 10000,
            "dry_run": True,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            monkeypatch.setattr(sys, "argv", ["validate_config.py", temp_path])
            exit_code = main()

            assert exit_code == 1
            captured = capsys.readouterr()
            assert "is invalid" in captured.err
            assert "Validation errors:" in captured.err
        finally:
            Path(temp_path).unlink()

    def test_main_with_file_not_found(self, monkeypatch, capsys):
        """ファイルが存在しない場合は失敗（終了コード1）"""
        monkeypatch.setattr(
            sys, "argv", ["validate_config.py", "/nonexistent/path/config.json"]
        )
        exit_code = main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_main_with_invalid_json(self, monkeypatch, capsys):
        """不正なJSON形式の場合は失敗（終了コード1）"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            temp_path = f.name

        try:
            monkeypatch.setattr(sys, "argv", ["validate_config.py", temp_path])
            exit_code = main()

            assert exit_code == 1
            captured = capsys.readouterr()
            assert "json" in captured.err.lower()
        finally:
            Path(temp_path).unlink()

    def test_main_with_no_arguments(self, monkeypatch, capsys):
        """引数なしで実行すると使い方を表示して失敗（終了コード1）"""
        monkeypatch.setattr(sys, "argv", ["validate_config.py"])
        exit_code = main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Usage:" in captured.err

    def test_main_with_warnings(self, monkeypatch, capsys):
        """警告がある場合でも成功（終了コード0）だが警告を表示"""
        config = {
            "max_open_trades": 2,
            "stake_currency": "JPY",
            "stake_amount": 100000,  # 高額ステーク
            "dry_run": False,  # ライブモード
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            monkeypatch.setattr(sys, "argv", ["validate_config.py", temp_path])
            exit_code = main()

            assert exit_code == 0
            captured = capsys.readouterr()
            assert "Warnings:" in captured.out
            assert "is valid" in captured.out
        finally:
            Path(temp_path).unlink()


class TestCheckHardcodedSecrets:
    """check_hardcoded_secrets()のテストスイート"""

    def test_hardcoded_telegram_token_detected(self):
        """Telegramトークンのハードコードを検出"""
        config = {
            "telegram": {
                "token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
                "chat_id": "123456789"
            }
        }

        errors = check_hardcoded_secrets(config)

        assert len(errors) > 0
        assert any("telegram.token" in error for error in errors)

    def test_hardcoded_api_password_detected(self):
        """APIパスワードのハードコードを検出"""
        config = {
            "api_server": {
                "password": "my_secret_password_123"
            }
        }

        errors = check_hardcoded_secrets(config)

        assert len(errors) > 0
        assert any("api_server.password" in error for error in errors)

    def test_hardcoded_jwt_secret_detected(self):
        """JWT秘密鍵のハードコードを検出"""
        config = {
            "api_server": {
                "jwt_secret_key": "super_secret_jwt_key_xyz"
            }
        }

        errors = check_hardcoded_secrets(config)

        assert len(errors) > 0
        assert any("api_server.jwt_secret_key" in error for error in errors)

    def test_placeholder_value_passes(self):
        """プレースホルダー値は安全として扱う"""
        config = {
            "telegram": {
                "token": "${TELEGRAM_TOKEN}",
                "chat_id": "${TELEGRAM_CHAT_ID}"
            },
            "api_server": {
                "password": "your_password_here",
                "jwt_secret_key": "change_this_secret"
            }
        }

        errors = check_hardcoded_secrets(config)

        assert len(errors) == 0

    def test_empty_secret_field_passes(self):
        """空文字列のシークレットフィールドは安全"""
        config = {
            "telegram": {
                "token": "",
                "chat_id": ""
            },
            "api_server": {
                "password": "",
                "jwt_secret_key": "",
                "ws_token": ""
            },
            "exchange": {
                "key": "",
                "secret": ""
            }
        }

        errors = check_hardcoded_secrets(config)

        assert len(errors) == 0
