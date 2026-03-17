"""Shared monitoring helpers for dry-run diagnostics and reports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

LOG_TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"
GAP_THRESHOLD_SECONDS = 300  # 5 minutes
DEFAULT_DRYRUN_START_DATE = "2026-01-30"

IGNORED_API_ERROR_PATTERNS = (
    "Connection closed by remote server, closing code 1008",
    "Exception in continuously_async_watch_ohlcv",
    "Exception in _unwatch_ohlcv",
)


def normalize_log_entries(log_entries: list | None) -> list[dict[str, str]]:
    """Normalize API/log-file entries to timestamp/message dicts."""
    normalized: list[dict[str, str]] = []
    for entry in log_entries or []:
        if isinstance(entry, dict):
            timestamp = str(entry.get("timestamp", "")).strip()
            message = str(entry.get("message", "")).strip()
            if timestamp:
                normalized.append({"timestamp": timestamp, "message": message})
            continue

        if isinstance(entry, (list, tuple)) and len(entry) >= 5:
            timestamp = str(entry[0]).strip()
            level = str(entry[3]).strip()
            message = str(entry[4]).strip()
            if timestamp:
                normalized.append({"timestamp": timestamp, "message": f"{level} {message}".strip()})

    return normalized


def read_log_entries_from_file(log_path: str | None) -> list[dict[str, str]]:
    """Read text log lines into timestamp/message dicts when possible."""
    if not log_path:
        return []

    path = Path(log_path)
    if not path.exists():
        return []

    entries: list[dict[str, str]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if len(line) >= 19:
                timestamp = line[:19]
                try:
                    datetime.strptime(timestamp, LOG_TIMESTAMP_FMT)
                except ValueError:
                    timestamp = ""
                if timestamp:
                    entries.append({"timestamp": timestamp, "message": line[20:].strip()})
                    continue
            entries.append({"timestamp": "", "message": line.strip()})
    except OSError:
        return []

    return entries


def calculate_uptime_from_logs(log_entries: list[dict[str, str]]) -> float | None:
    """Calculate uptime percentage from log gaps, or None if unavailable."""
    timestamps: list[datetime] = []
    for entry in log_entries:
        ts_str = entry.get("timestamp", "")
        try:
            timestamps.append(datetime.strptime(ts_str, LOG_TIMESTAMP_FMT))
        except (ValueError, TypeError):
            continue

    if len(timestamps) < 2:
        return None

    timestamps.sort()
    total_span = (timestamps[-1] - timestamps[0]).total_seconds()
    if total_span <= 0:
        return None

    gap_total = 0.0
    for index in range(1, len(timestamps)):
        diff = (timestamps[index] - timestamps[index - 1]).total_seconds()
        if diff > GAP_THRESHOLD_SECONDS:
            gap_total += diff

    uptime = (total_span - gap_total) / total_span * 100.0
    return max(uptime, 0.0)


def is_ignored_api_error(message: str) -> bool:
    """Return True when an error should be excluded from API error rate.

    We currently ignore known Binance websocket churn that does not imply the
    bot is down or that REST API requests are failing.
    """
    return any(pattern in message for pattern in IGNORED_API_ERROR_PATTERNS)



def calculate_api_error_stats(log_entries: list[dict[str, str]]) -> tuple[int, int, float | None]:
    """Return error count, total count, and error rate percentage."""
    total = len(log_entries)
    if total == 0:
        return 0, 0, None

    errors = 0
    for entry in log_entries:
        message = entry.get("message", "")
        if "ERROR" in message and not is_ignored_api_error(message):
            errors += 1
    return errors, total, errors / total * 100.0


def resolve_log_path(project_root: str) -> str | None:
    """Return the most recent supported log path, if one exists."""
    log_dir = Path(project_root) / "user_data" / "logs"
    if not log_dir.exists():
        return None

    candidates: list[Path] = []
    for pattern in ("freqtrade*.log", "dryrun*.log", "*.nohup.log", "*.log"):
        candidates.extend(log_dir.glob(pattern))

    unique_candidates = {candidate.resolve(): candidate for candidate in candidates}
    if not unique_candidates:
        return None

    newest = max(unique_candidates.values(), key=lambda path: path.stat().st_mtime)
    return str(newest)
