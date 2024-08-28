import types
from typing import Type

import pandas as pd
from pydantic import BaseModel
from pydantic._internal._model_construction import ModelMetaclass

from playground.driver import DataDriver
from playground.manager import ModelManager
from playground.source import DataSource
from playground.types import ModelType


class ModelMeta(ModelMetaclass):
    _source = DataSource()
    _driver = DataDriver()

    @property
    def objects(self: Type[ModelType]) -> "ModelManager[ModelType]":
        return ModelManager[self](self, source=self._source, driver=self._driver)  # type: ignore

    @classmethod
    def sourced(cls: "Type[ModelMeta]", source: DataSource) -> "Type[ModelMeta]":
        sourced_meta = type(f"{cls.__name__}::{source.__class__.__name__}", (cls,), {})
        sourced_meta._source = source
        return sourced_meta

    @classmethod
    def driven(cls: "Type[ModelMeta]", driver: DataDriver) -> "Type[ModelMeta]":
        driven_meta = type(f"{cls.__name__}::{driver.__class__.__name__}", (cls,), {})
        driven_meta._driver = driver
        return driven_meta


class Model(BaseModel, metaclass=ModelMeta):
    @property
    def dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.model_dump())

    @classmethod
    def sourced(cls: Type[ModelType], source: DataSource) -> Type[ModelType]:
        sourced_meta = cls.__class__.sourced(source)  # type: ignore
        return types.new_class(f"{cls.__name__}::{sourced_meta.__name__}", (cls,), {"metaclass": sourced_meta})

    @classmethod
    def driven(cls: Type[ModelType], driver: DataDriver) -> Type[ModelType]:
        driven_meta = cls.__class__.driven(driver)  # type: ignore
        return types.new_class(f"{cls.__name__}::{driven_meta.__name__}", (cls,), {"metaclass": driven_meta})
