from typing import Any


class Q:
    AND = "AND"
    OR = "OR"
    NOT = "NOT"

    query: dict[str, Any] | tuple

    def __init__(self, q: "Q | None" = None, **kwargs) -> None:
        self.query = kwargs
        self.connector = self.AND
        self.negated = False

    def __or__(self, other: "Q") -> "Q":
        return self._combine(other, self.OR)

    def __and__(self, other: "Q") -> "Q":
        return self._combine(other, self.AND)

    def __invert__(self) -> "Q":
        if isinstance(self.query, dict):
            new_q = Q(**self.query)
            new_q.connector = self.connector
            new_q.negated = not self.negated
        else:
            new_q = Q(**{**self.query[0], **self.query[1]})
            new_q.connector = self.connector
            new_q.negated = not self.negated
        return new_q

    def _combine(self, other: "Q", connector: str) -> "Q":
        combined_q = Q()
        combined_q.query = (self, other)
        combined_q.connector = connector
        return combined_q

    def evaluate(self, data: dict) -> bool:
        if isinstance(self.query, dict):
            result = all(data.get(key) == value for key, value in self.query.items())
            return not result if self.negated else result
        elif isinstance(self.query, tuple):
            q1, q2 = self.query
            if self.connector == self.AND:
                return q1.evaluate(data) and q2.evaluate(data)
            elif self.connector == self.OR:
                return q1.evaluate(data) or q2.evaluate(data)
        return False

    def as_dict(self) -> dict:
        if isinstance(self.query, dict):
            query_dict = {"NOT": self.query} if self.negated else self.query
            return query_dict
        elif isinstance(self.query, tuple):
            q1, q2 = self.query
            q1_dict = q1.as_dict()
            q2_dict = q2.as_dict()
            combined_dict = {self.connector: [q1_dict, q2_dict]}
            return {"NOT": combined_dict} if self.negated else combined_dict
        return {}

    def __str__(self) -> str:
        if isinstance(self.query, dict):
            return f"{'NOT ' if self.negated else ''}{self.query}"
        elif isinstance(self.query, tuple):
            q1, q2 = self.query
            return f"({q1} {self.connector} {q2})"
        return ""
