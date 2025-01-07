Here's the updated documentation for the `FileManager` class to reflect that the `search` and `fetch` methods now accept `Q` objects for query filtering.

---

# FileManager Library Documentation

## Overview

The `FileManager` class is designed to manage files and their associated metadata and chunks. It provides functionalities to search, filter, fetch, and manipulate files using various criteria including complex query objects (`Q`). This updated documentation provides a detailed overview of the methods and properties available in the `FileManager` class, particularly highlighting the integration of `Q` objects to refine search and fetch operations.

## Initialization

### `__init__`
Initializes the `FileManager` instance.

**Parameters:**
- `tokenizer` (tiktoken.Encoding): Tokenizer to be used. Default is `DEFAULTS.tokenizer`.
- `chat_only` (bool): If true, restricts the search to chat files only. Default is False.
- `search_type` (SearchType): Defines the type of search to be performed. Default is SearchType.COMBINED.
- `scopes` (list[str]): list of scopes to be used in searches. Default is an empty list.

## Properties

### `uploaded`
Returns a new `FileManager` instance with `chat_only` set to True.

## Methods

### `search`
Performs a search based on either a string query or a `Q` object and returns a `FileList`.

**Parameters:**
- `query` (str | Q): The search query, which can be a string or a `Q` object for complex queries. Default is an empty string.
- `limit` (int): The maximum number of results to return. Default is 1000.

**Returns:**
- `FileList`: list of files matching the search criteria.

### `fetch`
Fetches content based on the current filters, which can be defined using `Q` objects, and returns a `FileList`.

**Returns:**
- `FileList`: list of files matching the current filters.

### `filter`
Applies filters to the search using a `Q` object and returns a new `FileManager` instance.

**Parameters:**
- `filters` (Q): The `Q` object specifying the filters to apply.

**Returns:**
- `FileManager`: A new instance of `FileManager` with the specified filters.

### `using`
Sets the search type and returns a new `FileManager` instance.

**Parameters:**
- `search_type` (SearchType): The search type to be used.

**Returns:**
- `FileManager`: A new instance of `FileManager` with the specified search type.

### `scoped`
Sets the scopes and returns a new `FileManager` instance.

**Parameters:**
- `scopes` (list[str] | str): list of scopes to be used.

**Returns:**
- `FileManager`: A new instance of `FileManager` with the specified scopes.

### `all`
Retrieves all files and returns a `FileList`.

**Returns:**
- `FileList`: list of all files.

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

### `create`
Creates a new file.

**Parameters:**
- `name` (str): The name of the file.
- `mime` (str): The MIME type of the file. Default is "text/plain".

**Returns:**
- `File`: The newly created file.

## Examples

### Example 1: Basic Initialization and Fetching All Files

```python
# Initialize FileManager with default settings
file_manager = FileManager(tokenizer="default")

# Fetch all files and print details
all_files = file_manager.all()
for file in all_files:
    print(f"File ID: {file.id}, File Name: {file.name}")
```

### Example 2: Scoped Search

```python
# Define scopes and perform a scoped search for specific files
scoped_manager = file_manager.scoped(['project-documents', 'team-meetings'])
scoped_files = scoped_manager.search(query="meeting notes")
for file in scoped_files:
    print(f"Scoped File ID: {file.id}, File Name: {file.name}")
```

### Example 3: Filtering Files Using a Complex Q Object

```python
# Filter files using complex conditions with Q objects
from blue_lugia.models import Q
complex_filter = Q(name__startswith='Project') & ~Q(status='Archived')
filtered_manager = file_manager.filter(complex_filter)
filtered_files = filtered_manager.fetch()
for file in filtered_files:
    print(f"Filtered File ID: {file.id}, File Name: {file.name}")
```

### Example 4: Sorting Files by Creation Date

```python
# Sort files by their creation date in descending order
sorted_files = file_manager.all().sort(key=lambda x: x.created_at, reverse=True)
for file in sorted_files:
    print(f"Sorted File ID: {file.id}, File Name: {file.name}, Created At: {file.created_at}")
```

### Example 5: Creating and Retrieving a Specific File by ID

```python
# Create a new file and retrieve it by its ID
new_file = file_manager.create(name="annual_report.txt", mime="text/plain")
print(f"New File ID: {new_file.id}, File Name: {new_file.name}")

# Retrieve the newly created file by its ID
retrieved_file = file_manager.get_by_id(new_file.id)
if retrieved_file:
    print(f"Retrieved File ID: {retrieved_file.id}, File Name: {retrieved_file.name}")
```

### Example 6: Counting Files with Specific Attributes

```python
# Count files with MIME type 'text/plain'
count_plain_text_files = file_manager.filter(Q(mime__eq="text/plain")).count()
print(f"Total number of plain text files: {count_plain_text_files}")
```

### Example 7: Using Custom Search Types

```python
# Change the search type to 'FILES_ONLY' and perform a search
files_only_manager = file_manager.using(search_type=SearchType.FILES_ONLY)
files = files_only_manager.search(query="confidential")
for file in files:
    print(f"Files Only Search - File ID: {file.id}, File Name: {file.name}")
```

### Example 8: Updating File Information

```python
# Update a file's name and MIME type
file_to_update = file_manager.get_by_id("someFileId")
if file_to_update:
    updated_file = file_manager.create(name="updated_document.txt", mime="application/pdf", scope=file_to_update.scope)
    print(f"Updated File ID: {updated_file.id}, New Name: {updated_file.name}, New MIME: {updated_file.mime_type}")
```

### Example 9: Using Fetch with Filters Applied on Date Range

```python
from datetime import datetime, timedelta
# Define a date range filter for files created within the last month
date_one_month_ago = datetime.now() - timedelta(days=30)
date_filter = Q(created_at__gte=date_one_month_ago)
recent_files_manager = file_manager.filter(date_filter)
recent_files = recent_files_manager.fetch()
for file in recent_files:
    print(f"Recent File ID: {file.id}, File Name: {file.name}, Created At: {file.created_at}")
```
