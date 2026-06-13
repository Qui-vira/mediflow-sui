"""Tests for Band room message-limit handling."""
import pytest

from core.case_state import (
    disable_room_for_band_limit,
    init_case_state,
    is_band_message_limit_error,
    is_room_disabled,
)
from core import case_store


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("MEDBAND_DATA_DIR", str(tmp_path))
    case_store.DATA_DIR = tmp_path
    case_store.SQLITE_PATH = tmp_path / "medband_state.db"
    case_store._pg_pool = None
    init_case_state()


def test_detect_band_limit_error():
    assert is_band_message_limit_error(Exception("403 limit_reached for room"))
    assert is_band_message_limit_error(Exception("max_messages_per_room_count exceeded"))
    assert not is_band_message_limit_error(Exception("403 forbidden"))


def test_disable_room_persists():
    room_id = "room-maxed-out"
    assert not is_room_disabled(room_id)
    case_store.disable_room(room_id)
    assert is_room_disabled(room_id)


def test_disable_room_for_band_limit():
    room_id = "room-limit-403"
    exc = Exception("HTTP 403: limit_reached max_messages_per_room_count")
    assert disable_room_for_band_limit(room_id, exc) is True
    assert is_room_disabled(room_id)
    assert disable_room_for_band_limit(room_id, Exception("other error")) is False


def test_init_store_logs_sqlite(caplog):
    import logging

    caplog.set_level(logging.INFO, logger="core.case_store")
    case_store.init_store()
    assert any("Case store initialized: SQLite" in r.message for r in caplog.records)


def test_list_and_clear_disabled_rooms():
    case_store.disable_room("room-a")
    case_store.disable_room("room-b")
    rows = case_store.list_disabled_rooms()
    assert len(rows) == 2
    assert case_store.enable_room("room-a") is True
    assert case_store.is_room_disabled("room-a") is False
    assert case_store.is_room_disabled("room-b") is True
    assert case_store.clear_disabled_rooms() == 1
    assert case_store.list_disabled_rooms() == []
