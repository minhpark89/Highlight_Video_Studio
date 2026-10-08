"""Windows-friendly atomic replacement for small JSON ledgers."""

import os
import time
from contextlib import contextmanager


@contextmanager
def shared_reader(path, encoding="utf-8-sig"):
    """Allow an atomic rename while a Windows reader holds the previous file."""
    if os.name != "nt":
        with open(path, "r", encoding=encoding) as stream:
            yield stream
        return
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    handle = create(str(path), 0x80000000, 0x1 | 0x2 | 0x4, None, 3, 0x80, None)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except Exception:
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(handle)
        raise
    with os.fdopen(descriptor, "r", encoding=encoding) as stream:
        yield stream


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
