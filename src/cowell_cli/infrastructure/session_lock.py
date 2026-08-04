"""Single-session advisory lock so only one Cowell session runs at a time.

Uses an OS advisory byte-range lock on an open file handle (msvcrt on Windows,
fcntl elsewhere). The OS drops the lock when the handle closes or the process
dies, so a crashed run never leaves a stale lock behind (the file itself may
remain — the lock lives on the open handle, not on the file existing).
"""
from __future__ import annotations

import os
from pathlib import Path

from ..errors import SourceUnavailableError

try:  # Windows
    import msvcrt

    def _try_lock(fd: int) -> None:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)

    def _unlock(fd: int) -> None:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

except ImportError:  # POSIX (tests/CI on non-Windows)
    import fcntl

    def _try_lock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


class SessionLock:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: int | None = None

    def acquire(self) -> "SessionLock":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._path, os.O_RDWR | os.O_CREAT)
        try:
            _try_lock(fd)
        except OSError as error:
            os.close(fd)
            raise SourceUnavailableError(
                "SOURCE_UNAVAILABLE",
                "Another Cowell CLI session is already running",
                {"already_running": True, "lock": str(self._path)},
            ) from error
        self._fd = fd
        return self

    def release(self) -> None:
        if self._fd is None:
            return
        fd, self._fd = self._fd, None
        try:
            _unlock(fd)
        finally:
            os.close(fd)

    def __enter__(self) -> "SessionLock":
        return self.acquire()

    def __exit__(self, *_exc: object) -> None:
        self.release()
