"""
設定ファイル検証のユニットテスト
"""

import json
import tempfile
from pathlib import Path

import pytest

from scripts.validate_config import ValidationResult, load_and_validate_config, validate_config


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
