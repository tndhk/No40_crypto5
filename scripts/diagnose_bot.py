"""
Bot diagnostic script.

Runs comprehensive health checks on the Freqtrade bot:
process status, API server, database integrity, log freshness,
environment variables, Telegram token, DB path consistency, and open trades.
"""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.freqtrade_api_client import (
    ApiClientConfig,
    fetch_ping,
    load_api_config_from_env,
)


@dataclass(frozen=True)
class DiagnosticResult:
    """Single diagnostic check result."""

    name: str
    status: str  # "OK", "WARNING", "ERROR"
    message: str


@dataclass(frozen=True)
class DiagnosticReport:
    """Aggregated diagnostic report."""

    results: tuple[DiagnosticResult, ...]
    overall_status: str  # "HEALTHY", "DEGRADED", "UNHEALTHY"


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------


def check_process_running() -> DiagnosticResult:
    """Check whether the freqtrade trade process is running."""
    try:
        proc = subprocess.run(
            ["pgrep", "-f", "freqtrade trade"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return DiagnosticResult(
                name="process", status="OK", message="freqtrade process is running"
            )
        return DiagnosticResult(
            name="process", status="ERROR", message="freqtrade process not found"
        )
    except Exception as exc:
        return DiagnosticResult(
            name="process", status="ERROR", message=f"Process check failed: {exc}"
        )


def check_api_server(config: ApiClientConfig) -> DiagnosticResult:
    """Check whether the API server responds to ping."""
    try:
        resp = fetch_ping(config)
        if resp.success:
            return DiagnosticResult(
                name="api_server",
                status="OK",
                message="API server responded (pong)",
            )
        return DiagnosticResult(
            name="api_server",
            status="ERROR",
            message=f"API server unreachable: {resp.error}",
        )
    except Exception as exc:
        return DiagnosticResult(
            name="api_server",
            status="ERROR",
            message=f"API server check failed: {exc}",
        )


def check_database(db_path: str) -> DiagnosticResult:
    """Check database existence, size, integrity, and trade count."""
    path = Path(db_path)

    if not path.exists():
        return DiagnosticResult(
            name="database", status="ERROR", message=f"Database not found: {db_path}"
        )

    if path.stat().st_size == 0:
        return DiagnosticResult(
            name="database", status="ERROR", message=f"Database is 0 bytes: {db_path}"
        )

    try:
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()

            # Integrity check
            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()[0]
            if integrity != "ok":
                return DiagnosticResult(
                    name="database",
                    status="ERROR",
                    message=f"Integrity check failed: {integrity}",
                )

            # Check trades table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
            if cursor.fetchone() is None:
                return DiagnosticResult(
                    name="database",
                    status="ERROR",
                    message="trades table not found",
                )

            # Count trades
            cursor.execute("SELECT COUNT(*) FROM trades")
            count = cursor.fetchone()[0]

            return DiagnosticResult(
                name="database",
                status="OK",
                message=f"Database OK, {count} trades found",
            )
        finally:
            conn.close()
    except Exception as exc:
        return DiagnosticResult(name="database", status="ERROR", message=f"Database error: {exc}")


def check_log_freshness(log_path: str, max_age_minutes: int = 10) -> DiagnosticResult:
    """Check whether the log file has been recently modified."""
    path = Path(log_path)

    if not path.exists():
        return DiagnosticResult(
            name="log_freshness",
            status="ERROR",
            message=f"Log file not found: {log_path}",
        )

    mtime = path.stat().st_mtime
    age_seconds = time.time() - mtime
    age_minutes = age_seconds / 60

    if age_minutes <= max_age_minutes:
        return DiagnosticResult(
            name="log_freshness",
            status="OK",
            message=f"Log updated {age_minutes:.1f} minutes ago",
        )

    return DiagnosticResult(
        name="log_freshness",
        status="WARNING",
        message=f"Log is {age_minutes:.1f} minutes old (threshold: {max_age_minutes})",
    )


def check_env_variables(env_vars: dict | None = None) -> DiagnosticResult:
    """Check required FREQTRADE__ environment variables."""
    if env_vars is None:
        env_vars = dict(os.environ)

    required = [
        "FREQTRADE__TELEGRAM__TOKEN",
        "FREQTRADE__API_SERVER__PASSWORD",
        "FREQTRADE__API_SERVER__JWT_SECRET_KEY",
    ]

    missing = [var for var in required if var not in env_vars]

    if not missing:
        return DiagnosticResult(
            name="env_variables",
            status="OK",
            message="All required environment variables are set",
        )

    return DiagnosticResult(
        name="env_variables",
        status="WARNING",
        message=f"Missing environment variables: {', '.join(missing)}",
    )


def check_telegram_token(env_vars: dict | None = None) -> DiagnosticResult:
    """Validate Telegram token format."""
    if env_vars is None:
        env_vars = dict(os.environ)

    token = env_vars.get("FREQTRADE__TELEGRAM__TOKEN")

    if token is None:
        return DiagnosticResult(
            name="telegram_token",
            status="WARNING",
            message="FREQTRADE__TELEGRAM__TOKEN is not set",
        )

    pattern = r"^[0-9]+:[A-Za-z0-9_-]+$"
    if re.match(pattern, token):
        return DiagnosticResult(
            name="telegram_token",
            status="OK",
            message="Telegram token format is valid",
        )

    return DiagnosticResult(
        name="telegram_token",
        status="ERROR",
        message="Telegram token format is invalid",
    )


def check_db_path_consistency(project_root: str) -> DiagnosticResult:
    """Check for ghost database files (0-byte in user_data, real data in root)."""
    user_data_db = Path(project_root) / "user_data" / "tradesv3.dryrun.sqlite"
    root_db = Path(project_root) / "tradesv3.dryrun.sqlite"

    user_data_exists = user_data_db.exists()
    root_exists = root_db.exists()

    # Ghost file scenario: user_data has 0-byte file AND root has real data
    if user_data_exists and user_data_db.stat().st_size == 0 and root_exists:
        root_size = root_db.stat().st_size
        if root_size > 0:
            return DiagnosticResult(
                name="db_path_consistency",
                status="WARNING",
                message=(
                    f"Ghost file detected: {user_data_db} is 0 bytes, "
                    f"but {root_db} has {root_size} bytes"
                ),
            )

    return DiagnosticResult(
        name="db_path_consistency",
        status="OK",
        message="No database path inconsistency detected",
    )


def check_open_trades(db_path: str) -> DiagnosticResult:
    """Check for stale open trades (older than 7 days)."""
    path = Path(db_path)

    if not path.exists():
        return DiagnosticResult(
            name="open_trades",
            status="ERROR",
            message=f"Database not found: {db_path}",
        )

    try:
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT id, pair, open_date FROM trades WHERE is_open = 1")
            open_trades = cursor.fetchall()
        finally:
            conn.close()

        if not open_trades:
            return DiagnosticResult(
                name="open_trades",
                status="OK",
                message="No open trades",
            )

        stale_threshold = datetime.now(timezone.utc) - timedelta(days=7)
        stale = []
        for trade_id, pair, open_date_str in open_trades:
            # Parse ISO format date, handling timezone-aware strings
            open_date = datetime.fromisoformat(open_date_str)
            if open_date.tzinfo is None:
                open_date = open_date.replace(tzinfo=timezone.utc)
            if open_date < stale_threshold:
                stale.append((trade_id, pair))

        if stale:
            stale_info = ", ".join(f"{pair}(id={tid})" for tid, pair in stale)
            return DiagnosticResult(
                name="open_trades",
                status="WARNING",
                message=f"Stale open trades (>7 days): {stale_info}",
            )

        return DiagnosticResult(
            name="open_trades",
            status="OK",
            message=f"{len(open_trades)} open trade(s), all within 7 days",
        )
    except Exception as exc:
        return DiagnosticResult(
            name="open_trades",
            status="ERROR",
            message=f"Open trade check failed: {exc}",
        )


# ---------------------------------------------------------------------------
# Aggregation and formatting
# ---------------------------------------------------------------------------


def run_all_diagnostics(project_root: str, api_config: ApiClientConfig) -> DiagnosticReport:
    """Run all diagnostic checks and produce an aggregated report."""
    db_path = str(Path(project_root) / "tradesv3.dryrun.sqlite")
    log_path = str(Path(project_root) / "user_data" / "logs" / "freqtrade.log")

    results = [
        check_process_running(),
        check_api_server(api_config),
        check_database(db_path),
        check_log_freshness(log_path),
        check_env_variables(),
        check_telegram_token(),
        check_db_path_consistency(project_root),
        check_open_trades(db_path),
    ]

    statuses = {r.status for r in results}

    if "ERROR" in statuses:
        overall = "UNHEALTHY"
    elif "WARNING" in statuses:
        overall = "DEGRADED"
    else:
        overall = "HEALTHY"

    return DiagnosticReport(results=tuple(results), overall_status=overall)


def format_diagnostic_report(report: DiagnosticReport) -> str:
    """Format a DiagnosticReport as human-readable text."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("Bot Diagnostic Report")
    lines.append("=" * 60)

    for r in report.results:
        prefix = f"[{r.status}]"
        lines.append(f"  {prefix:<12} {r.name}: {r.message}")

    lines.append("-" * 60)
    lines.append(f"Overall Status: {report.overall_status}")
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Run diagnostics and print report. Returns exit code."""
    project_root = str(Path(__file__).resolve().parent.parent)

    try:
        api_config = load_api_config_from_env()
    except Exception:
        api_config = ApiClientConfig(
            base_url="http://127.0.0.1:8081",
            username="freqtrader",
            password="",
        )

    report = run_all_diagnostics(project_root, api_config)
    output = format_diagnostic_report(report)
    print(output)

    if report.overall_status == "HEALTHY":
        return 0
    elif report.overall_status == "DEGRADED":
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
