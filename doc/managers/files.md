# FileManager Library Documentation

## Overview
The `FileManager` class is designed to manage files and their associated metadata and chunks. It provides functionalities to search, filter, fetch, and manipulate files using various criteria. This documentation provides a detailed overview of the methods and properties available in the `FileManager` class.

## Initialization
### `__init__`
Initializes the `FileManager` instance.

**Parameters:**
- `event` (ExternalModuleChosenEvent): The event object containing user and company information.
- `chat_only` (bool): If true, restricts the search to chat files only. Default is False.
- `search_type` (SearchType): Defines the type of search to be performed. Default is SearchType.COMBINED.
- `scopes` (List[str]): List of scopes to be used in searches. Default is an empty list.
- `tokenizer` (tiktoken.Encoding): Tokenizer to be used. Default is `DEFAULTS.tokenizer`.

## Properties
### `uploaded`
Returns a new `FileManager` instance with `chat_only` set to True.

## Methods
### `_cast_search`
Converts search results into a `FileList`.

**Parameters:**
- `chunks` (unique_sdk.Search): Search results containing chunks of data.

**Returns:**
- `FileList`: List of files with their associated chunks.

### `_cast_content`
Converts content results into a `FileList`.

**Parameters:**
- `files` (unique_sdk.Content): Content results containing files and chunks.

**Returns:**
- `FileList`: List of files with their associated chunks.

### `using`
Sets the search type and returns a new `FileManager` instance.

**Parameters:**
- `search_type` (SearchType): The search type to be used.

**Returns:**
- `FileManager`: A new instance of `FileManager` with the specified search type.

### `scoped`
Sets the scopes and returns a new `FileManager` instance.

**Parameters:**
- `scopes` (List[str]): List of scopes to be used.

**Returns:**
- `FileManager`: A new instance of `FileManager` with the specified scopes.

### `search`
Performs a search and returns a `FileList`.

**Parameters:**
- `query` (str): The search query. Default is an empty string.
- `limit` (int): The maximum number of results to return. Default is 1000.

**Returns:**
- `FileList`: List of files matching the search criteria.

### `fetch`
Fetches content based on the current filters and returns a `FileList`.

**Returns:**
- `FileList`: List of files matching the current filters.

### `filter`
Applies filters to the search and returns a new `FileManager` instance.

**Parameters:**
- `op` (Op): The operator to use for combining filters. Default is `Op.OR`.
- `**kwargs`: The filters to be applied.

**Returns:**
- `FileManager`: A new instance of `FileManager` with the specified filters.

### `all`
Retrieves all files and returns a `FileList`.

**Returns:**
- `FileList`: List of all files.

### `first`
Returns the first file in the list.

**Returns:**
- `File`: The first file.

### `last`
Returns the last file in the list.

**Returns:**
- `File`: The last file.

### `get_by_id`
Returns a file by its ID.

**Parameters:**
- `file_id` (str): The ID of the file.

**Returns:**
- `File`: The file with the specified ID.

### `get_by_name`
Returns a file by its name.

**Parameters:**
- `name` (str): The name of the file.

**Returns:**
- `File`: The file with the specified name.

### `count`
Returns the total number of files.

**Returns:**
- `int`: The number of files.

### `__len__`
Returns the total number of files.

**Returns:**
- `int`: The number of files.

### `values`
Returns a list of values for specified attributes.

**Parameters:**
- `*args`: The attributes to retrieve.
- `**kwargs`: Additional options.

**Returns:**
- `List`: List of values for the specified attributes.

### `create`
Creates a new file.

**Parameters:**
- `name` (str): The name of the file.
- `mime` (str): The MIME type of the file. Default is "text/plain".

**Returns:**
- `File`: The newly created file.

# Usage Examples

## Example 1: Basic Initialization

```python
from blue_lugia.models import ExternalModuleChosenEvent
from blue_lugia.enums import SearchType
from blue_lugia.config import DEFAULTS
import tiktoken

event = ExternalModuleChosenEvent(userId="user123", companyId="company123", payload={"chatId": "chat123"})
file_manager = FileManager(event)
```

## Example 2: Searching Files

```python
file_list = file_manager.search(query="project report", limit=10)
for file in file_list:
    print(f"File ID: {file.id}, File Name: {file.name}")
```

## Example 3: Filtering Files

```python
file_manager_filtered = file_manager.filter(name__eq="report.pdf")
filtered_files = file_manager_filtered.fetch()
for file in filtered_files:
    print(f"Filtered File ID: {file.id}, File Name: {file.name}")
```

## Example 4: Creating a New File

```python
new_file = file_manager.create(name="new_document.txt", mime="text/plain")
print(f"New File ID: {new_file.id}, File Name: {new_file.name}")
```

## Example 5: Getting a File by ID

```python
file_id = "file123"
file = file_manager.get_by_id(file_id)
print(f"File ID: {file.id}, File Name: {file.name}")
```

## Example 6: Getting the First and Last Files

```python
first_file = file_manager.first()
print(f"First File ID: {first_file.id}, File Name: {first_file.name}")

last_file = file_manager.last()
print(f"Last File ID: {last_file.id}, File Name: {last_file.name}")
```

## Example 7: Using Scoped Search

```python
scopes = ["scope1", "scope2"]
scoped_file_manager = file_manager.scoped(scopes)
scoped_files = scoped_file_manager.search(query="meeting notes")
for file in scoped_files:
    print(f"Scoped File ID: {file.id}, File Name: {file.name}")
```

## Example 8: Counting Files

```python
total_files = file_manager.count()
print(f"Total number of files: {total_files}")
```

## Example 9: Retrieving File Values

```python
file_values = file_manager.values("id", "name", flat=True)
for value in file_values:
    print(f"File Value: {value}")
```