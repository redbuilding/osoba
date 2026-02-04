from __future__ import annotations
import threading
from collections import Counter
from typing import Any, Dict

from core.config import get_logger

logger = get_logger("telemetry")
_lock = threading.Lock()
_counters: Counter[str] = Counter()


def record_event(name: str, props: Dict[str, Any] | None = None) -> None:
    """Lightweight, in-process telemetry: increment counter and log structured event.

    This is intentionally simple and non-persistent. Use logs for analysis.
    """
    with _lock:
        _counters[name] += 1
    try:
        safe_props = {}
        if isinstance(props, dict):
            # Avoid logging large strings or PII
            for k, v in props.items():
                if isinstance(v, str) and len(v) > 200:
                    safe_props[k] = v[:200] + "…"
                else:
                    safe_props[k] = v
        logger.info(f"telemetry event name={name} props={safe_props}")
    except Exception:
        # Never crash callers
        pass


def get_counts() -> Dict[str, int]:
    with _lock:
        return dict(_counters)

