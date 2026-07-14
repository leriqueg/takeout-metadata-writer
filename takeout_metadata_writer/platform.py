"""Cross-platform file-timestamp manipulation.

Provides ``set_file_times()`` that:
- On **Windows**: uses ``ctypes`` + ``kernel32.SetFileTime`` for creation time
  and ``os.utime`` for modification time.
- On **Unix**: uses ``os.utime`` for modification time and logs a warning
  that creation time cannot be set.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    # -- Windows API type definitions ----------------------------------------

    class FILETIME(ctypes.Structure):
        """Windows FILETIME: 64-bit count of 100-ns intervals since 1601-01-01."""
        _fields_ = [
            ("dwLowDateTime", ctypes.wintypes.DWORD),
            ("dwHighDateTime", ctypes.wintypes.DWORD),
        ]

    LPFILETIME = ctypes.POINTER(FILETIME)

    # Constants
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 1
    FILE_SHARE_WRITE = 2
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000

    # Kernel32 function bindings
    _CreateFileW = ctypes.windll.kernel32.CreateFileW
    _CreateFileW.argtypes = [
        ctypes.wintypes.LPCWSTR,   # lpFileName
        ctypes.wintypes.DWORD,      # dwDesiredAccess
        ctypes.wintypes.DWORD,      # dwShareMode
        ctypes.wintypes.LPVOID,     # lpSecurityAttributes
        ctypes.wintypes.DWORD,      # dwCreationDisposition
        ctypes.wintypes.DWORD,      # dwFlagsAndAttributes
        ctypes.wintypes.HANDLE,     # hTemplateFile
    ]
    _CreateFileW.restype = ctypes.wintypes.HANDLE

    _SetFileTime = ctypes.windll.kernel32.SetFileTime
    _SetFileTime.argtypes = [
        ctypes.wintypes.HANDLE,  # hFile
        LPFILETIME,              # lpCreationTime
        LPFILETIME,              # lpLastAccessTime
        LPFILETIME,              # lpLastWriteTime
    ]
    _SetFileTime.restype = ctypes.wintypes.BOOL

    _CloseHandle = ctypes.windll.kernel32.CloseHandle
    _CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    _CloseHandle.restype = ctypes.wintypes.BOOL

    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    # -- Helpers -------------------------------------------------------------

    # Seconds between Windows FILETIME epoch (1601-01-01) and Unix epoch
    # (1970-01-01).  Required because SetFileTime speaks FILETIME while
    # the rest of the world uses Unix timestamps.
    _WINDOWS_EPOCH_DELTA = 11644473600

    def _unix_to_filetime(unix_seconds: int) -> FILETIME:
        """Convert a Unix epoch timestamp to a Windows FILETIME structure."""
        intervals = (unix_seconds + _WINDOWS_EPOCH_DELTA) * 10_000_000
        ft = FILETIME()
        ft.dwLowDateTime = intervals & 0xFFFFFFFF
        ft.dwHighDateTime = (intervals >> 32) & 0xFFFFFFFF
        return ft


# -- Public API ---------------------------------------------------------------


def set_file_times(
    path: Path,
    creation_time: Optional[int] = None,
    modification_time: Optional[int] = None,
) -> Optional[str]:
    """Set file timestamps.

    Parameters
    ----------
    path:
        Filesystem path to the target file.
    creation_time:
        Desired creation time as Unix epoch seconds.  On non-Windows systems
        a warning is logged and the value is ignored.
    modification_time:
        Desired modification time as Unix epoch seconds (set via ``os.utime``
        on all platforms).

    Returns
    -------
    ``None`` on success, or an error-message ``str`` on failure.
    """
    if sys.platform == "win32":
        return _set_file_times_windows(path, creation_time, modification_time)
    return _set_file_times_unix(path, creation_time, modification_time)


def _set_file_times_windows(
    path: Path,
    creation_time: Optional[int],
    modification_time: Optional[int],
) -> Optional[str]:
    """Windows implementation — uses ``SetFileTime`` for ctime, ``os.utime`` for mtime."""
    try:
        handle = _CreateFileW(
            str(path),
            GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )
        if handle == INVALID_HANDLE_VALUE or not handle:
            return f"Failed to open file: {ctypes.WinError()}"

        try:
            # Modification time: os.utime works on all platforms
            if modification_time is not None:
                os.utime(path, (modification_time, modification_time))

            # Creation time: SetFileTime (Windows-only)
            if creation_time is not None:
                ctime_ft = _unix_to_filetime(creation_time)
                success = _SetFileTime(handle, ctypes.byref(ctime_ft), None, None)
                if not success:
                    return f"SetFileTime failed: {ctypes.WinError()}"
        finally:
            _CloseHandle(handle)

        return None

    except Exception as exc:
        return str(exc)


def _set_file_times_unix(
    path: Path,
    creation_time: Optional[int],
    modification_time: Optional[int],
) -> Optional[str]:
    """Unix implementation — ``os.utime`` for mtime, logged warning for ctime."""
    try:
        if modification_time is not None:
            os.utime(path, (modification_time, modification_time))
        if creation_time is not None:
            logger.warning(
                "Cannot set creation time on %s; "
                "creation_time=%s ignored for %s",
                sys.platform,
                creation_time,
                path,
            )
        return None

    except Exception as exc:
        return str(exc)
