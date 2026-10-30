"""Tạo schema (và tùy chọn nạp dữ liệu) một cách tường minh.

    python -m app.db.init_db           # chỉ tạo bảng/index (idempotent)
    python -m app.db.init_db --seed    # + dữ liệu mẫu chính thức (INSERT OR IGNORE, không ghi đè)
    python -m app.db.init_db --demo    # + dữ liệu demo để test thủ công (id từ 101; tự gồm cả --seed)
"""
import sys
from pathlib import Path

from app.db.connection import get_connection

_HERE = Path(__file__).parent


def init_schema(seed: bool = False, demo: bool = False) -> None:
    with get_connection() as conn:
        conn.executescript((_HERE / "schema.sql").read_text(encoding="utf-8"))
        if seed or demo:
            conn.executescript((_HERE / "seed.sql").read_text(encoding="utf-8"))
        if demo:
            conn.executescript((_HERE / "demo.sql").read_text(encoding="utf-8"))


if __name__ == "__main__":
    args = sys.argv[1:]
    init_schema(seed="--seed" in args, demo="--demo" in args)
    # ASCII: console Windows cp1252 không in được tiếng Việt
    print("Schema initialized" + (" + seed" if "--seed" in args or "--demo" in args else "") + (" + demo" if "--demo" in args else ""))
