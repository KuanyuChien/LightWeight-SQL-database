from sql_db import DatabaseEngine


def test_engine_accepts_empty_sql() -> None:
    result = DatabaseEngine().execute("")
    assert result.success is True
    assert result.rows == []
