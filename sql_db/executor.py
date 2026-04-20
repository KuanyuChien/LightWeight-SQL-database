from __future__ import annotations

from dataclasses import dataclass, field

from .parser import (
    BetweenExpression,
    BinaryExpression,
    CaseExpression,
    ColumnExpression,
    CompoundSelectStatement,
    CreateIndexStatement,
    CreateTableStatement,
    EmptyStatement,
    ExistsExpression,
    Expression,
    FunctionExpression,
    InExpression,
    InsertStatement,
    IsNullExpression,
    LiteralExpression,
    OrderByTerm,
    SelectItem,
    SelectStatement,
    StarExpression,
    Statement,
    SubqueryExpression,
    TableReference,
    UnaryExpression,
    parse,
)
from .storage import InMemoryStorage
from .tokenizer import tokenize


AGGREGATE_FUNCTIONS = {"avg", "count", "max", "min", "sum"}


@dataclass(frozen=True)
class RowContext:
    table_name: str | None
    table_alias: str | None
    columns: tuple[str, ...]
    row: tuple[object, ...]
    outer: RowContext | None = None
    scope_level: int = 0


@dataclass
class ExecutionResult:
    success: bool
    rows: list[tuple[object, ...]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    error: str | None = None


class DatabaseEngine:
    def __init__(self, storage: InMemoryStorage | None = None) -> None:
        self.storage = storage or InMemoryStorage()
        self._table_indexes: dict[tuple[str, str], dict[object, list[int]]] = {}

    def execute(self, sql: str) -> ExecutionResult:
        try:
            statement = self._parse(sql)
            return self._execute_statement(statement)
        except Exception as exc:
            return ExecutionResult(success=False, error=str(exc))

    def _parse(self, sql: str) -> Statement:
        return parse(tokenize(sql))

    def _execute_statement(self, statement: Statement) -> ExecutionResult:
        if isinstance(statement, EmptyStatement):
            return ExecutionResult(success=True)
        if isinstance(statement, CreateTableStatement):
            self.storage.create_table(statement.table_name, statement.columns)
            self._table_indexes.clear()
            return ExecutionResult(success=True)
        if isinstance(statement, CreateIndexStatement):
            return ExecutionResult(success=True)
        if isinstance(statement, InsertStatement):
            self.storage.insert_row(statement.table_name, statement.values, statement.columns)
            self._table_indexes.clear()
            return ExecutionResult(success=True)
        if isinstance(statement, (SelectStatement, CompoundSelectStatement)):
            rows = self._select_rows(statement)
            columns = self._select_column_names(statement, rows)
            return ExecutionResult(success=True, rows=rows, columns=columns)
        return ExecutionResult(success=False, error="unsupported statement")

    def _select_rows(
        self,
        statement: Statement,
        outer_context: RowContext | None = None,
    ) -> list[tuple[object, ...]]:
        if isinstance(statement, CompoundSelectStatement):
            return self._combine_select_rows(statement, outer_context)
        source_contexts = self._source_contexts(statement.from_tables, statement.where_clause, outer_context)

        aggregate_query = self._is_aggregate_query(statement)
        if aggregate_query:
            aggregate_context = source_contexts[0] if source_contexts else self._empty_context(outer_context)
            records = [
                (
                    aggregate_context,
                    self._project_row(statement.items, aggregate_context, source_contexts),
                )
            ]
        else:
            records = [(context, self._project_row(statement.items, context)) for context in source_contexts]

        for term in reversed(statement.order_by):
            records.sort(
                key=lambda record, order_term=term: self._sort_key(
                    self._order_value(
                        record[0],
                        record[1],
                        statement.items,
                        order_term,
                        source_contexts if aggregate_query else None,
                    )
                ),
                reverse=term.descending,
            )
        return [projection for _, projection in records]

    def _select_column_names(
        self,
        statement: Statement,
        rows: list[tuple[object, ...]],
    ) -> list[str]:
        if isinstance(statement, CompoundSelectStatement):
            return self._select_column_names(statement.left, rows)
        names: list[str] = []
        i = 0
        for item in statement.items:
            if isinstance(item.expression, StarExpression):
                star = item.expression
                table_refs = (
                    [tr for tr in statement.from_tables if (star.table_name is None or tr.table_name.lower() == star.table_name.lower())]
                    if statement.from_tables
                    else []
                )
                for tr in table_refs:
                    try:
                        table = self.storage.read_table(tr.table_name)
                        names.extend(table.columns)
                    except Exception:
                        pass
                if not table_refs:
                    # Fallback: fill from row width
                    total = len(rows[0]) if rows else 0
                    for j in range(total - len(names)):
                        names.append(f"col{len(names) + 1}")
            else:
                if item.alias:
                    names.append(item.alias)
                elif isinstance(item.expression, ColumnExpression):
                    names.append(item.expression.column_name)
                elif isinstance(item.expression, FunctionExpression):
                    names.append(item.expression.name)
                else:
                    names.append(f"col{i + 1}")
            i += 1
        return names

    def _combine_select_rows(
        self,
        statement: CompoundSelectStatement,
        outer_context: RowContext | None,
    ) -> list[tuple[object, ...]]:
        left_rows = self._select_rows(statement.left, outer_context)
        right_rows = self._select_rows(statement.right, outer_context)
        if statement.operator == "UNION":
            if statement.all_modifier:
                return left_rows + right_rows
            return self._deduplicate_rows(left_rows + right_rows)
        if statement.operator == "EXCEPT":
            right_set = set(right_rows)
            return [row for row in self._deduplicate_rows(left_rows) if row not in right_set]
        if statement.operator == "INTERSECT":
            right_set = set(right_rows)
            return [row for row in self._deduplicate_rows(left_rows) if row in right_set]
        raise ValueError(f"unsupported compound operator {statement.operator!r}")

    def _deduplicate_rows(self, rows: list[tuple[object, ...]]) -> list[tuple[object, ...]]:
        seen: set[tuple[object, ...]] = set()
        unique_rows: list[tuple[object, ...]] = []
        for row in rows:
            if row in seen:
                continue
            seen.add(row)
            unique_rows.append(row)
        return unique_rows

    def _source_contexts(
        self,
        from_tables: tuple[TableReference, ...],
        where_clause: Expression | None,
        outer_context: RowContext | None,
    ) -> list[RowContext]:
        scope_level = self._next_scope_level(outer_context)
        where_terms = self._where_terms(from_tables, where_clause)
        if not from_tables:
            empty_context = self._empty_context(outer_context)
            return [empty_context] if self._where_terms_match(where_terms, empty_context, frozenset()) else []
        candidate_row_indexes = self._table_candidate_indexes(from_tables, where_terms, outer_context, scope_level)
        if any(not row_indexes for row_indexes in candidate_row_indexes.values()):
            return []
        checked_term_indexes = frozenset(
            term_index
            for term_index, (_, dependencies) in enumerate(where_terms)
            if not dependencies
        )
        return self._scan_source_contexts(
            from_tables,
            where_terms,
            candidate_row_indexes,
            outer_context,
            scope_level,
            0,
            frozenset(),
            checked_term_indexes,
        )

    def _scan_source_contexts(
        self,
        from_tables: tuple[TableReference, ...],
        where_terms: tuple[tuple[Expression, frozenset[str]], ...],
        candidate_row_indexes: dict[str, list[int]],
        base_context: RowContext | None,
        scope_level: int,
        table_index: int,
        bound_tables: frozenset[str],
        checked_term_indexes: frozenset[int],
    ) -> list[RowContext]:
        if table_index >= len(from_tables):
            return [] if base_context is None else [base_context]

        table_reference = from_tables[table_index]
        table = self.storage.read_table(table_reference.table_name)
        visible_name = table_reference.alias or table.name
        next_bound_tables = bound_tables | {visible_name}
        next_contexts: list[RowContext] = []
        rows, enforced_term_indexes = self._candidate_rows(
            table_reference,
            table,
            candidate_row_indexes[visible_name],
            where_terms,
            base_context,
            bound_tables,
        )
        next_checked_term_indexes = checked_term_indexes | enforced_term_indexes
        for row in rows:
            next_context = RowContext(
                table_name=table.name,
                table_alias=table_reference.alias,
                columns=tuple(table.columns),
                row=row,
                outer=base_context,
                scope_level=scope_level,
            )
            if not self._where_terms_match(
                where_terms,
                next_context,
                next_bound_tables,
                next_checked_term_indexes,
            ):
                continue
            if table_index == len(from_tables) - 1:
                next_contexts.append(next_context)
                continue
            next_contexts.extend(
                self._scan_source_contexts(
                    from_tables,
                    where_terms,
                    candidate_row_indexes,
                    next_context,
                    scope_level,
                    table_index + 1,
                    next_bound_tables,
                    next_checked_term_indexes,
                )
            )
        return next_contexts

    def _table_candidate_indexes(
        self,
        from_tables: tuple[TableReference, ...],
        where_terms: tuple[tuple[Expression, frozenset[str]], ...],
        outer_context: RowContext | None,
        scope_level: int,
    ) -> dict[str, list[int]]:
        table_references = {
            self._visible_table_reference_name(table_reference, table_reference.table_name): table_reference
            for table_reference in from_tables
        }
        tables = {
            visible_name: self.storage.read_table(table_reference.table_name)
            for visible_name, table_reference in table_references.items()
        }
        candidate_indexes = {
            visible_name: list(range(len(table.rows)))
            for visible_name, table in tables.items()
        }

        for expression, dependencies in where_terms:
            if dependencies:
                continue
            if not self._is_true(self._evaluate_expression(expression, self._empty_context(outer_context))):
                return {visible_name: [] for visible_name in tables}

        for visible_name, table_reference in table_references.items():
            table = tables[visible_name]
            single_table_terms = [
                expression for expression, dependencies in where_terms if dependencies == frozenset({visible_name})
            ]
            if not single_table_terms:
                continue
            filtered_indexes: list[int] = []
            for row_index in candidate_indexes[visible_name]:
                context = RowContext(
                    table_name=table.name,
                    table_alias=table_reference.alias,
                    columns=tuple(table.columns),
                    row=table.rows[row_index],
                    outer=outer_context,
                    scope_level=scope_level,
                )
                if all(self._is_true(self._evaluate_expression(expression, context)) for expression in single_table_terms):
                    filtered_indexes.append(row_index)
            candidate_indexes[visible_name] = filtered_indexes

        join_terms = [
            join_term
            for expression, dependencies in where_terms
            if len(dependencies) == 2
            for join_term in [self._join_term_columns(expression, tables)]
            if join_term is not None
        ]
        changed = True
        while changed:
            changed = False
            for left_name, left_column, right_name, right_column in join_terms:
                left_table = tables[left_name]
                right_table = tables[right_name]
                left_column_index = left_table.column_index(left_column)
                right_column_index = right_table.column_index(right_column)
                right_values = {
                    right_table.rows[row_index][right_column_index]
                    for row_index in candidate_indexes[right_name]
                    if right_table.rows[row_index][right_column_index] is not None
                }
                filtered_left = [
                    row_index
                    for row_index in candidate_indexes[left_name]
                    if left_table.rows[row_index][left_column_index] is not None
                    and left_table.rows[row_index][left_column_index] in right_values
                ]
                if len(filtered_left) != len(candidate_indexes[left_name]):
                    candidate_indexes[left_name] = filtered_left
                    changed = True

                left_values = {
                    left_table.rows[row_index][left_column_index]
                    for row_index in candidate_indexes[left_name]
                    if left_table.rows[row_index][left_column_index] is not None
                }
                filtered_right = [
                    row_index
                    for row_index in candidate_indexes[right_name]
                    if right_table.rows[row_index][right_column_index] is not None
                    and right_table.rows[row_index][right_column_index] in left_values
                ]
                if len(filtered_right) != len(candidate_indexes[right_name]):
                    candidate_indexes[right_name] = filtered_right
                    changed = True
        return candidate_indexes

    def _candidate_rows(
        self,
        table_reference: TableReference,
        table: object,
        candidate_row_indexes: list[int],
        where_terms: tuple[tuple[Expression, frozenset[str]], ...],
        base_context: RowContext | None,
        bound_tables: frozenset[str],
    ) -> tuple[list[tuple[object, ...]], frozenset[int]]:
        visible_name = table_reference.alias or table.name
        candidate_indexes: set[int] | None = None
        enforced_term_indexes = {
            term_index
            for term_index, (_, dependencies) in enumerate(where_terms)
            if dependencies == frozenset({visible_name})
        }
        for term_index, (expression, dependencies) in enumerate(where_terms):
            if not dependencies.issuperset({visible_name}) or not dependencies.issubset(bound_tables | {visible_name}):
                continue
            lookup = self._indexed_lookup(
                expression,
                table_reference,
                table.columns,
                table.name,
                base_context,
            )
            if lookup is None:
                continue
            if candidate_indexes is None:
                candidate_indexes = {row_index for row_index in candidate_row_indexes if row_index in lookup}
            else:
                candidate_indexes &= lookup
            if not candidate_indexes:
                return [], frozenset(enforced_term_indexes)
            enforced_term_indexes.add(term_index)
        if candidate_indexes is None:
            return [table.rows[index] for index in candidate_row_indexes], frozenset(enforced_term_indexes)
        return (
            [table.rows[index] for index in candidate_row_indexes if index in candidate_indexes],
            frozenset(enforced_term_indexes),
        )

    def _join_term_columns(
        self,
        expression: Expression,
        tables: dict[str, object],
    ) -> tuple[str, str, str, str] | None:
        if not isinstance(expression, BinaryExpression) or expression.operator != "=":
            return None
        left = self._column_dependency(expression.left, tables)
        right = self._column_dependency(expression.right, tables)
        if left is None or right is None or left[0] == right[0]:
            return None
        return left[0], left[1], right[0], right[1]

    def _column_dependency(
        self,
        expression: Expression,
        tables: dict[str, object],
    ) -> tuple[str, str] | None:
        if not isinstance(expression, ColumnExpression):
            return None
        if expression.table_name is not None:
            if expression.table_name not in tables:
                return None
            return (
                expression.table_name,
                expression.column_name,
            ) if expression.column_name in tables[expression.table_name].columns else None
        matches = [
            visible_name
            for visible_name, table in tables.items()
            if expression.column_name in table.columns
        ]
        if len(matches) != 1:
            return None
        return matches[0], expression.column_name

    def _indexed_lookup(
        self,
        expression: Expression,
        table_reference: TableReference,
        columns: list[str],
        table_name: str,
        base_context: RowContext | None,
    ) -> set[int] | None:
        if not isinstance(expression, BinaryExpression) or expression.operator != "=":
            return None
        for current_side, other_side in ((expression.left, expression.right), (expression.right, expression.left)):
            column_name = self._lookup_column_name(current_side, table_reference, columns)
            if column_name is None:
                continue
            other_dependencies = self._expression_dependencies(
                other_side,
                {self._visible_table_reference_name(table_reference, table_name): frozenset(columns)}
            )
            if other_dependencies:
                continue
            lookup_value = self._evaluate_expression(other_side, base_context or self._empty_context(None))
            if lookup_value is None:
                return set()
            return set(self._table_index_rows(table_name, column_name).get(lookup_value, []))
        return None

    def _lookup_column_name(
        self,
        expression: Expression,
        table_reference: TableReference,
        columns: list[str],
    ) -> str | None:
        if not isinstance(expression, ColumnExpression) or expression.column_name not in columns:
            return None
        visible_name = table_reference.alias or table_reference.table_name
        if expression.table_name is None:
            return expression.column_name
        return expression.column_name if expression.table_name == visible_name else None

    def _table_index_rows(self, table_name: str, column_name: str) -> dict[object, list[int]]:
        key = (table_name, column_name)
        if key in self._table_indexes:
            return self._table_indexes[key]
        table = self.storage.read_table(table_name)
        column_index = table.column_index(column_name)
        index: dict[object, list[int]] = {}
        for row_index, row in enumerate(table.rows):
            index.setdefault(row[column_index], []).append(row_index)
        self._table_indexes[key] = index
        return index

    def _visible_table_reference_name(self, table_reference: TableReference, table_name: str) -> str:
        return table_reference.alias or table_name

    def _where_terms(
        self,
        from_tables: tuple[TableReference, ...],
        where_clause: Expression | None,
    ) -> tuple[tuple[Expression, frozenset[str]], ...]:
        if where_clause is None:
            return ()
        table_columns = {
            (table_reference.alias or table_reference.table_name): frozenset(
                self.storage.read_table(table_reference.table_name).columns
            )
            for table_reference in from_tables
        }
        return tuple(
            (term, self._expression_dependencies(term, table_columns))
            for term in self._split_and_terms(where_clause)
        )

    def _split_and_terms(self, expression: Expression) -> tuple[Expression, ...]:
        if isinstance(expression, BinaryExpression) and expression.operator == "AND":
            return self._split_and_terms(expression.left) + self._split_and_terms(expression.right)
        return (expression,)

    def _expression_dependencies(
        self,
        expression: Expression,
        table_columns: dict[str, frozenset[str]],
    ) -> frozenset[str]:
        if isinstance(expression, LiteralExpression):
            return frozenset()
        if isinstance(expression, ColumnExpression):
            if expression.table_name is not None:
                return frozenset({expression.table_name}) if expression.table_name in table_columns else frozenset()
            return frozenset(
                table_name
                for table_name, columns in table_columns.items()
                if expression.column_name in columns
            )
        if isinstance(expression, UnaryExpression):
            return self._expression_dependencies(expression.operand, table_columns)
        if isinstance(expression, BinaryExpression):
            return self._expression_dependencies(expression.left, table_columns) | self._expression_dependencies(
                expression.right, table_columns
            )
        if isinstance(expression, IsNullExpression):
            return self._expression_dependencies(expression.operand, table_columns)
        if isinstance(expression, BetweenExpression):
            return (
                self._expression_dependencies(expression.operand, table_columns)
                | self._expression_dependencies(expression.lower_bound, table_columns)
                | self._expression_dependencies(expression.upper_bound, table_columns)
            )
        if isinstance(expression, InExpression):
            dependencies = self._expression_dependencies(expression.operand, table_columns)
            for option in expression.options:
                dependencies |= self._expression_dependencies(option, table_columns)
            return dependencies
        if isinstance(expression, CaseExpression):
            dependencies = frozenset()
            if expression.base_expression is not None:
                dependencies |= self._expression_dependencies(expression.base_expression, table_columns)
            if expression.else_expression is not None:
                dependencies |= self._expression_dependencies(expression.else_expression, table_columns)
            for when_expression, then_expression in expression.when_clauses:
                dependencies |= self._expression_dependencies(when_expression, table_columns)
                dependencies |= self._expression_dependencies(then_expression, table_columns)
            return dependencies
        if isinstance(expression, FunctionExpression):
            dependencies = frozenset()
            for argument in expression.arguments:
                dependencies |= self._expression_dependencies(argument, table_columns)
            return dependencies
        if isinstance(expression, (ExistsExpression, SubqueryExpression, StarExpression)):
            return frozenset(table_columns)
        return frozenset(table_columns)

    def _where_terms_match(
        self,
        where_terms: tuple[tuple[Expression, frozenset[str]], ...],
        context: RowContext,
        bound_tables: frozenset[str],
        checked_term_indexes: frozenset[int] = frozenset(),
    ) -> bool:
        for term_index, (expression, dependencies) in enumerate(where_terms):
            if term_index in checked_term_indexes:
                continue
            if not dependencies.issubset(bound_tables):
                continue
            if not self._is_true(self._evaluate_expression(expression, context)):
                return False
        return True

    def _empty_context(self, outer_context: RowContext | None) -> RowContext:
        return RowContext(None, None, (), (), outer_context, self._next_scope_level(outer_context))

    def _next_scope_level(self, outer_context: RowContext | None) -> int:
        if outer_context is None:
            return 0
        return outer_context.scope_level + 1

    def _project_row(
        self,
        items: tuple[SelectItem, ...],
        context: RowContext,
        aggregate_contexts: list[RowContext] | None = None,
    ) -> tuple[object, ...]:
        values, _ = self._project_row_with_names(items, context, aggregate_contexts)
        return values

    def _project_row_with_names(
        self,
        items: tuple[SelectItem, ...],
        context: RowContext,
        aggregate_contexts: list[RowContext] | None = None,
    ) -> tuple[tuple[object, ...], tuple[str | None, ...]]:
        values: list[object] = []
        names: list[str | None] = []
        for item in items:
            if isinstance(item.expression, StarExpression):
                star_values, star_names = self._expand_star(item.expression, context)
                values.extend(star_values)
                names.extend(star_names)
                continue
            values.append(self._evaluate_expression(item.expression, context, aggregate_contexts))
            names.append(item.alias or self._expression_name(item.expression))
        return tuple(values), tuple(names)

    def _expand_star(
        self,
        expression: StarExpression,
        context: RowContext,
    ) -> tuple[list[object], list[str]]:
        local_contexts = self._local_scope_contexts(context)
        if expression.table_name is not None:
            for local_context in local_contexts:
                if expression.table_name == self._visible_table_name(local_context):
                    return list(local_context.row), list(local_context.columns)
            raise ValueError(f"unknown table {expression.table_name!r} in SELECT *")
        values: list[object] = []
        names: list[str] = []
        for local_context in local_contexts:
            values.extend(local_context.row)
            names.extend(local_context.columns)
        return values, names

    def _local_scope_contexts(self, context: RowContext) -> list[RowContext]:
        local_contexts: list[RowContext] = []
        current: RowContext | None = context
        while current is not None and current.scope_level == context.scope_level:
            local_contexts.append(current)
            current = current.outer
        local_contexts.reverse()
        return local_contexts

    def _expression_name(self, expression: Expression) -> str | None:
        if isinstance(expression, ColumnExpression):
            return expression.column_name
        return None

    def _order_value(
        self,
        context: RowContext,
        projected_row: tuple[object, ...],
        items: tuple[SelectItem, ...],
        order_term: OrderByTerm,
        aggregate_contexts: list[RowContext] | None = None,
    ) -> object:
        if isinstance(order_term.key, int):
            return projected_row[order_term.key - 1]
        _, output_names = self._project_row_with_names(items, context, aggregate_contexts)
        if (
            isinstance(order_term.key, ColumnExpression)
            and order_term.key.table_name is None
            and order_term.key.column_name in output_names
        ):
            return projected_row[output_names.index(order_term.key.column_name)]
        return self._evaluate_expression(order_term.key, context, aggregate_contexts)

    def _evaluate_expression(
        self,
        expression: Expression,
        context: RowContext,
        aggregate_contexts: list[RowContext] | None = None,
    ) -> object:
        if isinstance(expression, LiteralExpression):
            return expression.value
        if isinstance(expression, ColumnExpression):
            return self._resolve_column(expression, context)
        if isinstance(expression, UnaryExpression):
            return self._apply_unary_operator(
                expression.operator,
                self._evaluate_expression(expression.operand, context, aggregate_contexts),
            )
        if isinstance(expression, BinaryExpression):
            if expression.operator == "AND":
                return self._sql_and(
                    self._evaluate_expression(expression.left, context, aggregate_contexts),
                    self._evaluate_expression(expression.right, context, aggregate_contexts),
                )
            if expression.operator == "OR":
                return self._sql_or(
                    self._evaluate_expression(expression.left, context, aggregate_contexts),
                    self._evaluate_expression(expression.right, context, aggregate_contexts),
                )
            return self._apply_binary_operator(
                expression.operator,
                self._evaluate_expression(expression.left, context, aggregate_contexts),
                self._evaluate_expression(expression.right, context, aggregate_contexts),
            )
        if isinstance(expression, IsNullExpression):
            is_null = self._evaluate_expression(expression.operand, context, aggregate_contexts) is None
            return not is_null if expression.negated else is_null
        if isinstance(expression, BetweenExpression):
            operand = self._evaluate_expression(expression.operand, context, aggregate_contexts)
            lower_bound = self._evaluate_expression(expression.lower_bound, context, aggregate_contexts)
            upper_bound = self._evaluate_expression(expression.upper_bound, context, aggregate_contexts)
            result = self._sql_and(
                self._apply_binary_operator(">=", operand, lower_bound),
                self._apply_binary_operator("<=", operand, upper_bound),
            )
            return self._sql_not(result) if expression.negated else result
        if isinstance(expression, InExpression):
            operand = self._evaluate_expression(expression.operand, context, aggregate_contexts)
            options = [self._evaluate_expression(option, context, aggregate_contexts) for option in expression.options]
            result = self._evaluate_in_expression(operand, options)
            return self._sql_not(result) if expression.negated else result
        if isinstance(expression, CaseExpression):
            return self._evaluate_case_expression(expression, context, aggregate_contexts)
        if isinstance(expression, FunctionExpression):
            return self._evaluate_function(expression, context, aggregate_contexts)
        if isinstance(expression, ExistsExpression):
            return bool(self._select_rows(expression.query, context))
        if isinstance(expression, SubqueryExpression):
            rows = self._select_rows(expression.query, context)
            if not rows:
                return None
            if len(rows) != 1 or len(rows[0]) != 1:
                raise ValueError("scalar subquery returned multiple values")
            return rows[0][0]
        if isinstance(expression, StarExpression):
            raise ValueError("cannot evaluate * as an expression")
        raise ValueError("unsupported expression")

    def _evaluate_case_expression(
        self,
        expression: CaseExpression,
        context: RowContext,
        aggregate_contexts: list[RowContext] | None,
    ) -> object:
        base_value = None
        if expression.base_expression is not None:
            base_value = self._evaluate_expression(expression.base_expression, context, aggregate_contexts)
        for when_expression, then_expression in expression.when_clauses:
            if expression.base_expression is None:
                matches = self._is_true(self._evaluate_expression(when_expression, context, aggregate_contexts))
            else:
                matches = self._apply_binary_operator(
                    "=",
                    base_value,
                    self._evaluate_expression(when_expression, context, aggregate_contexts),
                ) is True
            if matches:
                return self._evaluate_expression(then_expression, context, aggregate_contexts)
        if expression.else_expression is None:
            return None
        return self._evaluate_expression(expression.else_expression, context, aggregate_contexts)

    def _evaluate_function(
        self,
        expression: FunctionExpression,
        context: RowContext,
        aggregate_contexts: list[RowContext] | None,
    ) -> object:
        if expression.name in AGGREGATE_FUNCTIONS:
            if aggregate_contexts is None:
                raise ValueError(f"aggregate function {expression.name!r} requires an aggregate query")
            return self._evaluate_aggregate_function(expression, aggregate_contexts)
        arguments = [self._evaluate_expression(argument, context, aggregate_contexts) for argument in expression.arguments]
        if expression.name == "abs":
            return None if arguments[0] is None else abs(arguments[0])
        if expression.name == "coalesce":
            for argument in arguments:
                if argument is not None:
                    return argument
            return None
        raise ValueError(f"unknown function {expression.name!r}")

    def _evaluate_aggregate_function(
        self,
        expression: FunctionExpression,
        contexts: list[RowContext],
    ) -> object:
        if expression.name == "count":
            if expression.star_argument:
                return len(contexts)
            return sum(
                1
                for context in contexts
                if self._evaluate_expression(expression.arguments[0], context) is not None
            )

        values = [self._evaluate_expression(expression.arguments[0], context) for context in contexts]
        non_null_values = [value for value in values if value is not None]
        if expression.name == "avg":
            if not non_null_values:
                return None
            total = sum(non_null_values)
            if isinstance(total, int) and total % len(non_null_values) == 0:
                return total // len(non_null_values)
            return total / len(non_null_values)
        if expression.name == "sum":
            return None if not non_null_values else sum(non_null_values)
        if expression.name == "min":
            return None if not non_null_values else min(non_null_values)
        if expression.name == "max":
            return None if not non_null_values else max(non_null_values)
        raise ValueError(f"unknown aggregate function {expression.name!r}")

    def _resolve_column(self, expression: ColumnExpression, context: RowContext | None) -> object:
        if context is None:
            raise ValueError(f"unknown column {expression.column_name!r}")
        if self._column_matches_context(expression, context):
            return context.row[context.columns.index(expression.column_name)]
        return self._resolve_column(expression, context.outer)

    def _column_matches_context(self, expression: ColumnExpression, context: RowContext) -> bool:
        if expression.column_name not in context.columns:
            return False
        if expression.table_name is None:
            return True
        return expression.table_name == self._visible_table_name(context)

    def _visible_table_name(self, context: RowContext) -> str | None:
        if context.table_alias is not None:
            return context.table_alias
        return context.table_name

    def _apply_unary_operator(self, operator: str, operand: object) -> object:
        if operator == "NOT":
            return self._sql_not(operand)
        if operand is None:
            return None
        if operator == "+":
            return operand
        if operator == "-":
            return -operand
        raise ValueError(f"unsupported unary operator {operator!r}")

    def _apply_binary_operator(self, operator: str, left: object, right: object) -> object:
        if operator in {"+", "-", "*", "/", "%"}:
            return self._apply_arithmetic_operator(operator, left, right)
        if left is None or right is None:
            return None
        if operator == "=":
            return left == right
        if operator in {"<>", "!="}:
            return left != right
        if operator == "<":
            return left < right
        if operator == "<=":
            return left <= right
        if operator == ">":
            return left > right
        if operator == ">=":
            return left >= right
        raise ValueError(f"unsupported binary operator {operator!r}")

    def _apply_arithmetic_operator(self, operator: str, left: object, right: object) -> object:
        if left is None or right is None:
            return None
        if operator == "+":
            return left + right
        if operator == "-":
            return left - right
        if operator == "*":
            return left * right
        if operator == "/":
            if right == 0:
                return None
            if isinstance(left, int) and isinstance(right, int):
                return int(left / right)
            return left / right
        if operator == "%":
            return None if right == 0 else left % right
        raise ValueError(f"unsupported arithmetic operator {operator!r}")

    def _evaluate_in_expression(self, operand: object, options: list[object]) -> object:
        if operand is None:
            return None
        saw_null = False
        for option in options:
            if option is None:
                saw_null = True
                continue
            if operand == option:
                return True
        if saw_null:
            return None
        return False

    def _is_aggregate_query(self, statement: SelectStatement) -> bool:
        return any(self._contains_aggregate(item.expression) for item in statement.items) or any(
            not isinstance(term.key, int) and self._contains_aggregate(term.key)
            for term in statement.order_by
        )

    def _contains_aggregate(self, expression: Expression) -> bool:
        if isinstance(expression, FunctionExpression):
            return expression.name in AGGREGATE_FUNCTIONS or any(
                self._contains_aggregate(argument) for argument in expression.arguments
            )
        if isinstance(expression, (ExistsExpression, SubqueryExpression)):
            return False
        if isinstance(expression, UnaryExpression):
            return self._contains_aggregate(expression.operand)
        if isinstance(expression, BinaryExpression):
            return self._contains_aggregate(expression.left) or self._contains_aggregate(expression.right)
        if isinstance(expression, IsNullExpression):
            return self._contains_aggregate(expression.operand)
        if isinstance(expression, BetweenExpression):
            return (
                self._contains_aggregate(expression.operand)
                or self._contains_aggregate(expression.lower_bound)
                or self._contains_aggregate(expression.upper_bound)
            )
        if isinstance(expression, InExpression):
            return self._contains_aggregate(expression.operand) or any(
                self._contains_aggregate(option) for option in expression.options
            )
        if isinstance(expression, CaseExpression):
            if expression.base_expression is not None and self._contains_aggregate(expression.base_expression):
                return True
            if expression.else_expression is not None and self._contains_aggregate(expression.else_expression):
                return True
            return any(
                self._contains_aggregate(when_expression) or self._contains_aggregate(then_expression)
                for when_expression, then_expression in expression.when_clauses
            )
        return False

    def _is_true(self, value: object) -> bool:
        return value is True

    def _sql_not(self, value: object) -> object:
        if value is None:
            return None
        return not bool(value)

    def _sql_and(self, left: object, right: object) -> object:
        if left is False or right is False:
            return False
        if left is None or right is None:
            return None
        return bool(left) and bool(right)

    def _sql_or(self, left: object, right: object) -> object:
        if left is True or right is True:
            return True
        if left is None or right is None:
            return None
        return bool(left) or bool(right)

    def _sort_key(self, value: object) -> tuple[bool, object]:
        return (value is not None, value)
