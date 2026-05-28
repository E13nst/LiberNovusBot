import importlib.util
import uuid
from pathlib import Path


MIGRATION_FILE = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "2026-05-26-14-02-00_d4e5f6a7b8c9_enforce_dream_session_not_null.py"
)


def _load_migration_module():
    spec = importlib.util.spec_from_file_location(f"migration_{uuid.uuid4().hex}", MIGRATION_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class _RecordingConnection:
    def __init__(self, null_count):
        self.null_count = null_count
        self.executed_sql = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.executed_sql.append((sql, params))
        if "SELECT COUNT(*) FROM dreams WHERE session_id IS NULL" in sql:
            return _ScalarResult(self.null_count)
        return _ScalarResult(None)


class _FakeOp:
    def __init__(self, connection):
        self._connection = connection
        self.alter_calls = []

    def get_bind(self):
        return self._connection

    def alter_column(self, *args, **kwargs):
        self.alter_calls.append((args, kwargs))


def test_upgrade_backfills_orphans_before_not_null():
    module = _load_migration_module()
    connection = _RecordingConnection(null_count=2)
    fake_op = _FakeOp(connection)
    module.op = fake_op

    module.upgrade()

    assert any("INSERT INTO dream_sessions" in sql for sql, _ in connection.executed_sql)
    assert any("UPDATE dreams" in sql for sql, _ in connection.executed_sql)
    assert len(fake_op.alter_calls) == 1
