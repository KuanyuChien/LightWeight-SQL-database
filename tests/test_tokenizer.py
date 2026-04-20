from sql_db.tokenizer import tokenize


def test_tokenizer_handles_keywords_and_identifiers() -> None:
    tokens = tokenize("SELECT a FROM t1")
    assert [(token.kind, token.value) for token in tokens] == [
        ("keyword", "SELECT"),
        ("identifier", "a"),
        ("keyword", "FROM"),
        ("identifier", "t1"),
    ]


def test_tokenizer_handles_integer_literals() -> None:
    tokens = tokenize("VALUES(-12, 34)")
    assert [(token.kind, token.value) for token in tokens] == [
        ("keyword", "VALUES"),
        ("symbol", "("),
        ("symbol", "-"),
        ("integer", "12"),
        ("symbol", ","),
        ("integer", "34"),
        ("symbol", ")"),
    ]


def test_tokenizer_handles_string_literals() -> None:
    tokens = tokenize("VALUES('it''s fine')")
    assert [(token.kind, token.value) for token in tokens] == [
        ("keyword", "VALUES"),
        ("symbol", "("),
        ("string", "it's fine"),
        ("symbol", ")"),
    ]


def test_tokenizer_handles_null_literal() -> None:
    tokens = tokenize("VALUES(NULL)")
    assert [(token.kind, token.value) for token in tokens] == [
        ("keyword", "VALUES"),
        ("symbol", "("),
        ("null", "NULL"),
        ("symbol", ")"),
    ]


def test_tokenizer_handles_punctuation() -> None:
    tokens = tokenize("SELECT t1.a + 1 FROM t1 WHERE a>=1;")
    assert [(token.kind, token.value) for token in tokens] == [
        ("keyword", "SELECT"),
        ("identifier", "t1"),
        ("symbol", "."),
        ("identifier", "a"),
        ("symbol", "+"),
        ("integer", "1"),
        ("keyword", "FROM"),
        ("identifier", "t1"),
        ("keyword", "WHERE"),
        ("identifier", "a"),
        ("symbol", ">="),
        ("integer", "1"),
        ("symbol", ";"),
    ]
