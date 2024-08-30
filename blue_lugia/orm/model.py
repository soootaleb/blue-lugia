import datetime
import types
from typing import Any, List, Optional, Type

import pandas as pd
from pydantic import BaseModel, Field
from pydantic._internal._model_construction import ModelMetaclass

from blue_lugia.orm.driver import DataDriver
from blue_lugia.orm.manager import ModelManager
from blue_lugia.orm.source import DataSource
from blue_lugia.orm.types import ModelType


class ModelMeta(ModelMetaclass):
    _source = DataSource()
    _driver = DataDriver()

    @property
    def objects(self: Type[ModelType]) -> "ModelManager[ModelType]":
        model_meta = getattr(self, "Meta", None)
        table = (model_meta.table if hasattr(model_meta, "table") else self.__name__) if model_meta else self.__name__
        return ModelManager[self](self, source=self._source, driver=self._driver, table=table)  # type: ignore

    @classmethod
    def sourced(cls: "Type[ModelMeta]", source: DataSource) -> "Type[ModelMeta]":
        # sourced_meta = type(f"{cls.__name__}::{source.__class__.__name__}", (cls,), {})
        sourced_meta = type(cls.__name__, (cls,), {})
        sourced_meta._source = source
        return sourced_meta

    @classmethod
    def driven(cls: "Type[ModelMeta]", driver: DataDriver) -> "Type[ModelMeta]":
        # driven_meta = type(f"{cls.__name__}::{driver.__class__.__name__}", (cls,), {})
        driven_meta = type(cls.__name__, (cls,), {})
        driven_meta._driver = driver
        return driven_meta


class Model(BaseModel, metaclass=ModelMeta):
    @property
    def dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.model_dump())

    @classmethod
    def sourced(cls: Type[ModelType], source: DataSource) -> Type[ModelType]:
        sourced_meta = cls.__class__.sourced(source)  # type: ignore
        # return types.new_class(f"{cls.__name__}::{sourced_meta.__name__}", (cls,), {"metaclass": sourced_meta})
        return types.new_class(cls.__name__, (cls,), {"metaclass": sourced_meta})

    @classmethod
    def driven(cls: Type[ModelType], driver: DataDriver) -> Type[ModelType]:
        driven_meta = cls.__class__.driven(driver)  # type: ignore
        # return types.new_class(f"{cls.__name__}::{driven_meta.__name__}", (cls,), {"metaclass": driven_meta})
        return types.new_class(cls.__name__, (cls,), {"metaclass": driven_meta})


class Chunk(Model):
    id: str = Field(...)
    order: int = Field(...)
    content: str = Field(...)
    start_page: Optional[int] = Field(...)
    end_page: Optional[int] = Field(...)
    created_at: datetime.datetime = Field(...)
    updated_at: datetime.datetime = Field(...)
    metadata: dict[str, Any] = Field(...)
    url: Optional[str] = Field(...)


class File(Model):
    id: str = Field(...)
    key: str = Field(...)
    name: str = Field(...)
    chunks: List[Chunk] = Field(...)
    mime_type: str = Field(...)
    write_url: str = Field(...)
    created_at: datetime.datetime = Field(...)
    updated_at: datetime.datetime = Field(...)


class Remote(Model):  # noqa: N801
    id: str = Field(...)
    debug: dict = Field(...)


class ToolCallFunction(Model):  # noqa: N801
    name: str = Field(...)
    arguments: dict = Field(...)


class ToolCall(Model):  # noqa: N801
    id: str = Field(...)
    type: str = Field(...)
    function: ToolCallFunction


class Message(Model):
    role: str = Field(...)
    content: str = Field(...)
    original_content: str = Field(...)
    tool_calls: Optional[List[ToolCall]] = Field([])
    tool_call_id: Optional[str] = Field(None)
    remote: Optional[Remote] = Field(None)
