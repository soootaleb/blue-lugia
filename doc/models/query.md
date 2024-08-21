Here's an extensive markdown documentation for the `Q` class:

---

# Q Class Documentation

The `Q` class facilitates the creation of complex query expressions for filtering data based on specified conditions that are logically connected. It is inspired by Django's Q objects, allowing for advanced queries with AND, OR, and NOT logical connectors. The class supports the construction of query conditions using simple key-value pairs, nested Q objects, and combinations thereof using logical operations.

## Features

- **Logical Operations**: Combine query objects using AND, OR, and NOT operations.
- **Nested Queries**: Support for nested conditions within a single query object.
- **Flexible Query Conditions**: Accepts multiple condition formats and custom operations like `gt`, `lt`, `contains`, etc.
- **Dynamic Evaluation**: Evaluate the constructed query against a dictionary to filter data dynamically.

## Usage

Below are typical use cases demonstrating how to construct queries using the `Q` class:

### Simple Condition

```python
q = Q(age__gt=30)
```

This creates a query that checks if the `age` field is greater than 30.

### Combining Conditions

```python
q = Q(name__startswith='J', age__lt=50)
```

This query will be true for records where `name` starts with 'J' and `age` is less than 50.

### Logical AND

```python
q = Q(name__startswith='J') & Q(age__lt=50)
```

Equivalent to the previous example, but explicitly using the AND connector.

### Logical OR

```python
q = Q(name__startswith='J') | Q(name__startswith='A')
```

Selects records where `name` starts with either 'J' or 'A'.

### Logical NOT

```python
q = ~Q(status='inactive')
```

Negates the condition, thus selecting records where `status` is not 'inactive'.

### Nested Conditions

```python
q = Q(Q(name__startswith='J') | Q(name__startswith='A'), age__lt=50)
```

Combines multiple conditions where `name` starts with 'J' or 'A', and `age` is less than 50.

## Methods

### `__init__(self, *args: "Q", **kwargs: Any) -> None`

Initializes a new Q object, optionally with nested Q objects and keyword conditions.

### `__or__(self, other: "Q") -> "Q"`

Combines this Q object with another using a logical OR and returns the result as a new Q object.

### `__and__(self, other: "Q") -> "Q"`

Combines this Q object with another using a logical AND and returns the result as a new Q object.

### `__invert__(self) -> "Q"`

Returns a new Q object that is the logical negation of this Q object.

### `pprint(self) -> None`

Pretty prints the Q object's dictionary representation for debugging and visualization.

### `evaluate(self, data: dict[str, Any]) -> bool`

Evaluates the query expression against the provided data dictionary. Returns `True` if the data matches the conditions specified, otherwise `False`.

## Properties

### `conditions`

Returns a list of conditions and/or nested Q objects within this Q object.

### `connector`

Returns the logical connector (AND, OR) used in this Q object.

### `negated`

Indicates whether the current Q object is negated.

## Examples

Here is an example of constructing a query and evaluating data against it:

```python
# Define the query
query = Q(name__startswith='J') & ~Q(status='inactive')

# Data to evaluate
data = {'name': 'John', 'status': 'active'}

# Evaluate the query
result = query.evaluate(data)  # Returns True
```

This documentation covers the creation, usage, and evaluation of Q objects for advanced data querying scenarios.

Certainly! Here are more examples of using the `Q` class, ranging from simple to more complex queries. These examples will help illustrate the flexibility and power of the `Q` class for constructing various types of query conditions.

## Simple Queries

### Single Condition

```python
# Query to check if the 'age' is exactly 30
simple_query = Q(age=30)
```

### Single Condition with Operation

```python
# Query to find entries where 'age' is greater than 20
gt_query = Q(age__gt=20)
```

### Negation

```python
# Query to find entries where 'active' is NOT True
negated_query = ~Q(active=True)
```

## Combining Conditions

### Using AND

```python
# Query to find entries where 'age' is greater than 20 and 'name' starts with 'J'
and_query = Q(age__gt=20) & Q(name__startswith='J')
```

### Using OR

```python
# Query to find entries where 'age' is less than 18 or greater than 65
or_query = Q(age__lt=18) | Q(age__gt=65)
```

## Nested Conditions

### Nested AND and OR

```python
# Query to find entries where 'age' is between 30 and 40, and 'name' starts with 'A' or 'B'
nested_query = Q(age__gte=30, age__lte=40) & (Q(name__startswith='A') | Q(name__startswith='B'))
```

### Complex Negation with Nesting

```python
# Query to find entries where 'status' is not 'inactive' and either 'age' is over 50 or 'name' ends with 'son'
complex_negated_query = ~Q(status='inactive') & (Q(age__gt=50) | Q(name__endswith='son'))
```

## Real-World Example Scenarios

### Employee Data Filtering

```python
# Find active employees in the 'Engineering' department who are either managers or senior-level
employee_query = Q(department='Engineering', status='active') & (Q(title__contains='Manager') | Q(level__startswith='Senior'))
```

### Inventory Management

```python
# Find items in a specific category that are either low stock or discontinued
inventory_query = Q(category='Electronics') & (Q(stock__lte=5) | Q(status='Discontinued'))
```

### Health Records

```python
# Find patients over 65 who have diabetes and high blood pressure
patient_query = Q(age__gt=65) & Q(conditions__contains='diabetes') & Q(conditions__contains='high blood pressure')
```

These examples cover a range of use cases from simple condition checks to more intricate queries involving logical operators and nested conditions. They demonstrate how the `Q` class can be used to build dynamic and powerful queries for various applications.