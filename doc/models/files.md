# File Management Documentation

## Overview

This module defines classes for handling files and their content within a chatbot framework. It includes classes for representing chunks of content (`Chunk`), a list of chunks (`ChunkList`), files (`File`), and a list of files (`FileList`). These classes provide methods for manipulating and interacting with file content, tokenization, and storage.

## Classes

### Chunk

The `Chunk` class represents a piece of content within a file. It includes methods for cleaning, tokenizing, and truncating the content.

#### Attributes

- `id`: `str` - The unique identifier for the chunk.
- `order`: `int` - The order of the chunk within the file.
- `content`: `str` - The content of the chunk.
- `start_page`: `int` - The starting page of the chunk.
- `end_page`: `int` - The ending page of the chunk.
- `created_at`: `datetime.datetime` - The timestamp when the chunk was created.
- `updated_at`: `datetime.datetime` - The timestamp when the chunk was last updated.
- `_tokenizer`: `tiktoken.Encoding` - The tokenizer used for encoding the content.

#### Methods

- `__init__(id: str, order: int, content: str, start_page: int, end_page: int, created_at: datetime.datetime, updated_at: datetime.datetime, tokenizer: tiktoken.Encoding) -> None`: Initializes a new chunk.
- `tokens() -> list[int]`: Property that returns the tokenized content.
- `_clean_content(_content: str) -> str`: Cleans the content by removing certain tags.
- `using(model: str | tiktoken.Encoding) -> Chunk`: Sets the tokenizer based on the model and returns the chunk.
- `truncate(tokens_limit: int) -> Chunk`: Truncates the content to the specified token limit and returns the chunk.
- `__len__() -> int`: Returns the length of the content.

### ChunkList

The `ChunkList` class is a list of `Chunk` objects with additional utility methods.

#### Methods

- `first() -> Chunk`: Returns the first chunk in the list.
- `last() -> Chunk`: Returns the last chunk in the list.
- `sort(key=None, reverse=False) -> list`: Sorts the chunks in the list.
- `filter(f: Callable[[Chunk], bool]) -> ChunkList`: Filters the chunks in place based on the provided function.

### File

The `File` class represents a file within the chatbot framework. It includes methods for reading, writing, and manipulating file content.

#### Attributes

- `id`: `str` - The unique identifier for the file.
- `name`: `str` - The name of the file.
- `chunks`: `ChunkList` - The list of chunks within the file.
- `mime_type`: `str` - The MIME type of the file.
- `read_url`: `str` - The URL for reading the file.
- `write_url`: `str` - The URL for writing to the file.
- `_event`: `ExternalModuleChosenEvent` - The event associated with the file.
- `_tokenizer`: `tiktoken.Encoding` - The tokenizer used for encoding the content.

#### Methods

- `__init__(event: ExternalModuleChosenEvent, id: str, name: str, mime_type: str, chunks=ChunkList(), tokenizer=None, read_url="", write_url="") -> None`: Initializes a new file.
- `content() -> str`: Property that returns the concatenated content of all chunks.
- `xml() -> str`: Property that returns the content as XML.
- `tokens() -> list[int]`: Property that returns the tokenized content.
- `using(model: str | tiktoken.Encoding) -> File`: Sets the tokenizer based on the model and returns the file.
- `truncate(tokens_limit: int) -> File`: Truncates the content to the specified token limit and returns the file.
- `write(content: str) -> File`: Writes the content to the file and updates the storage.

### FileList

The `FileList` class is a list of `File` objects with additional utility methods.

#### Methods

- `first() -> File`: Returns the first file in the list.
- `last() -> File`: Returns the last file in the list.

## Usage Example

```python
from your_module import Chunk, ChunkList, File, FileList, ExternalModuleChosenEvent
import datetime
import tiktoken

# Example tokenizer
tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")

# Create a chunk
chunk = Chunk(
    id="chunk1",
    order=1,
    content="This is a test chunk.",
    start_page=1,
    end_page=1,
    created_at=datetime.datetime.now(),
    updated_at=datetime.datetime.now(),
    tokenizer=tokenizer
)

# Create a chunk list
chunk_list = ChunkList([chunk])

# Create an event
event = ExternalModuleChosenEvent(...)

# Create a file
file = File(
    event=event,
    id="file1",
    name="Test File",
    mime_type="text/plain",
    chunks=chunk_list,
    tokenizer=tokenizer
)

# Access file content
print(file.content)

# Write content to file
file.write("New content for the file.")

# Truncate file content
file.truncate(100)

# Create a file list
file_list = FileList([file])

# Access first and last files
first_file = file_list.first()
last_file = file_list.last()

# Print file details
print(first_file)
print(last_file)
