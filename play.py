from typing import List

from pydantic import Field

from blue_lugia.models.query import Q
from playground.driver import JSONDriver
from playground.model import Model
from playground.source import FileDataSource


class Person(Model):
    name: str = Field(...)
    age: int = Field(...)
    city: str = Field(...)
    salary: int = Field(...)
    department: str = Field(...)
    years_experience: int = Field(...)
    performance_score: float = Field(...)


class People(Model):
    name: List[str] = Field(...)
    age: List[int] = Field(...)
    city: List[str] = Field(...)
    salary: List[int] = Field(...)
    department: List[str] = Field(...)
    years_experience: List[int] = Field(...)
    performance_score: List[float] = Field(...)


class Parents(Model):
    father: str = Field(...)
    mother: str = Field(...)


class Child(Model):
    name: str = Field(...)
    family: Parents = Field(...)


JSONChild = Child.sourced(FileDataSource("nested.json")).driven(JSONDriver())
children = JSONChild.objects.all()

children_df = children.dataframe

# ================= Query Language ====================
complex_query = Q(department__in=["IT", "Finance"]) & Q(salary__gt=60000) & (Q(years_experience__gt=5) | Q(performance_score__gt=4.5))

# ================= Query API ====================
people = Person.objects.filter(complex_query)
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
