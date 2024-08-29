from pprint import pprint
from typing import Any, List, Tuple

from blue_lugia.enums import Op
from blue_lugia.errors import QError


class Q:
    """
    A class to construct complex queries with conditions and logical operators.

    This class allows for the chaining of query conditions using AND, OR, and NOT operators
    using a Django-like interface for constructing query expressions. Conditions can be
    composed of simple key-value pairs or nested Q objects.

    Attributes:
        _conditions (List[Tuple[str, str, Any] | "Q"]): A list of conditions and/or nested Q objects.
        _connector (Op): The logical operator that connects conditions (AND, OR).
        _negated (bool): Flag indicating if the query expression is negated.

    Args:
        *args (Q): Positional Q objects, which are merged with the current instance based on logical rules.
        **kwargs (Any): Keyword arguments representing conditions in the form of key-value pairs where
            keys can include an operation as a suffix (e.g., 'field__gt' for 'greater than').

    Examples:
        Q(age__gt=30)
        Q(name__startswith='J', age__lt=50) & ~Q(status='inactive')
    """

    _conditions: List[Tuple[str, str, Any] | "Q"]
    _connector: Op
    _negated: bool

    _select: List[str] | None = None
    _from: str | None = None
    _limit: int | None = None
    _offset: int | None = None
    _group_by: List[str] | None = None

    def __init__(self, *args: "Q", **kwargs: Any) -> None:
        """
        Initializes a new Q object with optional nested Q objects and keyword conditions.

        All arguments are optional and can be mixed to represent more complex query logic.
        """
        self._conditions = []

        self._connector: Op = Op.AND

        for arg in args:
            if isinstance(arg, Q):
                if arg.connector == self.connector and not arg.negated:
                    self._conditions.extend(arg.conditions)
                else:
                    self._conditions.append(arg)

        self._conditions.extend(self._kwargs_to_kov(**kwargs))

        self._negated: bool = False

        self._select = None
        self._from = None
        self._limit = None
        self._offset = None
        self._group_by = None
        self._order_by = None

        if len(self._conditions) == 1 and isinstance(self._conditions[0], Q):
            sub_condition = self._conditions[0]
            self._conditions = sub_condition.conditions
            self._connector = sub_condition.connector
            self._negated = sub_condition.negated

    @property
    def conditions(self) -> List[Tuple[str, str, Any] | "Q"]:
        return self._conditions

    @property
    def connector(self) -> Op:
        return self._connector

    @property
    def negated(self) -> bool:
        return self._negated

    def _kwargs_to_kov(self, **kwargs: dict[str, Any]) -> List[Tuple[str, str, Any]]:
        kov = []

        for key, value in kwargs.items():
            if "__" in key:
                splited = key.split("__")
                if len(splited) == 2:
                    key, operation = splited[0], splited[1]
                else:
                    key, operation = "__".join(splited[:-1]), splited[-1]
            else:
                key, operation = key, "equals"

            kov.append((key, operation, value))

        return kov

    def __or__(self, other: "Q") -> "Q":
        """
        Returns a new Q object representing the logical OR between this and another Q object.

        Args:
            other (Q): Another Q object to combine with this one using the OR operator.

        Returns:
            Q: A new Q object that combines the conditions of both Q objects using the OR logical operator.
        """
        return self._combine(other, Op.OR)

    def __and__(self, other: "Q") -> "Q":
        """
        Returns a new Q object representing the logical AND between this and another Q object.

        Args:
            other (Q): Another Q object to combine with this one using the AND operator.

        Returns:
            Q: A new Q object that combines the conditions of both Q objects using the AND logical operator.
        """
        return self._combine(other, Op.AND)

    def __invert__(self) -> "Q":
        """
        Returns a new Q object representing the logical negation of this Q object.

        Returns:
            Q: A new Q object that is the logical negation of this one.
        """
        query = Q()
        query._conditions = self._conditions
        query._connector = self._connector
        query._negated = not self._negated
        return query

    def _combine(self, other: "Q", connector: Op) -> "Q":
        query = Q()
        query._connector = connector

        # Handle self conditions, respecting negation
        if self._connector == connector:
            if self._negated:
                self_wrapped = Q()
                self_wrapped._conditions = self._conditions
                self_wrapped._connector = self._connector
                self_wrapped._negated = True
                query._conditions.append(self_wrapped)
            else:
                query._conditions.extend(self._conditions)
        else:
            self_wrapped = Q()
            self_wrapped._conditions = self._conditions
            self_wrapped._connector = self._connector
            self_wrapped._negated = self._negated
            query._conditions.append(self_wrapped)

        # Handle other conditions, respecting negation
        if other._connector == connector:
            if other._negated:
                other_wrapped = Q()
                other_wrapped._conditions = other._conditions
                other_wrapped._connector = other._connector
                other_wrapped._negated = True
                query._conditions.append(other_wrapped)
            else:
                query._conditions.extend(other._conditions)
        else:
            other_wrapped = Q()
            other_wrapped._conditions = other._conditions
            other_wrapped._connector = other._connector
            other_wrapped._negated = other._negated
            query._conditions.append(other_wrapped)

        return query

    def __repr__(self) -> str:
        op = "NOT " + self._connector.value if self._negated else self._connector.value
        return f"<{op}: {self._conditions}>"

    def as_dict(self) -> dict[str, Any]:
        if len(self._conditions) == 1:
            return {
                "NOT" if self._negated else self._connector.value: self._conditions[0].as_dict() if isinstance(self._conditions[0], Q) else self._conditions[0],
            }
        else:
            return {
                "NOT" if self._negated else self._connector.value: [c.as_dict() if isinstance(c, Q) else c for c in self._conditions],
            }

    def pprint(self) -> None:
        """
        Pretty prints the dictionary representation of the Q object to provide a more readable output.
        Useful for debugging and visualizing the structure of complex Q objects.
        """
        pprint(self.as_dict(), width=1)

    def _evaluate_eq(self, data: dict[str, Any], key: str, value: Any) -> bool:
        return data.get(key) == value

    def _evaluate_equals(self, data: dict[str, Any], key: str, value: Any) -> bool:
        return data.get(key) == value

    def _evaluate_ne(self, data: dict[str, Any], key: str, value: Any) -> bool:
        return data.get(key) != value

    def _evaluate_not_equals(self, data: dict[str, Any], key: str, value: Any) -> bool:
        return data.get(key) != value

    def _evaluate_gt(self, data: dict[str, Any], key: str, value: Any) -> bool:
        return data.get(key) > value

    def _evaluate_gte(self, data: dict[str, Any], key: str, value: Any) -> bool:
        return data.get(key) >= value

    def _evaluate_lt(self, data: dict[str, Any], key: str, value: Any) -> bool:
        return data.get(key) < value

    def _evaluate_lte(self, data: dict[str, Any], key: str, value: Any) -> bool:
        return data.get(key) <= value

    def _evaluate_contains(self, data: dict[str, Any], key: str, value: Any) -> bool:
        return value in data.get(key)

    def _evaluate_not_contains(self, data: dict[str, Any], key: str, value: Any) -> bool:
        return value not in data.get(key)

    def _evaluate_startswith(self, data: dict[str, Any], key: str, value: Any) -> bool:
        found = data.get(key)
        return found.startswith(value) if isinstance(found, str) else False

    def _evaluate_endswith(self, data: dict[str, Any], key: str, value: Any) -> bool:
        found = data.get(key)
        return found.endswith(value) if isinstance(found, str) else False

    def _evaluate_in(self, data: dict[str, Any], key: str, value: Any) -> bool:
        return data.get(key) in value

    def _evaluate(self, data: dict[str, Any]) -> bool:  # noqa: C901
        if self._connector == Op.AND:
            for condition in self._conditions:
                if isinstance(condition, Q):
                    if not condition.evaluate(data):
                        return False
                else:
                    key, operation, value = condition
                    if not getattr(self, f"_evaluate_{operation}")(data, key, value):
                        return False
            return True
        elif self._connector == Op.OR:
            for condition in self._conditions:
                if isinstance(condition, Q):
                    if condition.evaluate(data):
                        return True
                else:
                    key, operation, value = condition
                    if getattr(self, f"_evaluate_{operation}")(data, key, value):
                        return True
            return (not len(self._conditions)) and (not self._negated)  # return True if not conditions evaled to True because there are no conditions
        else:
            for condition in self._conditions:
                if isinstance(condition, Q):
                    if condition.evaluate(data):
                        return False
                else:
                    key, operation, value = condition
                    if getattr(self, f"_evaluate_{operation}")(data, key, value):
                        return False
            return False  # Op.NOT should return False if there are no conditions

    def evaluate(self, data: dict[str, Any]) -> bool:
        if self._negated:
            return not self._evaluate(data)
        else:
            return self._evaluate(data)

    def select(self, *args: str) -> "Q":
        self._select = list(args)
        return self

    def from_(self, table: str) -> "Q":
        self._from = table
        return self

    def limit(self, limit: int) -> "Q":
        self._limit = limit
        return self

    def offset(self, offset: int) -> "Q":
        self._offset = offset
        return self

    def group_by(self, *args: str) -> "Q":
        self._group_by = list(args)
        return self

    def order_by(self, *args: str) -> "Q":
        self._order_by = list(args)
        return self

    @property
    def where(self) -> Tuple[str, List]:  # noqa: C901
        conditions = []
        parameters = []
        for condition in self._conditions:
            if isinstance(condition, Q):
                nested_where, nested_params = condition.where
                if condition.negated:
                    nested_where = f"NOT ({nested_where})"
                conditions.append(nested_where)
                parameters.extend(nested_params)
            else:
                key, operation, value = condition
                if operation == "equals":
                    conditions.append(f"{key} = ?")
                    parameters.append(value)
                elif operation == "not_equals":
                    conditions.append(f"{key} != ?")
                    parameters.append(value)
                elif operation == "gt":
                    conditions.append(f"{key} > ?")
                    parameters.append(value)
                elif operation == "gte":
                    conditions.append(f"{key} >= ?")
                    parameters.append(value)
                elif operation == "lt":
                    conditions.append(f"{key} < ?")
                    parameters.append(value)
                elif operation == "lte":
                    conditions.append(f"{key} <= ?")
                    parameters.append(value)
                elif operation == "contains":
                    conditions.append(f"{key} LIKE ?")
                    parameters.append(f"%{value}%")
                elif operation == "not_contains":
                    conditions.append(f"{key} NOT LIKE ?")
                    parameters.append(f"%{value}%")
                elif operation == "startswith":
                    conditions.append(f"{key} LIKE ?")
                    parameters.append(f"{value}%")
                elif operation == "endswith":
                    conditions.append(f"{key} LIKE ?")
                    parameters.append(f"%{value}")
                elif operation == "in":
                    placeholders = ", ".join(["?"] * len(value))
                    conditions.append(f"{key} IN ({placeholders})")
                    parameters.extend(value)
                else:
                    conditions.append(f"{key} = ?")  # default to equals if operation is unrecognized
                    parameters.append(value)

        where_clause = f"{' AND '.join(conditions)}" if self._connector == Op.AND else f"{' OR '.join(conditions)}"

        if self._negated and len(conditions) == 1:
            where_clause = f"NOT ({where_clause})"

        return where_clause, parameters

    def sql(self) -> Tuple[str, List]:
        select = ", ".join(self._select) if self._select else "*"

        if not self._from:
            raise QError("BL::Q::sql: Missing table name in FROM clause")

        sql = f"SELECT {select} FROM {self._from}"

        where, params = self.where

        if where:
            sql += f" WHERE {where}"

        if self._group_by:
            sql += f" GROUP BY {', '.join(self._group_by)}"

        if self._order_by:
            orders = []
            for order in self._order_by:
                if order.startswith("-"):
                    orders.append(f"{order[1:]} DESC")
                else:
                    orders.append(order)
            sql += f" ORDER BY {', '.join(orders)}"

        if self._limit:
            sql += f" LIMIT {self._limit}"

        if self._offset:
            sql += f" OFFSET {self._offset}"

        return sql, params
