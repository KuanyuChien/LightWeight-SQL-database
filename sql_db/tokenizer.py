from __future__ import annotations

from dataclasses import dataclass


KEYWORDS = {
    "ALL",
    "AND",
    "AS",
    "ASC",
    "BETWEEN",
    "BY",
    "CASE",
    "CREATE",
    "DESC",
    "ELSE",
    "END",
    "EXCEPT",
    "EXISTS",
    "FROM",
    "INDEX",
    "IN",
    "INSERT",
    "INTERSECT",
    "INTO",
    "IS",
    "KEY",
    "NOT",
    "ON",
    "OR",
    "ORDER",
    "PRIMARY",
    "SELECT",
    "TABLE",
    "THEN",
    "UNION",
    "VALUES",
    "WHEN",
    "WHERE",
}

SYMBOLS = {"(", ")", ",", "*", ";", "+", "-", "/", "%", "=", "<", ">", "."}
MULTI_CHARACTER_SYMBOLS = {"<=", ">=", "<>", "!="}


@dataclass(frozen=True)
class Token:
    kind: str
    value: str


def tokenize(sql: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    while index < len(sql):
        char = sql[index]
        if char.isspace():
            index += 1
            continue
        pair = sql[index : index + 2]
        if pair in MULTI_CHARACTER_SYMBOLS:
            tokens.append(Token(kind="symbol", value=pair))
            index += 2
            continue
        if char in SYMBOLS:
            tokens.append(Token(kind="symbol", value=char))
            index += 1
            continue
        if char == "'":
            value, index = _read_string(sql, index)
            tokens.append(Token(kind="string", value=value))
            continue
        if char.isdigit():
            value, index = _read_integer(sql, index)
            tokens.append(Token(kind="integer", value=value))
            continue
        if char.isalpha() or char == "_":
            value, index = _read_identifier(sql, index)
            upper = value.upper()
            if upper == "NULL":
                tokens.append(Token(kind="null", value=upper))
            elif upper in KEYWORDS:
                tokens.append(Token(kind="keyword", value=upper))
            else:
                tokens.append(Token(kind="identifier", value=value))
            continue
        raise ValueError(f"unexpected character {char!r}")
    return tokens


def _read_string(sql: str, start: int) -> tuple[str, int]:
    index = start + 1
    parts: list[str] = []
    while index < len(sql):
        char = sql[index]
        if char == "'":
            if index + 1 < len(sql) and sql[index + 1] == "'":
                parts.append("'")
                index += 2
                continue
            return "".join(parts), index + 1
        parts.append(char)
        index += 1
    raise ValueError("unterminated string literal")


def _read_integer(sql: str, start: int) -> tuple[str, int]:
    index = start + 1
    while index < len(sql) and sql[index].isdigit():
        index += 1
    return sql[start:index], index


def _read_identifier(sql: str, start: int) -> tuple[str, int]:
    index = start + 1
    while index < len(sql) and (sql[index].isalnum() or sql[index] == "_"):
        index += 1
    return sql[start:index], index
