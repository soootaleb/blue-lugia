from typing import Any, Type

import pandas as pd
from pydantic import Field

from blue_lugia.enums import Op
from playground.core import DATA_LIST, Model, Q, QuerySet, Table, TableManager, TableMeta, TableType


class People(Table):
    name: str = Field(...)
    age: int = Field(...)
    city: str = Field(...)
    salary: int = Field(...)
    department: str = Field(...)
    years_experience: int = Field(...)
    performance_score: float = Field(...)


class DataFrameTableManager(TableManager[Model]):
    _dataframe: pd.DataFrame | None = None

    @property
    def dataframe(self) -> pd.DataFrame:
        if self._dataframe is None:
            self._dataframe = pd.DataFrame(DATA_LIST)
        return self._dataframe

    @property
    def columns(self) -> pd.Index:
        return self.dataframe.columns

    def _q_to_dataframe_filter(self, q: Q) -> pd.Series:
        """
        Translates a Q object into a DataFrame filter.

        Args:
            q (Q): The Q object containing the conditions.
            df (pd.DataFrame): The DataFrame to apply the filter on.

        Returns:
            pd.Series: A boolean Series representing the filter.
        """
        if q.connector == Op.AND:
            filter_series = pd.Series([True] * len(self.dataframe))
            for condition in q.conditions:
                if isinstance(condition, Q):
                    filter_series &= self._q_to_dataframe_filter(condition)
                else:
                    key, operation, value = condition
                    filter_series &= self._apply_condition(key, operation, value)
        elif q.connector == Op.OR:
            filter_series = pd.Series([False] * len(self.dataframe))
            for condition in q.conditions:
                if isinstance(condition, Q):
                    filter_series |= self._q_to_dataframe_filter(condition)
                else:
                    key, operation, value = condition
                    filter_series |= self._apply_condition(key, operation, value)
        elif q.connector == Op.NOT:
            filter_series = pd.Series([True] * len(self.dataframe))
            for condition in q.conditions:
                if isinstance(condition, Q):
                    filter_series &= ~self._q_to_dataframe_filter(condition)
                else:
                    key, operation, value = condition
                    filter_series &= ~self._apply_condition(key, operation, value)
        else:
            raise ValueError(f"Unsupported connector: {q.connector}")

        return filter_series

    def _apply_condition(self, key: str, operation: str, value: Any) -> pd.Series:  # noqa: C901
        """
        Applies a single condition to the DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame to apply the condition on.
            key (str): The column name.
            operation (str): The operation to apply.
            value (Any): The value to compare against.

        Returns:
            pd.Series: A boolean Series representing the condition.
        """

        if operation == "equals" or operation == "eq":
            return self.dataframe[key] == value
        elif operation == "notEquals" or operation == "ne":
            return self.dataframe[key] != value
        elif operation == "greaterThan" or operation == "gt":
            return self.dataframe[key] > value
        elif operation == "greaterThanOrEqual" or operation == "gte":
            return self.dataframe[key] >= value
        elif operation == "lessThan" or operation == "lt":
            return self.dataframe[key] < value
        elif operation == "lessThanOrEqual" or operation == "lte":
            return self.dataframe[key] <= value
        elif operation == "contains":
            return self.dataframe[key].str.contains(value)
        elif operation == "notContains":
            return ~self.dataframe[key].str.contains(value)
        elif operation == "startsWith":
            return self.dataframe[key].str.startswith(value)
        elif operation == "endsWith":
            return self.dataframe[key].str.endswith(value)
        elif operation == "in":
            return self.dataframe[key].isin(value)
        else:
            raise ValueError(f"Unsupported operation: {operation}")

    def all(self) -> pd.DataFrame:
        return self.dataframe

    def filter(self, *args, **kwargs) -> pd.DataFrame:
        df_filter = self._q_to_dataframe_filter(Q(*args, **kwargs))
        return self.dataframe[df_filter]


class DataFrameTable(TableMeta):
    @property
    def objects(self: "Type[TableType]") -> DataFrameTableManager[TableType]:
        return DataFrameTableManager[TableType](self)


class PeopleDataFrame(People, metaclass=DataFrameTable):
    pass


complex_query = Q(department__in=["IT", "Finance"]) & Q(salary__gt=60000) & (Q(years_experience__gt=5) | Q(performance_score__gt=4.5))
person = People.objects.filter(complex_query).first()

print(person.model_dump())
print(PeopleDataFrame.objects.dataframe.tail())


pass
