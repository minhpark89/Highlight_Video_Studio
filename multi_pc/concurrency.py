"""Safe user-selectable render concurrency policy."""

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
