"""Windows-friendly atomic replacement for small JSON ledgers."""

import os
import time


def replace_with_retry(source, target, timeout=20):
    """Retry transient sharing violations from readers, indexing and AV scanners."""
    deadline = time.monotonic() + timeout
    delay = 0.05
    while True:
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(delay)
            delay = min(delay * 1.5, 0.5)
