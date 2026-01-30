"""Environment variable validation for Freqtrade DCA bot."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EnvValidationResult:
    """Result of environment variable validation."""

    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def validate_config_env_consistency(
    config: dict[str, Any], env_vars: dict[str, str]
) -> tuple[str, ...]:
    """
    設定ファイルと環境変数の整合性を検証（純粋関数）

    configにハードコードされた秘密情報がある場合にエラーを返す。
    FREQTRADE__環境変数で上書きされる前提のため、configは空文字列であるべき。

    Args:
        config: 検証する設定辞書
        env_vars: 環境変数の辞書

    Returns:
        tuple[str, ...]: エラーメッセージのタプル
    """
    errors: list[str] = []

    # config内の秘密フィールドをチェック
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

        # 空文字列またはプレースホルダーは安全
        if _is_safe_value(value):
            continue

        # ハードコードされた秘密情報を検出
        errors.append(
            f"Config contains hardcoded secret in '{parent_key}.{field_key}'. "
            f"Use empty string in config and set FREQTRADE__{parent_key.upper()}__{field_key.upper()} "
            f"environment variable instead."
        )

    return tuple(errors)


def _is_safe_value(value: str) -> bool:
    """
    値が安全（空またはプレースホルダー）かどうかを判定

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


def validate_env(env_vars: dict[str, str], mode: str = "dry_run") -> EnvValidationResult:
    """Validate environment variables.

    Args:
        env_vars: Dictionary of environment variable names to values
        mode: Operating mode ('dry_run' or 'live')

    Returns:
        EnvValidationResult with validation status

    """
    errors = []
    warnings = []

    # Define required variables per mode
    required_common = [
        "TELEGRAM_TOKEN",
        "TELEGRAM_CHAT_ID",
        "JWT_SECRET_KEY",
        "API_PASSWORD",
    ]

    required_live_only = [
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
    ]

    optional_vars = [
        "HEARTBEAT_URL",
    ]

    # Placeholder patterns to detect
    placeholders = [
        "your_",
        "change_this_",
        "replace_",
        "example_",
    ]

    # Check required common variables
    for var in required_common:
        if var not in env_vars or not env_vars[var]:
            errors.append(f"Missing required environment variable: {var}")
        elif any(placeholder in env_vars[var].lower() for placeholder in placeholders):
            errors.append(
                f"Environment variable {var} contains placeholder value: {env_vars[var]}"
            )

    # Check live-mode-only variables
    if mode == "live":
        for var in required_live_only:
            if var not in env_vars or not env_vars[var]:
                errors.append(f"Missing required environment variable for live mode: {var}")
            elif any(placeholder in env_vars[var].lower() for placeholder in placeholders):
                errors.append(
                    f"Environment variable {var} contains placeholder value: {env_vars[var]}"
                )

    # Check optional variables
    for var in optional_vars:
        if var not in env_vars or not env_vars[var]:
            warnings.append(f"Optional environment variable not set: {var}")

    # Check ENVIRONMENT variable
    if "ENVIRONMENT" in env_vars:
        env_value = env_vars["ENVIRONMENT"]
        if env_value not in ("dry_run", "live"):
            errors.append(
                f"ENVIRONMENT must be 'dry_run' or 'live', got: {env_value}"
            )

    # Check FREQTRADE__ environment variables
    freqtrade_vars = [
        "FREQTRADE__TELEGRAM__TOKEN",
        "FREQTRADE__TELEGRAM__CHAT_ID",
        "FREQTRADE__API_SERVER__JWT_SECRET_KEY",
        "FREQTRADE__API_SERVER__PASSWORD",
        "FREQTRADE__API_SERVER__WS_TOKEN",
    ]

    missing_freqtrade_vars = [var for var in freqtrade_vars if var not in env_vars]
    if missing_freqtrade_vars:
        warnings.append(
            f"FREQTRADE__ environment variables not set: {', '.join(missing_freqtrade_vars)}. "
            "These override config file values and are recommended for secret management."
        )

    return EnvValidationResult(
        valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def main() -> int:
    """Main entry point for CLI usage."""
    # Load .env file
    env_file = Path(__file__).parent.parent / ".env"

    if not env_file.exists():
        print(f"Error: .env file not found at {env_file}")
        print("\nPlease create .env file from .env.example:")
        print("  cp .env.example .env")
        return 1

    # Parse .env file
    env_vars = {}
    with env_file.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip().strip('"').strip("'")

    # Determine mode
    mode = env_vars.get("ENVIRONMENT", "dry_run")

    # Validate
    result = validate_env(env_vars, mode=mode)

    # Print results
    if result.errors:
        print("VALIDATION FAILED\n")
        print("Errors:")
        for error in result.errors:
            print(f"  - {error}")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.valid:
        print("\n✓ Environment validation passed")
        return 0

    print("\n✗ Environment validation failed")
    print("\nPlease fix the errors above and try again.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
