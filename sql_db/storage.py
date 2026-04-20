from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Table:
    name: str
    columns: list[str] = field(default_factory=list)
    rows: list[tuple[object, ...]] = field(default_factory=list)

    def column_index(self, column_name: str) -> int:
        try:
            return self.columns.index(column_name)
        except ValueError as exc:
            raise ValueError(f"unknown column {column_name!r} on table {self.name!r}") from exc


@dataclass
class InMemoryStorage:
    tables: dict[str, Table] = field(default_factory=dict)

    def create_table(self, table_name: str, columns: tuple[str, ...]) -> None:
        normalized_name = table_name.lower()
        if normalized_name in self.tables:
            raise ValueError(f"table {table_name!r} already exists")
        self.tables[normalized_name] = Table(name=normalized_name, columns=list(columns))

    def insert_row(
        self,
        table_name: str,
        values: tuple[object, ...],
        columns: tuple[str, ...] | None = None,
    ) -> None:
        table = self.read_table(table_name)
        if columns is None:
            if len(values) != len(table.columns):
                raise ValueError(f"expected {len(table.columns)} values for table {table.name!r}")
            table.rows.append(tuple(values))
            return
        if len(columns) != len(values):
            raise ValueError("column count does not match value count")
        row = [None] * len(table.columns)
        for column_name, value in zip(columns, values, strict=True):
            row[table.column_index(column_name.lower())] = value
        table.rows.append(tuple(row))

    def read_table(self, table_name: str) -> Table:
        normalized_name = table_name.lower()
        if normalized_name not in self.tables:
            raise ValueError(f"unknown table {table_name!r}")
        return self.tables[normalized_name]
