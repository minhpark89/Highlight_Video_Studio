"""Safe user-selectable render concurrency policy."""

import json
import threading
from contextlib import contextmanager

HARD_MAX_CONCURRENT_RENDERS = 4


def bounded_concurrency(value, *, maximum=HARD_MAX_CONCURRENT_RENDERS):
    """Return a valid positive concurrency value, bounded by the app limit."""
    if isinstance(value, bool) or isinstance(value, float) or not isinstance(value, (int, str)):
        raise ValueError("Concurrency must be an integer")
    if isinstance(value, str) and (not value.isascii() or not value.isdecimal()):
        raise ValueError("Concurrency must be an integer")
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError("Concurrency must be an integer")
    if value < 1 or value > maximum:
        raise ValueError(f"Concurrency must be between 1 and {maximum}")
    return value


def resolve_concurrency(mode, manual_value, auto_value, *, maximum=HARD_MAX_CONCURRENT_RENDERS):
    """Resolve Auto/manual selection without ever exceeding the hard safety cap."""
    normalized_mode = str(mode or "auto").strip().lower()
    if normalized_mode == "auto":
        return "auto", bounded_concurrency(auto_value, maximum=maximum)
    if normalized_mode != "manual":
        raise ValueError("Concurrency mode must be auto or manual")
    return "manual", bounded_concurrency(manual_value, maximum=maximum)


def saved_concurrency(path, auto_value):
    """Restore user preferences without changing the hardware recommendation."""
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        return resolve_concurrency(state.get("concurrency_mode", "auto"),
                                   state.get("manual_concurrency"), auto_value)
    except (OSError, ValueError, TypeError, AttributeError):
        return resolve_concurrency("auto", None, auto_value)


class RenderLimiter:
    """Resize while retaining the leases held by active render processes."""

    def __init__(self, limit):
        self.limit = bounded_concurrency(limit)
        self.active = 0
        self.condition = threading.Condition()

    def resize(self, limit):
        with self.condition:
            self.limit = bounded_concurrency(limit)
            self.condition.notify_all()

    @contextmanager
    def slot(self):
        with self.condition:
            self.condition.wait_for(lambda: self.active < self.limit)
            self.active += 1
        try:
            yield
        finally:
            with self.condition:
                self.active -= 1
                self.condition.notify_all()
