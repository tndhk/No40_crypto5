"""Daily report generation for Freqtrade DCA bot Dry Run monitoring."""

import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from scripts.freqtrade_api_client import (
    ApiClientConfig,
    fetch_logs,
    fetch_profit,
    fetch_status,
    fetch_trades,
    load_api_config_from_env,
)


@dataclass(frozen=True)
class DailyMetrics:
    """Daily metrics collected from Freqtrade."""

    date: str
    uptime_percent: float
    total_trades: int
    daily_pnl: float
    cumulative_pnl: float
    open_positions: int
    api_errors: int
    api_total_calls: int


def format_daily_report(metrics: DailyMetrics) -> str:
    """Format daily metrics into a report string.

    Args:
        metrics: DailyMetrics to format

    Returns:
        Formatted report string

    """
    # Calculate API error rate
    if metrics.api_total_calls > 0:
        api_error_rate = (metrics.api_errors / metrics.api_total_calls) * 100
    else:
        api_error_rate = 0.0

    # Format P&L with sign and comma separators
    daily_pnl_str = f"{metrics.daily_pnl:+,.0f}"
    cumulative_pnl_str = f"{metrics.cumulative_pnl:+,.0f}"

    # Build report
    report_lines = [
        "=" * 60,
        f"Daily Report - {metrics.date}",
        "=" * 60,
        "",
        "UPTIME & STABILITY",
        f"  Uptime:           {metrics.uptime_percent:.1f}%",
        f"  API Error Rate:   {api_error_rate:.2f}% ({metrics.api_errors}/{metrics.api_total_calls} calls)",
        "",
        "TRADING ACTIVITY",
        f"  Total Trades:     {metrics.total_trades}",
        f"  Open Positions:   {metrics.open_positions}",
        "",
        "PROFIT & LOSS (JPY)",
        f"  Daily P&L:        {daily_pnl_str}",
        f"  Cumulative P&L:   {cumulative_pnl_str}",
        "",
        "=" * 60,
    ]

    return "\n".join(report_lines)


def collect_daily_metrics_from_api(
    api_config: ApiClientConfig,
    report_date: str,
) -> DailyMetrics | None:
    """Collect daily metrics from the Freqtrade REST API.

    Calls fetch_profit, fetch_status, fetch_trades, and fetch_logs to
    assemble a DailyMetrics snapshot.  Returns None if the initial profit
    call fails (indicating the API is unreachable).

    Args:
        api_config: API client configuration.
        report_date: Date string in "YYYY-MM-DD" format.

    Returns:
        DailyMetrics populated from API data, or None on connection failure.

    """
    profit_resp = fetch_profit(api_config)
    if not profit_resp.success:
        return None

    status_resp = fetch_status(api_config)
    trades_resp = fetch_trades(api_config)
    logs_resp = fetch_logs(api_config)

    # --- profit ---
    profit_data = profit_resp.data or {}
    profit_all = profit_data.get("profit_all_coin", 0.0)

    # --- open positions ---
    status_data = status_resp.data if status_resp.success else []
    if isinstance(status_data, list):
        open_positions = len(status_data)
    else:
        open_positions = 0

    # --- trades closed on report_date ---
    trades_data = trades_resp.data if trades_resp.success else {}
    trades_list = trades_data.get("trades", []) if isinstance(trades_data, dict) else []
    total_trades = sum(1 for t in trades_list if t.get("close_date", "").startswith(report_date))

    # --- logs -> api_errors / api_total_calls ---
    logs_data = logs_resp.data if logs_resp.success else {}
    log_entries = logs_data.get("logs", []) if isinstance(logs_data, dict) else []
    api_total_calls = len(log_entries)
    api_errors = sum(
        1
        for entry in log_entries
        if isinstance(entry, (list, tuple)) and len(entry) >= 4 and "ERROR" in str(entry[3])
    )

    # --- uptime estimate ---
    if api_total_calls > 0:
        error_rate = (api_errors / api_total_calls) * 100
        uptime_percent = 100.0 - error_rate
    else:
        uptime_percent = 100.0

    return DailyMetrics(
        date=report_date,
        uptime_percent=uptime_percent,
        total_trades=total_trades,
        daily_pnl=profit_all,
        cumulative_pnl=profit_all,
        open_positions=open_positions,
        api_errors=api_errors,
        api_total_calls=api_total_calls,
    )


def collect_daily_metrics_from_db(
    db_path: str,
    log_path: str | None,
    report_date: str,
) -> DailyMetrics | None:
    """Collect daily metrics by reading the Freqtrade SQLite database directly.

    This is a fallback when the REST API is unavailable.  Reads trade data
    from the ``trades`` table and optionally counts ERROR lines from the log
    file at *log_path*.

    Args:
        db_path: Path to the Freqtrade SQLite database.
        log_path: Optional path to a Freqtrade log file.
        report_date: Date string in "YYYY-MM-DD" format.

    Returns:
        DailyMetrics populated from database data, or None on error.

    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Trades closed on report_date
        cursor.execute(
            "SELECT close_profit_abs FROM trades WHERE close_date LIKE ?",
            (f"{report_date}%",),
        )
        daily_rows = cursor.fetchall()
        total_trades = len(daily_rows)
        daily_pnl = sum(row[0] for row in daily_rows if row[0] is not None)

        # Cumulative P&L (all closed trades)
        cursor.execute("SELECT close_profit_abs FROM trades WHERE close_date IS NOT NULL")
        all_rows = cursor.fetchall()
        cumulative_pnl = sum(row[0] for row in all_rows if row[0] is not None)

        # Open positions
        cursor.execute("SELECT COUNT(*) FROM trades WHERE is_open = 1")
        open_positions = cursor.fetchone()[0]
    except Exception:
        return None
    finally:
        if conn is not None:
            conn.close()

    # Log analysis
    api_errors = 0
    api_total_calls = 0
    if log_path:
        try:
            with open(log_path) as f:
                for line in f:
                    api_total_calls += 1
                    if "ERROR" in line:
                        api_errors += 1
        except OSError:
            pass

    return DailyMetrics(
        date=report_date,
        uptime_percent=95.0,
        total_trades=total_trades,
        daily_pnl=daily_pnl,
        cumulative_pnl=cumulative_pnl,
        open_positions=open_positions,
        api_errors=api_errors,
        api_total_calls=api_total_calls,
    )


def save_report_to_file(report: str, output_dir: str, report_date: str) -> str:
    """Save a report string to a text file.

    Creates *output_dir* (including parents) if it does not already exist.

    Args:
        report: The report text to write.
        output_dir: Directory in which to save the file.
        report_date: Date string used in the filename ("YYYY-MM-DD").

    Returns:
        Absolute path of the saved file.

    """
    dir_path = Path(output_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    file_path = dir_path / f"daily_report_{report_date}.txt"
    file_path.write_text(report)
    return str(file_path)


def main() -> int:
    """Generate and display a daily report.

    Attempts to collect metrics from the Freqtrade REST API first, then
    falls back to reading the database directly.  The formatted report is
    printed to stdout and saved to a file under ``user_data/logs/``.

    Returns:
        0 on success, 2 if no data source is available.

    """
    print("Daily Report Generator")
    print("=" * 60)

    report_date = datetime.now().strftime("%Y-%m-%d")
    api_config = load_api_config_from_env()

    # Data source selection: API -> DB fallback
    metrics = collect_daily_metrics_from_api(api_config, report_date)
    source = "API"

    if metrics is None:
        print("API connection failed, falling back to database...")
        project_root = str(Path(__file__).resolve().parent.parent)
        # DB path detection
        db_path = None
        root_db = Path(project_root) / "tradesv3.dryrun.sqlite"
        userdata_db = Path(project_root) / "user_data" / "tradesv3.dryrun.sqlite"
        if root_db.exists() and root_db.stat().st_size > 0:
            db_path = str(root_db)
        elif userdata_db.exists() and userdata_db.stat().st_size > 0:
            db_path = str(userdata_db)

        if db_path:
            log_path = None
            log_dir = Path(project_root) / "user_data" / "logs"
            if log_dir.exists():
                log_files = sorted(
                    log_dir.glob("freqtrade*.log"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if log_files:
                    log_path = str(log_files[0])
            metrics = collect_daily_metrics_from_db(db_path, log_path, report_date)
            source = "Database"

    if metrics is None:
        print("ERROR: Could not collect metrics from any source")
        return 2

    print(f"\nData source: {source}\n")

    report = format_daily_report(metrics)
    print(report)

    # Save report to file
    project_root = str(Path(__file__).resolve().parent.parent)
    output_dir = str(Path(project_root) / "user_data" / "logs")
    saved_path = save_report_to_file(report, output_dir, report_date)
    print(f"\nReport saved to: {saved_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
