import pytest

from cowell_cli.errors import SourceUnavailableError
from cowell_cli.exit_codes import SOURCE_ERROR
from cowell_cli.infrastructure.session_lock import SessionLock


def test_second_acquire_reports_already_running(tmp_path):
    path = tmp_path / "session.lock"
    first = SessionLock(path).acquire()
    try:
        with pytest.raises(SourceUnavailableError) as excinfo:
            SessionLock(path).acquire()
    finally:
        first.release()

    error = excinfo.value
    assert error.code == "SOURCE_UNAVAILABLE"
    assert error.exit_code == SOURCE_ERROR
    assert error.details["already_running"] is True


def test_release_allows_reacquire(tmp_path):
    path = tmp_path / "session.lock"
    lock = SessionLock(path)
    lock.acquire()
    lock.release()

    # A fresh acquire on the freed lock must succeed.
    again = SessionLock(path).acquire()
    again.release()


def test_context_manager_holds_then_frees(tmp_path):
    path = tmp_path / "session.lock"
    with SessionLock(path):
        with pytest.raises(SourceUnavailableError):
            SessionLock(path).acquire()

    # After the with-block the lock is free again.
    SessionLock(path).acquire().release()


def test_release_is_idempotent(tmp_path):
    lock = SessionLock(tmp_path / "session.lock")
    lock.acquire()
    lock.release()
    lock.release()  # must not raise
