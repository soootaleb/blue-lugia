from typing import Type

from pydantic import BaseModel
from pydantic._internal._model_construction import ModelMetaclass

from playground.manager import TableManager
from playground.types import ModelType


class ModelMeta(ModelMetaclass):
    @property
    def objects(self: Type[ModelType]) -> "TableManager[ModelType]":
        return TableManager[ModelType](self)


class Model(BaseModel, metaclass=ModelMeta):
    pass
