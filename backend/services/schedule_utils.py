from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple

import croniter
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover - fallback if zoneinfo not present
    ZoneInfo = None  # type: ignore


class ScheduleComputationError(Exception):
    pass


def _get_tz(tz_name: Optional[str]) -> ZoneInfo:
    if not tz_name:
        tz_name = "UTC"
    if ZoneInfo is None:
        raise ScheduleComputationError("ZoneInfo not available on this Python runtime")
    try:
        return ZoneInfo(tz_name)
    except Exception as e:
        raise ScheduleComputationError(f"Invalid timezone '{tz_name}': {e}")


def _ensure_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_once_at_local(once_at: str, tz_name: str) -> datetime:
    """Parse a once_at ISO timestamp.

    If it includes a timezone offset, trust it; otherwise interpret as wall-clock time in tz_name.
    Returns an aware UTC datetime.
    """
    try:
        dt = datetime.fromisoformat(once_at)
    except Exception as e:
        raise ScheduleComputationError(f"Invalid once_at format '{once_at}': {e}")

    if dt.tzinfo is None:
        tz = _get_tz(tz_name)
        local = dt.replace(tzinfo=tz)
    else:
        local = dt
    return local.astimezone(timezone.utc)


def compute_next_run(schedule: dict, now_utc: Optional[datetime] = None) -> Tuple[Optional[datetime], Optional[str]]:
    """Compute the next_run in UTC for a schedule.

    Returns (next_run_utc, error_message). If error_message is not None, computation failed.
    schedule keys expected:
      - type: 'recurring' | 'once' (default 'recurring')
      - timezone: IANA tz
      - cron_expression (recurring)
      - once_at (once)
    """
    try:
        now_utc = _ensure_aware(now_utc or datetime.now(timezone.utc))
        tz = _get_tz(schedule.get("timezone") or "UTC")
        s_type = (schedule.get("type") or "recurring").lower()

        if s_type == "once":
            once_at = schedule.get("once_at")
            if not once_at:
                return None, "Missing once_at for one-time schedule"
            target_utc = parse_once_at_local(once_at, tz.key)
            if target_utc <= now_utc:
                return None, "once_at is in the past"
            return target_utc, None

        # recurring
        cron_expr = schedule.get("cron_expression")
        if not cron_expr:
            return None, "Missing cron_expression for recurring schedule"

        # Use local wall-clock base time
        base_local = datetime.now(tz)
        try:
            cron = croniter.croniter(cron_expr, base_local)
            next_local = cron.get_next(datetime)
        except Exception as e:
            return None, f"Invalid cron expression: {e}"

        # Ensure next_local is tz-aware (croniter keeps tzinfo from base)
        if getattr(next_local, "tzinfo", None) is None:
            next_local = next_local.replace(tzinfo=tz)

        next_utc = next_local.astimezone(timezone.utc)
        if next_utc <= now_utc:
            # Safety: compute again using next_local as base
            cron = croniter.croniter(cron_expr, next_local)
            next_local = cron.get_next(datetime)
            if getattr(next_local, "tzinfo", None) is None:
                next_local = next_local.replace(tzinfo=tz)
            next_utc = next_local.astimezone(timezone.utc)
        return next_utc, None
    except ScheduleComputationError as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error computing next_run: {e}"

