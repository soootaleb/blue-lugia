from typing import Callable, ClassVar, Generic, List, Type, TypeVar

from pydantic import BaseModel
from pydantic._internal._model_construction import ModelMetaclass

from blue_lugia.models.query import Q

DATA = {
    "name": [
        "Alice",
        "Bob",
        "Charlie",
        "David",
        "Eve",
        "Frank",
        "Grace",
        "Hannah",
        "Ivan",
        "Jack",
        "Kate",
        "Leo",
        "Mia",
        "Nina",
        "Oscar",
        "Paul",
        "Quincy",
        "Rita",
        "Steve",
        "Tracy",
    ],
    "age": [25, 30, 35, 28, 22, 31, 27, 29, 24, 33, 26, 32, 28, 30, 34, 36, 27, 31, 29, 23],
    "city": [
        "Paris",
        "London",
        "New York",
        "Berlin",
        "Madrid",
        "Tokyo",
        "Sydney",
        "Moscow",
        "Toronto",
        "Dubai",
        "Rome",
        "Beijing",
        "Paris",
        "London",
        "New York",
        "Berlin",
        "Madrid",
        "Tokyo",
        "Sydney",
        "Moscow",
    ],
    "salary": [50000, 60000, 70000, 48000, 52000, 75000, 47000, 62000, 53000, 68000, 54000, 71000, 56000, 59000, 72000, 67000, 50000, 66000, 63000, 52000],
    "department": [
        "HR",
        "Finance",
        "IT",
        "Marketing",
        "HR",
        "IT",
        "Marketing",
        "Finance",
        "IT",
        "HR",
        "Finance",
        "Marketing",
        "HR",
        "IT",
        "Finance",
        "Marketing",
        "HR",
        "IT",
        "Finance",
        "Marketing",
    ],
    "years_experience": [2, 5, 8, 3, 1, 9, 4, 6, 2, 7, 3, 10, 2, 5, 8, 4, 2, 9, 6, 1],
    "performance_score": [3.2, 4.5, 4.8, 3.6, 2.9, 5.0, 3.7, 4.4, 3.0, 4.1, 3.5, 4.9, 3.3, 4.6, 4.7, 3.8, 3.1, 4.3, 4.0, 2.8],
}

DATA_LIST = [{k: v[i] for k, v in DATA.items()} for i in range(len(DATA["name"]))]


"""

We want a table, a two dimension array of data
Tables can be a SQL table, an Excel sheet, etc... DataFrame seems a cool base class

Tables must have

- [OK] a structure definition => PYDANTIC MODELS
  - fields names
  - fields types
  - (opt) fields descriptions
  - (opt) fields defaults

- a way to be hydrated => MANAGERS API ?
  - from an excel sheet to a table instance
  - from an SQL table to a table instance
  - from a list of dictionaries to a table instance
  - ...

- [OK] a way to be queried => MANAGERS API
  - Q api
  - ...? Pandas api?
"""

Model = TypeVar("Model", bound=BaseModel)


class QuerySet(Generic[Model], List[Model]):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def filter(self, f: Callable[[Model], bool]) -> "QuerySet[Model]":
        return QuerySet(filter(f, self))

    def first(self, f: Callable[[Model], bool] | None = None) -> Model:
        if f:
            return next(filter(f, self))
        elif self:
            return self[0]
        else:
            raise ValueError("BL::Model::QuerySet::first::Empty QuerySet")


# class ManagerMetaClass(type):
#     def __new__(cls, name: str, bases: tuple, attrs: dict) -> "ManagerMetaClass":
#         manager = attrs.get("manager")
#         if manager is not None:
#             manager = manager.__class_getitem__(manager)
#             attrs["manager"] = manager
#         return super().__new__(cls, name, bases, attrs)


class TableManager(Generic[Model]):
    model: Type[Model]

    def __init__(self, model: Type[Model] = BaseModel) -> None:
        self.model = model

    def all(self) -> QuerySet[Model]:
        return QuerySet([self.model(**item) for item in DATA_LIST])

    def filter(self, *args, **kwargs) -> QuerySet[Model]:
        query = Q(*args, **kwargs)

        return self.all().filter(lambda item: query.evaluate(item.model_dump()))


TableManagerType = TypeVar("TableManagerType", bound=TableManager)


class TableMeta(ModelMetaclass):
    @property
    def objects(self: Type[Model]) -> "TableManager[Model]":
        return TableManager[Model](self)


class Table(BaseModel, metaclass=TableMeta):
    pass


TableType = TypeVar("TableType", bound=Table)
