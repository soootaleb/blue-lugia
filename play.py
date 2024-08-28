from playground.source import JSONFileDataSource

# # ================= Data Structure ====================
# class Person(Model):
#     name: str = Field(...)
#     age: int = Field(...)
#     city: str = Field(...)
#     salary: int = Field(...)
#     department: str = Field(...)
#     years_experience: int = Field(...)
#     performance_score: float = Field(...)


# # ================= Query Language ====================
# complex_query = Q(department__in=["IT", "Finance"]) & Q(salary__gt=60000) & (Q(years_experience__gt=5) | Q(performance_score__gt=4.5))

# # ================= Query API ====================
# people = Person.objects.filter(complex_query)
# person = people.first()

# print("All people count")
# print(Person.objects.count())

# print("First person with salary > 60000 and department in IT or Finance:")
# print(person.model_dump())

# print("Tail people with salary > 60000 and department in IT or Finance:")
# print(people.dataframe.tail())

# # ================= CRUD API ====================
# Me = Person(name="Me", age=25, city="Paris", salary=100000, department="IT", years_experience=10, performance_score=5.0)
# Person.objects.create(Me)

# print("All people count")
# print(Person.objects.count())

# pass


# data = InMemoryDataSource()
# data.open()
# data.write(b"Hello World")
# message = data.read()
# # data.close()
# print(message)

# db = SQLDataSource(db_path="playground.db")
# db.open()
# db.write("CREATE TABLE IF NOT EXISTS playground (id INTEGER PRIMARY KEY, message TEXT)")
# db.write("INSERT INTO playground (message) VALUES ('Hello World')")
# message = db.read("SELECT * FROM playground")
# print(message)
# db.close()

json_data = JSONFileDataSource(file_path="playground.json")
json_data.open()
json_data.write({"message": "Helloo World"})
message = json_data.read()
print(message)
json_data.close()
