"""
Freqtrade設定ファイル検証スクリプト

設定ファイルの必須フィールド、値の妥当性、取引所設定を検証する。
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    """
    検証結果を表すイミュータブルなデータクラス

    Attributes:
        is_valid: 検証が成功したかどうか
        errors: エラーメッセージのタプル
        warnings: 警告メッセージのタプル
    """
    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def check_hardcoded_secrets(config: dict[str, Any]) -> tuple[str, ...]:
    """
    設定ファイル内のハードコードされた秘密情報を検出（純粋関数）

    Args:
        config: 検証する設定辞書

    Returns:
        tuple[str, ...]: 検出されたハードコードされた秘密情報のエラーメッセージ
    """
    errors: list[str] = []

    # 検証対象のシークレットフィールド
    secret_fields = [
        ("telegram", "token"),
        ("telegram", "chat_id"),
        ("api_server", "password"),
        ("api_server", "jwt_secret_key"),
        ("api_server", "ws_token"),
        ("exchange", "key"),
        ("exchange", "secret"),
    ]

    for parent_key, field_key in secret_fields:
        if parent_key not in config:
            continue

        parent = config[parent_key]
        if not isinstance(parent, dict) or field_key not in parent:
            continue

        value = parent[field_key]
        if not isinstance(value, str):
            continue

        # 安全なパターン: 空文字列、プレースホルダー、サンプル値
        if _is_safe_secret_value(value):
            continue

        # ハードコードされた秘密情報を検出
        errors.append(
            f"Hardcoded secret detected in '{parent_key}.{field_key}'. "
            f"Use FREQTRADE__{parent_key.upper()}__{field_key.upper()} "
            f"environment variable instead."
        )

    return tuple(errors)


def _is_safe_secret_value(value: str) -> bool:
    """
    秘密情報の値が安全（プレースホルダーまたは空）かどうかを判定

    Args:
        value: 検証する値

    Returns:
        bool: 安全な値の場合True
    """
    # 空文字列
    if not value or value.strip() == "":
        return True

    # プレースホルダーパターン: ${VAR}
    if value.startswith("${"):
        return True

    # サンプル値パターン
    safe_prefixes = ("your_", "change_this_")
    if any(value.lower().startswith(prefix) for prefix in safe_prefixes):
        return True

    return False


def validate_config(config: dict[str, Any]) -> ValidationResult:
    """
    設定辞書の妥当性を検証（純粋関数）

    Args:
        config: 検証する設定辞書

    Returns:
        ValidationResult: 検証結果
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ハードコードされた秘密情報のチェック
    secret_errors = check_hardcoded_secrets(config)
    errors.extend(secret_errors)

    # 必須フィールドのチェック
    required_fields = ["max_open_trades", "stake_currency", "stake_amount", "dry_run"]
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")

    # max_open_tradesの検証
    if "max_open_trades" in config:
        max_open_trades = config["max_open_trades"]
        if not isinstance(max_open_trades, int) or max_open_trades <= 0:
            errors.append("max_open_trades must be a positive integer")

    # stake_amountの検証
    if "stake_amount" in config:
        stake_amount = config["stake_amount"]
        if not isinstance(stake_amount, (int, float)) or stake_amount <= 0:
            errors.append("stake_amount must be a positive number")

    # exchangeのpair_whitelistチェック
    if "exchange" in config and isinstance(config["exchange"], dict):
        if "pair_whitelist" in config["exchange"]:
            pair_whitelist = config["exchange"]["pair_whitelist"]
            if isinstance(pair_whitelist, list) and len(pair_whitelist) == 0:
                errors.append("exchange.pair_whitelist cannot be empty")

    # ライブモードでの高額ステーク警告
    if "dry_run" in config and "stake_amount" in config:
        if config["dry_run"] is False and config["stake_amount"] > 50000:
            warnings.append(
                f"Live mode with high stake_amount ({config['stake_amount']}). "
                "Please ensure this is intentional."
            )

    is_valid = len(errors) == 0
    return ValidationResult(
        is_valid=is_valid,
        errors=tuple(errors),
        warnings=tuple(warnings)
    )


def load_and_validate_config(config_path: str) -> ValidationResult:
    """
    設定ファイルを読み込んで検証

    Args:
        config_path: 設定ファイルのパス

    Returns:
        ValidationResult: 検証結果
    """
    path = Path(config_path)

    # ファイル存在チェック
    if not path.exists():
        return ValidationResult(
            is_valid=False,
            errors=(f"Config file not found: {config_path}",),
            warnings=()
        )

    # JSONパース
    try:
        with path.open('r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        return ValidationResult(
            is_valid=False,
            errors=(f"Invalid JSON syntax: {e}",),
            warnings=()
        )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            errors=(f"Error reading config file: {e}",),
            warnings=()
        )

    # 設定検証
    return validate_config(config)


def main() -> int:
    """
    CLI用エントリーポイント

    Returns:
        int: 終了コード（0=成功、1=失敗）
    """
    if len(sys.argv) < 2:
        print("Usage: python validate_config.py <config_file>", file=sys.stderr)
        return 1

    config_path = sys.argv[1]
    result = load_and_validate_config(config_path)

    # エラー出力
    if result.errors:
        print("Validation errors:", file=sys.stderr)
        for error in result.errors:
            print(f"  - {error}", file=sys.stderr)

    # 警告出力
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    # 結果出力
    if result.is_valid:
        print(f"✓ Config file '{config_path}' is valid")
        return 0
    else:
        print(f"✗ Config file '{config_path}' is invalid", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
