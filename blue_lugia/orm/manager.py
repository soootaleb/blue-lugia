from typing import Any, Callable, Generic, List, Type

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

        self._datasource.metadata.update({"model_name": model.__name__})

        self._table = table or model.__name__

        if hasattr(model, "Config"):
            model_config = getattr(model, "Config", None)
            self._table = getattr(model_config, "table") or self._table

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

        if isinstance(parsed_data, dict) and self._table in parsed_data:
            parsed_data = parsed_data[self._table]

        if isinstance(parsed_data, dict):
            return QuerySet([self.model(**parsed_data)])
        elif isinstance(parsed_data, QuerySet):
            return parsed_data
        elif isinstance(parsed_data, list):
            items_as_dict = []
            for i in parsed_data:
                if isinstance(i, dict):
                    items_as_dict.append(i)
                elif hasattr(i, "as_dict"):
                    items_as_dict.append(i.as_dict())
                elif isinstance(i, BaseModel):
                    items_as_dict.append(i.model_dump())
                else:
                    items_as_dict.append(dict(i))
            return QuerySet([self.model(**item) for item in items_as_dict])
        elif not bool(parsed_data):
            return QuerySet()
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

    def limit(self, limit: int) -> "ModelManager[ModelType]":
        self._query = self.query.limit(limit)
        return self

    def offset(self, offset: int) -> "ModelManager[ModelType]":
        self._query = self.query.offset(offset)
        return self

    def order_by(self, *args) -> "ModelManager[ModelType]":
        self._query = self.query.order_by(*args)
        return self

    def group_by(self, *args) -> "ModelManager[ModelType]":
        self._query = self.query.group_by(*args)
        return self

    def from_(self, table: str) -> "ModelManager[ModelType]":
        self._query = self.query.from_(table)
        return self

    def values(self, *args, **kwargs) -> List[dict[str, Any]]:
        flat = kwargs.pop("flat", False)

        self._query.select(*args)

        if flat and len(args) > 1:
            raise ValueError("BL::ModelManager::values:Cannot use flat=True with multiple fields")
        elif flat and len(args) == 1:
            try:
                return QuerySet([item.model_dump().get(args[0]) for item in self.all()])
            except KeyError:
                raise ValueError(f"BL::ModelManager::values:Field {args[0]} not found in model {self.model.__name__}")
        else:
            return QuerySet([item.model_dump(include=set(args)) for item in self.all()])

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.model.__name__}>"
