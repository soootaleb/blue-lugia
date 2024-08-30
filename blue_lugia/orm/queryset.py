from typing import Callable, Generic, List

import pandas as pd

from blue_lugia.models import Q
from blue_lugia.orm.types import ModelType


class QuerySet(Generic[ModelType], List[ModelType]):
    @property
    def dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([item.model_dump() for item in self])

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def filter(self, *args, **kwargs) -> "QuerySet[ModelType]":
        f = args[0] if len(args) == 1 and isinstance(args[0], Callable) else Q(*args, **kwargs)
        return QuerySet(filter(f, self))

    def first(self, f: Callable[[ModelType], bool] | None = None) -> ModelType:
        if f:
            return next(filter(f, self))
        elif self:
            return self[0]
        else:
            raise ValueError("BL::Model::QuerySet::first::Empty QuerySet")

    def count(self, f: Callable[[ModelType], bool] | None = None) -> int:
        if f:
            return sum(1 for item in self if f(item))
        else:
            return len(self)
