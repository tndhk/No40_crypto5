"""Dry Run criteria evaluation for Freqtrade DCA bot."""

from __future__ import annotations

import json
import math
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from scripts.freqtrade_api_client import (
    ApiClientConfig,
    fetch_logs,
    fetch_trades,
    load_api_config_from_env,
)


@dataclass(frozen=True)
class DryRunMetrics:
    """Metrics collected during Dry Run."""

    uptime_percent: float
    api_error_rate: float
    order_accuracy: float
    sharpe_deviation: float
    days_running: int


@dataclass(frozen=True)
class DryRunCriteriaResult:
    """Result of Dry Run criteria evaluation."""

    passed: bool
    details: tuple[str, ...]


def evaluate_dryrun(metrics: DryRunMetrics) -> DryRunCriteriaResult:
    """Evaluate Dry Run metrics against acceptance criteria.

    Acceptance criteria:
    - Uptime >= 99%
    - API error rate < 1%
    - Order accuracy >= 98%
    - Sharpe ratio deviation <= 0.3
    - Running period >= 14 days

    Args:
        metrics: DryRunMetrics to evaluate

    Returns:
        DryRunCriteriaResult with pass/fail status and details

    """
    details = []
    passed = True

    # Check uptime
    if metrics.uptime_percent >= 99.0:
        details.append(f"✓ Uptime: {metrics.uptime_percent:.1f}% (>= 99%)")
    else:
        details.append(f"✗ Uptime: {metrics.uptime_percent:.1f}% (< 99%)")
        passed = False

    # Check API error rate
    if metrics.api_error_rate < 1.0:
        details.append(f"✓ API error rate: {metrics.api_error_rate:.2f}% (< 1%)")
    else:
        details.append(f"✗ API error rate: {metrics.api_error_rate:.2f}% (>= 1%)")
        passed = False

    # Check order accuracy
    if metrics.order_accuracy >= 98.0:
        details.append(f"✓ Order accuracy: {metrics.order_accuracy:.1f}% (>= 98%)")
    else:
        details.append(f"✗ Order accuracy: {metrics.order_accuracy:.1f}% (< 98%)")
        passed = False

    # Check Sharpe deviation
    if metrics.sharpe_deviation <= 0.3:
        details.append(f"✓ Sharpe deviation: {metrics.sharpe_deviation:.2f} (<= 0.3)")
    else:
        details.append(f"✗ Sharpe deviation: {metrics.sharpe_deviation:.2f} (> 0.3)")
        passed = False

    # Check days running
    if metrics.days_running >= 14:
        details.append(f"✓ Running period: {metrics.days_running} days (>= 14 days)")
    else:
        details.append(f"✗ Running period: {metrics.days_running} days (< 14 days)")
        passed = False

    # Add overall result
    if passed:
        details.append("\n✓ Dry Run PASSED - Ready for backtest")
    else:
        details.append("\n✗ Dry Run FAILED - Continue monitoring")

    return DryRunCriteriaResult(
        passed=passed,
        details=tuple(details),
    )


# ---------------------------------------------------------------------------
# Data collection functions
# ---------------------------------------------------------------------------

_LOG_TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"
_GAP_THRESHOLD_SECONDS = 300  # 5 minutes


def calculate_uptime_from_logs(log_entries: list[dict]) -> float:
    """Calculate uptime percentage from log entries.

    Examines timestamps in *log_entries* (each dict must contain a
    ``"timestamp"`` key).  Any consecutive gap larger than 5 minutes is
    considered downtime.

    Args:
        log_entries: List of log entry dicts with "timestamp" field.

    Returns:
        Uptime percentage (0.0 -- 100.0).  Returns 0.0 for empty or
        single-entry lists.

    """
    if len(log_entries) < 2:
        return 0.0

    timestamps: list[datetime] = []
    for entry in log_entries:
        ts_str = entry.get("timestamp", "")
        try:
            timestamps.append(datetime.strptime(ts_str, _LOG_TIMESTAMP_FMT))
        except (ValueError, TypeError):
            continue

    if len(timestamps) < 2:
        return 0.0

    timestamps.sort()

    total_span = (timestamps[-1] - timestamps[0]).total_seconds()
    if total_span <= 0:
        return 0.0

    gap_total = 0.0
    for i in range(1, len(timestamps)):
        diff = (timestamps[i] - timestamps[i - 1]).total_seconds()
        if diff > _GAP_THRESHOLD_SECONDS:
            gap_total += diff

    uptime = (total_span - gap_total) / total_span * 100.0
    return max(uptime, 0.0)


def calculate_api_error_rate_from_logs(log_entries: list[dict]) -> float:
    """Calculate the API error rate from log entries.

    Counts entries whose ``"message"`` field contains the string ``"ERROR"``.

    Args:
        log_entries: List of log entry dicts with "message" field.

    Returns:
        Error rate as a percentage (0.0 -- 100.0).  Returns 0.0 for an
        empty list.

    """
    if not log_entries:
        return 0.0

    total = len(log_entries)
    errors = sum(1 for entry in log_entries if "ERROR" in entry.get("message", ""))
    return errors / total * 100.0


def calculate_order_accuracy_from_trades(trades: list[dict]) -> float:
    """Calculate order accuracy from trade records.

    A trade is considered *closed* when ``"close_profit_abs"`` is present.
    Among closed trades, those with ``exit_reason`` equal to
    ``"force_exit"`` or ``"emergency_exit"`` are counted as abnormal.
    ``"replaced"`` (DCA) is treated as normal.

    Args:
        trades: List of trade dicts from the Freqtrade API.

    Returns:
        Accuracy percentage (0.0 -- 100.0).  Returns 100.0 when there
        are no closed trades.

    """
    closed = [t for t in trades if "close_profit_abs" in t]
    if not closed:
        return 100.0

    abnormal_reasons = {"force_exit", "emergency_exit"}
    abnormal = sum(1 for t in closed if t.get("exit_reason") in abnormal_reasons)
    normal = len(closed) - abnormal
    return normal / len(closed) * 100.0


def calculate_sharpe_deviation(trades: list[dict], backtest_sharpe: float = 0.28) -> float:
    """Calculate deviation of live Sharpe ratio from backtest Sharpe.

    Uses ``close_profit`` of closed trades (``is_open == False``) to
    compute a simple Sharpe ratio (mean / std of returns).

    Args:
        trades: List of trade dicts with "is_open" and "close_profit".
        backtest_sharpe: Reference Sharpe ratio from backtest results.

    Returns:
        Absolute deviation ``|live_sharpe - backtest_sharpe|``.
        Returns 1.0 when fewer than 5 closed trades are available.

    """
    closed_returns = [
        t["close_profit"] for t in trades if not t.get("is_open", True) and "close_profit" in t
    ]

    if len(closed_returns) < 5:
        return 1.0

    mean_ret = sum(closed_returns) / len(closed_returns)
    variance = sum((r - mean_ret) ** 2 for r in closed_returns) / len(closed_returns)
    std_ret = math.sqrt(variance)

    live_sharpe = mean_ret / std_ret if std_ret > 0 else 0.0
    return abs(live_sharpe - backtest_sharpe)


def calculate_days_running(start_date: str) -> int:
    """Calculate number of days from *start_date* until today.

    Args:
        start_date: ISO-format date string (``"YYYY-MM-DD"``).

    Returns:
        Number of elapsed days.

    """
    start = date.fromisoformat(start_date)
    return (date.today() - start).days


def find_database_path(project_root: str) -> str | None:
    """Locate the Freqtrade dry-run database file.

    Search order:
    1. ``db_url`` key in ``{project_root}/user_data/config/config.json``
    2. ``{project_root}/tradesv3.dryrun.sqlite`` (size > 0)
    3. ``{project_root}/user_data/tradesv3.dryrun.sqlite`` (size > 0)

    Args:
        project_root: Absolute path to the project root.

    Returns:
        Absolute path to the database file, or ``None`` if not found.

    """
    # 1. Try config.json db_url
    config_path = Path(project_root) / "user_data" / "config" / "config.json"
    if config_path.is_file():
        try:
            with open(config_path) as f:
                config = json.load(f)
            db_url = config.get("db_url", "")
            if db_url.startswith("sqlite:///"):
                db_file = db_url.replace("sqlite:///", "")
                if Path(db_file).is_file() and Path(db_file).stat().st_size > 0:
                    return db_file
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Project root
    root_db = Path(project_root) / "tradesv3.dryrun.sqlite"
    if root_db.is_file() and root_db.stat().st_size > 0:
        return str(root_db)

    # 3. user_data dir
    user_data_db = Path(project_root) / "user_data" / "tradesv3.dryrun.sqlite"
    if user_data_db.is_file() and user_data_db.stat().st_size > 0:
        return str(user_data_db)

    return None


def collect_metrics_from_api(
    api_config: ApiClientConfig,
    start_date: str = "2026-01-30",
) -> DryRunMetrics | None:
    """Collect Dry Run metrics via the Freqtrade REST API.

    Calls ``fetch_trades`` and ``fetch_logs``, then delegates to the
    individual ``calculate_*`` helpers.

    Args:
        api_config: API client configuration.
        start_date: Dry Run start date (default ``"2026-01-30"``).

    Returns:
        ``DryRunMetrics`` on success, ``None`` when the API is
        unreachable.

    """
    trades_resp = fetch_trades(api_config)
    logs_resp = fetch_logs(api_config, limit=500)

    if not trades_resp.success or not logs_resp.success:
        return None

    trades_data = trades_resp.data or {}
    logs_data = logs_resp.data or {}

    trades_list: list[dict] = trades_data.get("trades", []) if isinstance(trades_data, dict) else []
    logs_list: list[dict] = logs_data.get("logs", []) if isinstance(logs_data, dict) else []

    uptime = calculate_uptime_from_logs(logs_list)
    error_rate = calculate_api_error_rate_from_logs(logs_list)
    accuracy = calculate_order_accuracy_from_trades(trades_list)
    sharpe_dev = calculate_sharpe_deviation(trades_list)
    days = calculate_days_running(start_date)

    return DryRunMetrics(
        uptime_percent=uptime,
        api_error_rate=error_rate,
        order_accuracy=accuracy,
        sharpe_deviation=sharpe_dev,
        days_running=days,
    )


def collect_metrics_from_db(db_path: str, log_path: str | None = None) -> DryRunMetrics | None:
    """Collect Dry Run metrics by reading the SQLite database directly.

    Falls back to this approach when the REST API is unavailable.
    ``uptime_percent`` is set to a fixed estimate of 95.0 because
    precise uptime cannot be derived from the database alone.

    Args:
        db_path: Path to the Freqtrade SQLite database.
        log_path: Optional path to a Freqtrade log file for error-rate
            calculation.

    Returns:
        ``DryRunMetrics`` on success, ``None`` on database errors.

    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT is_open, close_profit, close_profit_abs, exit_reason FROM trades"
        )
        rows = [dict(row) for row in cursor.fetchall()]
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        return None
    finally:
        if conn is not None:
            conn.close()

    # Uptime: fixed estimate (cannot derive from DB)
    uptime = 95.0

    # API error rate from log file
    api_error_rate = 0.0
    if log_path:
        try:
            with open(log_path) as f:
                lines = f.readlines()
            if lines:
                error_count = sum(1 for line in lines if "ERROR" in line)
                api_error_rate = error_count / len(lines) * 100.0
        except OSError:
            pass

    accuracy = calculate_order_accuracy_from_trades(rows)
    sharpe_dev = calculate_sharpe_deviation(rows)
    days = calculate_days_running("2026-01-30")

    return DryRunMetrics(
        uptime_percent=uptime,
        api_error_rate=api_error_rate,
        order_accuracy=accuracy,
        sharpe_deviation=sharpe_dev,
        days_running=days,
    )


def main() -> int:
    """Main entry point for CLI usage.

    Attempts to collect metrics from the Freqtrade REST API first.
    Falls back to direct database reading if the API is unavailable.

    """
    print("Dry Run Criteria Checker")
    print("=" * 50)

    # API settings
    api_config = load_api_config_from_env()

    # Data source selection: API -> DB -> failure
    metrics = collect_metrics_from_api(api_config)
    source = "API"

    if metrics is None:
        print("API connection failed, falling back to database...")
        project_root = str(Path(__file__).resolve().parent.parent)
        db_path = find_database_path(project_root)
        if db_path:
            log_path = next(
                Path(project_root, "user_data", "logs").glob("freqtrade*.log"),
                None,
            )
            metrics = collect_metrics_from_db(db_path, str(log_path) if log_path else None)
            source = "Database"

    if metrics is None:
        print("ERROR: Could not collect metrics from any source")
        return 2

    print(f"Data source: {source}")
    print()

    result = evaluate_dryrun(metrics)
    for detail in result.details:
        print(detail)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
