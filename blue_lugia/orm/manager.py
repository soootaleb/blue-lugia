from typing import Callable, Generic, Type

import pandas as pd
from pydantic import BaseModel

from blue_lugia.models.query import Q
from blue_lugia.orm.driver import DataDriver
from blue_lugia.orm.queryset import QuerySet
from blue_lugia.orm.source import DataSource
from blue_lugia.orm.types import ModelType


class ModelManager(Generic[ModelType]):
    _model: Type[ModelType]
    _datasource: DataSource
    _datadriver: DataDriver
    _table: str

    _query: Q

    def __init__(self, model: Type[ModelType] = BaseModel, source: DataSource = DataSource(), driver: DataDriver = DataDriver(), table: str | None = None) -> None:
        self._model = model
        self._datasource = source
        self._datadriver = driver
        self._table = table or model.__name__
        self._query = Q().from_(self._table)

    @property
    def model(self) -> Type[ModelType]:
        return self._model

    @property
    def dataframe(self) -> pd.DataFrame:
        return self.all().dataframe

    @property
    def query(self) -> Q:
        return self._query

    def all(self) -> QuerySet[ModelType]:
        self._datasource.open()
        raw_data = self._datasource.read(self.query)
        self._datasource.close()
        parsed_data = self._datadriver.decode(raw_data)

        if isinstance(parsed_data, dict):
            return QuerySet([self.model(**parsed_data)])
        elif isinstance(parsed_data, list):
            return QuerySet([self.model(**item) for item in parsed_data])
        else:
            raise ValueError("BL::ModelManager::all:Invalid data type")

    def filter(self, *args, **kwargs) -> QuerySet[ModelType]:
        self._query = Q(*args, **kwargs)
        return self.all().filter(lambda item: self.query.evaluate(item.model_dump()))

    def create(self, item: ModelType) -> None:
        self._datasource.open()
        raw_data, params = self._datadriver.encode({"_table": self._table, "_item": item.model_dump()})
        self._datasource.write(data=raw_data, params=params)
        self._datasource.close()

    def count(self, f: Callable[[ModelType], bool] | None = None) -> int:
        return self.all().count(f)

    def first(self, f: Callable[[ModelType], bool] | None = None) -> ModelType:
        return self.all().first(f)

    def bulk_create(self, items: QuerySet[ModelType]) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.model.__name__}>"
