from pydantic import Field

from blue_lugia.models.query import Q
from blue_lugia.orm.driver import JSONDriver, SQLiteDriver
from blue_lugia.orm.model import Model
from blue_lugia.orm.source import FileDataSource, SQLiteDataSource


class Person(Model):
    name: str = Field(...)
    age: int = Field(...)
    city: str = Field(...)
    salary: int = Field(...)
    department: str = Field(...)
    years_experience: int = Field(...)
    performance_score: float = Field(...)


class Message(Model):

    class Meta:
        table = "playground"

    message: str = Field(...)


# PersonDB = Person.sourced(FileDataSource("db.ignore.json")).driven(JSONDriver())
# query = Q(department__in=["IT", "Finance"]) & Q(salary__gt=60000) & (Q(years_experience__gt=5) | Q(performance_score__gt=4.5))
# people_to_export = PersonDB.objects.filter(query)

Messages = Message.sourced(SQLiteDataSource(db_path="playground.ignore.db")).driven(SQLiteDriver())

Messages.objects.all()

Messages.objects.create(Message(message="Bye, World!"))

# SQLDB.objects.bulk_create(people_to_export)

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


class A:
    pass


class B(A):
    pass


def f(x: A):
    pass


f(B())
