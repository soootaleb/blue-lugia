from re import S
from typing import List

from pydantic import Field

from blue_lugia.models.query import Q
from blue_lugia.orm.driver import JSONDriver
from blue_lugia.orm.model import Model
from blue_lugia.orm.source import FileDataSource, SQLDataSource


class Person(Model):
    name: str = Field(...)
    age: int = Field(...)
    city: str = Field(...)
    salary: int = Field(...)
    department: str = Field(...)
    years_experience: int = Field(...)
    performance_score: float = Field(...)


PersonDB = Person.sourced(FileDataSource("db.json")).driven(JSONDriver())

SQLDB = Person.sourced(SQLDataSource(db_path="playground.db"))

query = Q(department__in=["IT", "Finance"]) & Q(salary__gt=60000) & (Q(years_experience__gt=5) | Q(performance_score__gt=4.5))

people_to_export = PersonDB.objects.filter(query)

SQLDB.objects.bulk_create(people_to_export)

# ================= Query Language ====================
query = Q(department__in=["IT", "Finance"]) & Q(salary__gt=60000) & (Q(years_experience__gt=5) | Q(performance_score__gt=4.5))

# ================= Query API ====================
people = Person.objects.filter(query)
person = people.first()

print("All people count")
print(Person.objects.count())

print("First person with salary > 60000 and department in IT or Finance:")
print(person.model_dump())

print("Tail people with salary > 60000 and department in IT or Finance:")
print(people.dataframe.tail())

# ================= CRUD API ====================
Me = Person(name="Me", age=25, city="Paris", salary=100000, department="IT", years_experience=10, performance_score=5.0)
Person.objects.create(Me)

print("All people count")
print(Person.objects.count())
