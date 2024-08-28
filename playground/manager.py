from typing import Callable, Generic, Type

import pandas as pd
from pydantic import BaseModel

from blue_lugia.models.query import Q
from playground.driver import DataDriver
from playground.queryset import QuerySet
from playground.source import DataSource
from playground.types import ModelType


class ModelManager(Generic[ModelType]):
    _model: Type[ModelType]
    _datasource: DataSource
    _datadriver: DataDriver

    def __init__(self, model: Type[ModelType] = BaseModel, source: DataSource = DataSource(), driver: DataDriver = DataDriver()) -> None:
        self._model = model
        self._datasource = source
        self._datadriver = driver

    @property
    def model(self) -> Type[ModelType]:
        return self._model

    @property
    def dataframe(self) -> pd.DataFrame:
        return self.all().dataframe

    def all(self) -> QuerySet[ModelType]:
        self._datasource.open()
        raw_data = self._datasource.read()
        self._datasource.close()
        parsed_data = self._datadriver.decode(raw_data)

        if isinstance(parsed_data, dict):
            return QuerySet([self.model(**parsed_data)])
        elif isinstance(parsed_data, list):
            return QuerySet([self.model(**item) for item in parsed_data])
        else:
            raise ValueError("BL::ModelManager::all:Invalid data type")

    def filter(self, *args, **kwargs) -> QuerySet[ModelType]:
        query = Q(*args, **kwargs)

        return self.all().filter(lambda item: query.evaluate(item.model_dump()))

    def create(self, item: ModelType) -> None:
        raise NotImplementedError

    def count(self, f: Callable[[ModelType], bool] | None = None) -> int:
        return self.all().count(f)

    def first(self, f: Callable[[ModelType], bool] | None = None) -> ModelType:
        return self.all().first(f)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.model.__name__}>"
