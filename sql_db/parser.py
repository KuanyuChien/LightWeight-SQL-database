from __future__ import annotations

from dataclasses import dataclass

from .tokenizer import Token


class Statement:
    pass


class Expression:
    pass


@dataclass(frozen=True)
class EmptyStatement(Statement):
    pass


@dataclass(frozen=True)
class CreateTableStatement(Statement):
    table_name: str
    columns: tuple[str, ...]


@dataclass(frozen=True)
class CreateIndexStatement(Statement):
    index_name: str
    table_name: str


@dataclass(frozen=True)
class InsertStatement(Statement):
    table_name: str
    columns: tuple[str, ...] | None
    values: tuple[object, ...]


@dataclass(frozen=True)
class LiteralExpression(Expression):
    value: object


@dataclass(frozen=True)
class ColumnExpression(Expression):
    column_name: str
    table_name: str | None = None


@dataclass(frozen=True)
class UnaryExpression(Expression):
    operator: str
    operand: Expression


@dataclass(frozen=True)
class BinaryExpression(Expression):
    operator: str
    left: Expression
    right: Expression


@dataclass(frozen=True)
class IsNullExpression(Expression):
    operand: Expression
    negated: bool = False


@dataclass(frozen=True)
class BetweenExpression(Expression):
    operand: Expression
    lower_bound: Expression
    upper_bound: Expression
    negated: bool = False


@dataclass(frozen=True)
class InExpression(Expression):
    operand: Expression
    options: tuple[Expression, ...]
    negated: bool = False


@dataclass(frozen=True)
class CaseExpression(Expression):
    base_expression: Expression | None
    when_clauses: tuple[tuple[Expression, Expression], ...]
    else_expression: Expression | None


@dataclass(frozen=True)
class FunctionExpression(Expression):
    name: str
    arguments: tuple[Expression, ...] = ()
    star_argument: bool = False


@dataclass(frozen=True)
class TableReference:
    table_name: str
    alias: str | None = None


@dataclass(frozen=True)
class SelectItem:
    expression: Expression
    alias: str | None = None


@dataclass(frozen=True)
class OrderByTerm:
    key: Expression | int
    descending: bool = False


@dataclass(frozen=True)
class SelectStatement(Statement):
    items: tuple[SelectItem, ...]
    from_tables: tuple[TableReference, ...] = ()
    where_clause: Expression | None = None
    order_by: tuple[OrderByTerm, ...] = ()


@dataclass(frozen=True)
class CompoundSelectStatement(Statement):
    left: Statement
    operator: str
    right: Statement
    all_modifier: bool = False


@dataclass(frozen=True)
class ExistsExpression(Expression):
    query: Statement


@dataclass(frozen=True)
class SubqueryExpression(Expression):
    query: Statement


@dataclass(frozen=True)
class StarExpression(Expression):
    table_name: str | None = None


def parse(tokens: list[Token]) -> Statement:
    if not tokens:
        return EmptyStatement()
    parser = Parser(tokens)
    return parser.parse_statement()


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    def parse_statement(self) -> Statement:
        if self._match_keyword("CREATE"):
            statement = self._parse_create_statement()
        elif self._match_keyword("INSERT"):
            statement = self._parse_insert()
        elif self._match_keyword("SELECT"):
            statement = self._parse_select_statement()
        else:
            token = self._peek()
            raise ValueError(f"unsupported statement starting with {token.value!r}")
        self._consume_optional_symbol(";")
        if self._peek() is not None:
            raise ValueError(f"unexpected token {self._peek().value!r}")
        return statement

    def _parse_create_statement(self) -> Statement:
        self._consume_keyword("CREATE")
        if self._match_keyword("TABLE"):
            return self._parse_create_table()
        if self._match_keyword("INDEX"):
            return self._parse_create_index()
        token = self._peek()
        found = "end of input" if token is None else token.value
        raise ValueError(f"unsupported CREATE statement {found!r}")

    def _parse_create_table(self) -> CreateTableStatement:
        self._consume_keyword("TABLE")
        table_name = self._consume_identifier()
        self._consume_symbol("(")
        columns: list[str] = []
        while True:
            if self._consume_optional_symbol(")"):
                break
            columns.append(self._consume_identifier())
            self._skip_column_definition()
            if self._consume_optional_symbol(","):
                continue
            self._consume_symbol(")")
            break
        return CreateTableStatement(table_name=table_name, columns=tuple(columns))

    def _parse_create_index(self) -> CreateIndexStatement:
        self._consume_keyword("INDEX")
        index_name = self._consume_identifier()
        self._consume_keyword("ON")
        table_name = self._consume_identifier()
        self._skip_index_column_list()
        return CreateIndexStatement(index_name=index_name, table_name=table_name)

    def _parse_insert(self) -> InsertStatement:
        self._consume_keyword("INSERT")
        self._consume_keyword("INTO")
        table_name = self._consume_identifier()
        columns = self._parse_identifier_list() if self._current_symbol() == "(" else None
        self._consume_keyword("VALUES")
        values = tuple(self._parse_literal_list())
        return InsertStatement(table_name=table_name, columns=columns, values=values)

    def _parse_select_statement(self) -> Statement:
        statement: Statement = self._parse_select()
        while self._match_keyword("UNION") or self._match_keyword("EXCEPT") or self._match_keyword("INTERSECT"):
            operator = self._consume_keyword_value()
            all_modifier = False
            if operator == "UNION" and self._match_keyword("ALL"):
                self._consume_keyword("ALL")
                all_modifier = True
            statement = CompoundSelectStatement(
                left=statement,
                operator=operator,
                right=self._parse_select(),
                all_modifier=all_modifier,
            )
        return statement

    def _parse_select(self) -> SelectStatement:
        self._consume_keyword("SELECT")
        items = [self._parse_select_item()]
        while self._consume_optional_symbol(","):
            items.append(self._parse_select_item())
        from_tables: tuple[TableReference, ...] = ()
        if self._match_keyword("FROM"):
            self._consume_keyword("FROM")
            tables = [self._parse_table_reference()]
            while self._consume_optional_symbol(","):
                tables.append(self._parse_table_reference())
            from_tables = tuple(tables)
        where_clause = None
        if self._match_keyword("WHERE"):
            self._consume_keyword("WHERE")
            where_clause = self._parse_expression()
        order_by: list[OrderByTerm] = []
        if self._match_keyword("ORDER"):
            self._consume_keyword("ORDER")
            self._consume_keyword("BY")
            order_by = self._parse_order_by_terms()
        return SelectStatement(
            items=tuple(items),
            from_tables=from_tables,
            where_clause=where_clause,
            order_by=tuple(order_by),
        )

    def _parse_select_item(self) -> SelectItem:
        if self._consume_optional_symbol("*"):
            return SelectItem(expression=StarExpression())
        if self._match_qualified_star():
            table_name = self._consume_identifier()
            self._consume_symbol(".")
            self._consume_symbol("*")
            return SelectItem(expression=StarExpression(table_name=table_name))
        expression = self._parse_expression()
        alias = None
        if self._match_keyword("AS"):
            self._consume_keyword("AS")
            alias = self._consume_identifier()
        return SelectItem(expression=expression, alias=alias)

    def _parse_table_reference(self) -> TableReference:
        table_name = self._consume_identifier()
        alias = None
        if self._match_keyword("AS"):
            self._consume_keyword("AS")
            alias = self._consume_identifier()
        elif self._peek() is not None and self._peek().kind == "identifier":
            alias = self._consume_identifier()
        return TableReference(table_name=table_name, alias=alias)

    def _parse_identifier_list(self) -> tuple[str, ...]:
        enclosed = self._current_symbol() == "("
        if enclosed:
            self._consume_symbol("(")
        identifiers = [self._consume_identifier()]
        while self._consume_optional_symbol(","):
            identifiers.append(self._consume_identifier())
        if enclosed:
            self._consume_symbol(")")
        return tuple(identifiers)

    def _parse_literal_list(self) -> list[object]:
        self._consume_symbol("(")
        values = [self._consume_literal()]
        while self._consume_optional_symbol(","):
            values.append(self._consume_literal())
        self._consume_symbol(")")
        return values

    def _parse_order_by_terms(self) -> list[OrderByTerm]:
        terms = [self._parse_order_by_term()]
        while self._consume_optional_symbol(","):
            terms.append(self._parse_order_by_term())
        return terms

    def _parse_order_by_term(self) -> OrderByTerm:
        token = self._peek()
        if token is None:
            raise ValueError("expected ORDER BY term")
        if token.kind == "integer":
            self.index += 1
            key: Expression | int = int(token.value)
        else:
            key = self._parse_expression()
        descending = False
        if self._match_keyword("ASC"):
            self._consume_keyword("ASC")
        elif self._match_keyword("DESC"):
            self._consume_keyword("DESC")
            descending = True
        return OrderByTerm(key=key, descending=descending)

    def _parse_expression(self) -> Expression:
        return self._parse_or_expression()

    def _parse_or_expression(self) -> Expression:
        expression = self._parse_and_expression()
        while self._match_keyword("OR"):
            self._consume_keyword("OR")
            expression = BinaryExpression(
                operator="OR",
                left=expression,
                right=self._parse_and_expression(),
            )
        return expression

    def _parse_and_expression(self) -> Expression:
        expression = self._parse_not_expression()
        while self._match_keyword("AND"):
            self._consume_keyword("AND")
            expression = BinaryExpression(
                operator="AND",
                left=expression,
                right=self._parse_not_expression(),
            )
        return expression

    def _parse_not_expression(self) -> Expression:
        if self._match_keyword("NOT") and not self._match_keyword_at(1, "BETWEEN"):
            self._consume_keyword("NOT")
            return UnaryExpression(operator="NOT", operand=self._parse_not_expression())
        return self._parse_comparison_expression()

    def _parse_comparison_expression(self) -> Expression:
        expression = self._parse_additive_expression()
        if self._match_keyword("IS"):
            self._consume_keyword("IS")
            negated = False
            if self._match_keyword("NOT"):
                self._consume_keyword("NOT")
                negated = True
            self._consume_null_literal()
            return IsNullExpression(operand=expression, negated=negated)
        if self._match_keyword("NOT") and self._match_keyword_at(1, "BETWEEN"):
            self._consume_keyword("NOT")
            self._consume_keyword("BETWEEN")
            lower_bound = self._parse_additive_expression()
            self._consume_keyword("AND")
            upper_bound = self._parse_additive_expression()
            return BetweenExpression(
                operand=expression,
                lower_bound=lower_bound,
                upper_bound=upper_bound,
                negated=True,
            )
        if self._match_keyword("BETWEEN"):
            self._consume_keyword("BETWEEN")
            lower_bound = self._parse_additive_expression()
            self._consume_keyword("AND")
            upper_bound = self._parse_additive_expression()
            return BetweenExpression(
                operand=expression,
                lower_bound=lower_bound,
                upper_bound=upper_bound,
            )
        if self._match_keyword("NOT") and self._match_keyword_at(1, "IN"):
            self._consume_keyword("NOT")
            self._consume_keyword("IN")
            return InExpression(operand=expression, options=self._parse_in_list(), negated=True)
        if self._match_keyword("IN"):
            self._consume_keyword("IN")
            return InExpression(operand=expression, options=self._parse_in_list())
        if self._current_symbol() in {"=", "<", "<=", ">", ">=", "<>", "!="}:
            operator = self._consume_symbol_value()
            return BinaryExpression(
                operator=operator,
                left=expression,
                right=self._parse_additive_expression(),
            )
        return expression

    def _parse_additive_expression(self) -> Expression:
        expression = self._parse_multiplicative_expression()
        while self._current_symbol() in {"+", "-"}:
            operator = self._consume_symbol_value()
            expression = BinaryExpression(
                operator=operator,
                left=expression,
                right=self._parse_multiplicative_expression(),
            )
        return expression

    def _parse_multiplicative_expression(self) -> Expression:
        expression = self._parse_unary_expression()
        while self._current_symbol() in {"*", "/", "%"}:
            operator = self._consume_symbol_value()
            expression = BinaryExpression(
                operator=operator,
                left=expression,
                right=self._parse_unary_expression(),
            )
        return expression

    def _parse_unary_expression(self) -> Expression:
        if self._current_symbol() in {"+", "-"}:
            operator = self._consume_symbol_value()
            return UnaryExpression(operator=operator, operand=self._parse_unary_expression())
        return self._parse_primary_expression()

    def _parse_primary_expression(self) -> Expression:
        token = self._peek()
        if token is None:
            raise ValueError("expected expression")
        if token.kind == "integer":
            self.index += 1
            return LiteralExpression(value=int(token.value))
        if token.kind == "string":
            self.index += 1
            return LiteralExpression(value=token.value)
        if token.kind == "null":
            self.index += 1
            return LiteralExpression(value=None)
        if token.kind == "identifier":
            return self._parse_identifier_expression()
        if token.kind == "keyword" and token.value == "CASE":
            return self._parse_case_expression()
        if token.kind == "keyword" and token.value == "EXISTS":
            return self._parse_exists_expression()
        if token.kind == "symbol" and token.value == "(":
            return self._parse_parenthesized_expression()
        raise ValueError(f"expected expression but found {token.value!r}")

    def _parse_identifier_expression(self) -> Expression:
        name = self._consume_identifier()
        if self._current_symbol() == "(":
            return self._parse_function_expression(name)
        if self._consume_optional_symbol("."):
            return ColumnExpression(column_name=self._consume_identifier(), table_name=name)
        return ColumnExpression(column_name=name)

    def _parse_function_expression(self, name: str) -> FunctionExpression:
        self._consume_symbol("(")
        if self._consume_optional_symbol("*"):
            self._consume_symbol(")")
            return FunctionExpression(name=name, star_argument=True)
        arguments: list[Expression] = []
        if not self._consume_optional_symbol(")"):
            arguments.append(self._parse_expression())
            while self._consume_optional_symbol(","):
                arguments.append(self._parse_expression())
            self._consume_symbol(")")
        return FunctionExpression(name=name, arguments=tuple(arguments))

    def _parse_case_expression(self) -> CaseExpression:
        self._consume_keyword("CASE")
        base_expression = None if self._match_keyword("WHEN") else self._parse_expression()
        when_clauses: list[tuple[Expression, Expression]] = []
        while self._match_keyword("WHEN"):
            self._consume_keyword("WHEN")
            when_expression = self._parse_expression()
            self._consume_keyword("THEN")
            then_expression = self._parse_expression()
            when_clauses.append((when_expression, then_expression))
        else_expression = None
        if self._match_keyword("ELSE"):
            self._consume_keyword("ELSE")
            else_expression = self._parse_expression()
        self._consume_keyword("END")
        return CaseExpression(
            base_expression=base_expression,
            when_clauses=tuple(when_clauses),
            else_expression=else_expression,
        )

    def _parse_exists_expression(self) -> ExistsExpression:
        self._consume_keyword("EXISTS")
        self._consume_symbol("(")
        query = self._parse_select()
        self._consume_symbol(")")
        return ExistsExpression(query=query)

    def _parse_parenthesized_expression(self) -> Expression:
        self._consume_symbol("(")
        if self._match_keyword("SELECT"):
            query = self._parse_select_statement()
            self._consume_symbol(")")
            return SubqueryExpression(query=query)
        expression = self._parse_expression()
        self._consume_symbol(")")
        return expression

    def _parse_in_list(self) -> tuple[Expression, ...]:
        self._consume_symbol("(")
        options = [self._parse_expression()]
        while self._consume_optional_symbol(","):
            options.append(self._parse_expression())
        self._consume_symbol(")")
        return tuple(options)

    def _skip_column_definition(self) -> None:
        depth = 0
        while self._peek() is not None:
            value = self._peek().value
            if value == ")" and depth == 0:
                return
            if value == "," and depth == 0:
                return
            if value == "(":
                depth += 1
            elif value == ")":
                depth -= 1
            self.index += 1

    def _skip_index_column_list(self) -> None:
        self._consume_symbol("(")
        depth = 1
        while self._peek() is not None and depth > 0:
            value = self._peek().value
            self.index += 1
            if value == "(":
                depth += 1
            elif value == ")":
                depth -= 1
        if depth != 0:
            raise ValueError("unterminated index column list")

    def _consume_literal(self) -> object:
        token = self._peek()
        if token is None:
            raise ValueError("expected literal")
        if token.kind == "symbol" and token.value in {"+", "-"}:
            sign = -1 if token.value == "-" else 1
            self.index += 1
            token = self._peek()
            if token is None or token.kind != "integer":
                raise ValueError("expected integer literal")
            self.index += 1
            return sign * int(token.value)
        if token.kind == "integer":
            self.index += 1
            return int(token.value)
        if token.kind == "string":
            self.index += 1
            return token.value
        if token.kind == "null":
            self.index += 1
            return None
        raise ValueError(f"expected literal but found {token.value!r}")

    def _consume_null_literal(self) -> None:
        token = self._peek()
        if token is None or token.kind != "null":
            found = "end of input" if token is None else token.value
            raise ValueError(f"expected NULL but found {found!r}")
        self.index += 1

    def _consume_identifier(self) -> str:
        token = self._peek()
        if token is None or token.kind != "identifier":
            found = "end of input" if token is None else token.value
            raise ValueError(f"expected identifier but found {found!r}")
        self.index += 1
        return token.value.lower()

    def _consume_keyword(self, value: str) -> None:
        token = self._peek()
        if token is None or token.kind != "keyword" or token.value != value:
            found = "end of input" if token is None else token.value
            raise ValueError(f"expected keyword {value!r} but found {found!r}")
        self.index += 1

    def _consume_keyword_value(self) -> str:
        token = self._peek()
        if token is None or token.kind != "keyword":
            found = "end of input" if token is None else token.value
            raise ValueError(f"expected keyword but found {found!r}")
        self.index += 1
        return token.value

    def _consume_symbol(self, value: str) -> None:
        token = self._peek()
        if token is None or token.kind != "symbol" or token.value != value:
            found = "end of input" if token is None else token.value
            raise ValueError(f"expected symbol {value!r} but found {found!r}")
        self.index += 1

    def _consume_optional_symbol(self, value: str) -> bool:
        token = self._peek()
        if token is None or token.kind != "symbol" or token.value != value:
            return False
        self.index += 1
        return True

    def _consume_symbol_value(self) -> str:
        token = self._peek()
        if token is None or token.kind != "symbol":
            found = "end of input" if token is None else token.value
            raise ValueError(f"expected symbol but found {found!r}")
        self.index += 1
        return token.value

    def _current_symbol(self) -> str | None:
        token = self._peek()
        if token is None or token.kind != "symbol":
            return None
        return token.value

    def _match_keyword(self, value: str) -> bool:
        token = self._peek()
        return token is not None and token.kind == "keyword" and token.value == value

    def _match_keyword_at(self, offset: int, value: str) -> bool:
        token = self._peek(offset)
        return token is not None and token.kind == "keyword" and token.value == value

    def _match_qualified_star(self) -> bool:
        return (
            self._peek() is not None
            and self._peek().kind == "identifier"
            and self._peek(1) is not None
            and self._peek(1).kind == "symbol"
            and self._peek(1).value == "."
            and self._peek(2) is not None
            and self._peek(2).kind == "symbol"
            and self._peek(2).value == "*"
        )

    def _peek(self, offset: int = 0) -> Token | None:
        position = self.index + offset
        if position >= len(self.tokens):
            return None
        return self.tokens[position]
