from sql_db import DatabaseEngine


def test_create_insert_select_star_round_trip() -> None:
    engine = DatabaseEngine()

    assert engine.execute("CREATE TABLE t1(a INTEGER, b INTEGER, c VARCHAR(30))").success is True
    assert engine.execute("INSERT INTO t1(c, a) VALUES('hello', 7)").success is True

    result = engine.execute("SELECT * FROM t1")

    assert result.success is True
    assert result.rows == [(7, None, "hello")]


def test_select_projection_and_order_by_position() -> None:
    engine = DatabaseEngine()

    engine.execute("CREATE TABLE t1(a INTEGER, b INTEGER)")
    engine.execute("INSERT INTO t1 VALUES(2, 1)")
    engine.execute("INSERT INTO t1 VALUES(1, 2)")

    result = engine.execute("SELECT a, b FROM t1 ORDER BY 1, 2")

    assert result.success is True
    assert result.rows == [(1, 2), (2, 1)]
