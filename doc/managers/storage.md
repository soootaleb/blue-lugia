# StorageManager Library Documentation

## Overview
The `StorageManager` class is designed to manage key-value storage within a message's debug information. It provides functionalities to get and set values in the storage. This documentation provides a detailed overview of the methods and properties available in the `StorageManager` class.

## Initialization
### `__init__`
Initializes the `StorageManager` instance.

**Parameters:**
- `event` (ExternalModuleChosenEvent): The event object containing user and company information.
- `store` (Message): The message object containing debug information.

## Properties
### `data`
Returns the current storage data as a dictionary.

**Returns:**
- `dict`: The current storage data.

## Methods
### `__getitem__`
Retrieves a value from the storage by key.

**Parameters:**
- `key` (str): The key of the value to retrieve.

**Returns:**
- `dict`: The value associated with the specified key.

### `__setitem__`
Sets a value in the storage by key.

**Parameters:**
- `key` (str): The key of the value to set.
- `value` (dict): The value to set.

### `get`
Retrieves a value from the storage by key, with an optional default.

**Parameters:**
- `key` (str): The key of the value to retrieve.
- `default` (any): The default value to return if the key is not found. Default is None.

**Returns:**
- `dict`: The value associated with the specified key, or the default value.

### `set`
Sets a value in the storage by key.

**Parameters:**
- `key` (str): The key of the value to set.
- `value` (dict): The value to set.

**Returns:**
- `dict`: The updated storage data.

# Usage Examples

## Example 1: Basic Initialization

```python
from blue_lugia.models import ExternalModuleChosenEvent, Message
from blue_lugia.config import DEFAULTS

event = ExternalModuleChosenEvent(userId="user123", companyId="company123", payload={"chatId": "chat123"})
message = Message(role=Role.USER, content="Initial message")
storage_manager = StorageManager(event, message)
```

## Example 2: Retrieving Data

```python
store_data = storage_manager.data
print(f"Store Data: {store_data}")
```

## Example 3: Getting a Value by Key

```python
value = storage_manager.get("key1", default={"default": "value"})
print(f"Value for 'key1': {value}")
```

## Example 4: Setting a Value by Key

```python
storage_manager.set("key1", {"example": "data"})
updated_data = storage_manager.data
print(f"Updated Store Data: {updated_data}")
```

## Example 5: Using Bracket Notation to Get and Set Values

```python
# Getting a value using bracket notation
value = storage_manager["key1"]
print(f"Value for 'key1' using bracket notation: {value}")

# Setting a value using bracket notation
storage_manager["key2"] = {"another": "example"}
print(f"Updated Store Data: {storage_manager.data}")
```