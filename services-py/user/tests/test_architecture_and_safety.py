"""Kiểm tra kiến trúc 3 lớp, an toàn dữ liệu và không tạo DB ngoài ý muốn."""
import ast
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.core import config
from app.main import app

APP = Path(__file__).resolve().parents[1] / "app"
USER_ROOT = APP.parent


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            names.add(n.module or "")
    return names


def test_no_sql_or_sqlite_outside_repository_and_db():
    for layer in ("api", "controllers", "services", "schemas", "entities"):
        for f in (APP / layer).glob("*.py"):
            text = f.read_text(encoding="utf-8")
            assert "sqlite3" not in _imports(f), f
            for kw in ("SELECT ", "INSERT ", "UPDATE ", "DELETE ", "CREATE TABLE"):
                assert kw not in text, f"{f} chứa SQL: {kw}"


def test_layers_only_call_downwards():
    forbidden = {
        "api": ("app.repositories", "app.db", "app.services"),
        "controllers": ("app.repositories", "app.db", "app.api"),
        "services": ("app.controllers", "app.api", "app.db", "fastapi"),
        "repositories": ("app.services", "app.controllers", "app.api", "fastapi"),
    }
    for layer, bad in forbidden.items():
        for f in (APP / layer).glob("*.py"):
            if f.name == "deps.py":  # composition root: được phép lắp ráp
                continue
            for imp in _imports(f):
                assert not any(imp == b or imp.startswith(b + ".") for b in bad), f"{f}: import {imp}"


def test_sql_is_parameterized_in_repository():
    text = (APP / "repositories" / "user_repository.py").read_text(encoding="utf-8")
    assert "execute(f" not in text and ".format(" not in text and "% (" not in text
    assert text.count("?") >= 5


def test_importing_app_creates_no_database(tmp_path):
    db = tmp_path / "should_not_exist" / "user.db"
    env = {**os.environ, "DB_PATH": str(db)}
    subprocess.run([sys.executable, "-c", "import app.main"], cwd=USER_ROOT, env=env, check=True)
    assert not db.exists() and not db.parent.exists()
    assert not (USER_ROOT / "data").exists()


def test_startup_creates_schema_but_no_data(isolated_db):
    import sqlite3

    with TestClient(app) as c:  # chạy lifespan
        assert c.get("/health").status_code == 200
    assert Path(config.DB_PATH).exists()
    with sqlite3.connect(config.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_tests_never_touch_real_database(isolated_db):
    assert "user.db" in config.DB_PATH and str(isolated_db) == config.DB_PATH
    assert Path(config.DB_PATH).parent != USER_ROOT / "data"


def test_no_extra_endpoints_beyond_contract():
    paths = app.openapi()["paths"]
    api = {(m.upper(), p) for p, ops in paths.items() for m in ops}
    assert api == {
        ("POST", "/api/register"), ("POST", "/api/login"),
        ("GET", "/api/users"), ("GET", "/api/users/{user_id}"), ("GET", "/health"),
    }
