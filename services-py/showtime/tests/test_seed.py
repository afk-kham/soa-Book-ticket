"""Seed suất chiếu lịch sử: đúng id/giá của dữ liệu mẫu chung, chạy lại an toàn, không chiếm id lịch tự sinh."""
from app.db import connection
from app.db.seed import HISTORY, run_seed
from app.repositories import create_showtime, get_showtime


def test_seed_history_idempotent_and_keeps_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(connection, "DB_PATH", str(tmp_path / "showtime.db"))
    assert run_seed() == len(HISTORY)
    assert run_seed() == 0
    s = get_showtime(1)
    assert (s.movie_id, s.time, s.price) == (1, "2026-10-10 18:00:00", 90000)
    assert get_showtime(5).price == 90000
    new = create_showtime(9, "BHD Star Bitexco", "P1", "2030-01-01 10:00:00", 65000)
    assert new.id == 7
