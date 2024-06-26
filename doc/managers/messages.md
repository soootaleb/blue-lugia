# MessageManager Library Documentation

## Overview
The `MessageManager` class is designed to manage messages within a chat, including retrieving, filtering, creating, and deleting messages. This documentation provides a detailed overview of the methods and properties available in the `MessageManager` class.

## Initialization
### `__init__`
Initializes the `MessageManager` instance.

**Parameters:**
- `event` (ExternalModuleChosenEvent): The event object containing user and company information.

## Methods
### `all`
Retrieves all messages and returns a `MessageList`.

**Returns:**
- `MessageList`: List of all messages.

### `filter`
Applies a filter to the messages and returns a new `MessageManager` instance.

**Parameters:**
- `f` (Callable[[Message], bool]): The filter function to be applied.

**Returns:**
- `MessageManager`: A new instance of `MessageManager` with the filtered messages.

### `__getitem__`
Retrieves a message by index.

**Parameters:**
- `index` (int): The index of the message.

**Returns:**
- `Message`: The message at the specified index.

### `count`
Returns the total number of messages.

**Returns:**
- `int`: The number of messages.

### `first`
Returns the first message in the list.

**Returns:**
- `Message`: The first message.

### `last`
Returns the last message in the list.

**Returns:**
- `Message`: The last message.

### `get`
Retrieves a message by its ID.

**Parameters:**
- `message_id` (str): The ID of the message.

**Returns:**
- `Message`: The message with the specified ID.

### `values`
Returns a list of values for specified attributes.

**Parameters:**
- `*args`: The attributes to retrieve.
- `**kwargs`: Additional options.

**Returns:**
- `List`: List of values for the specified attributes.

### `create`
Creates a new message.

**Parameters:**
- `role_or_message` (Role | Message): The role or message to be created.
- `text` (str): The text of the message. Default is an empty string.

**Returns:**
- `Message`: The newly created message.

### `delete`
Deletes all messages.

**Returns:**
- `int`: The number of messages deleted.

# Usage Examples

## Example 1: Basic Initialization

```python
from blue_lugia.models import ExternalModuleChosenEvent
from blue_lugia.enums import Role
from blue_lugia.config import DEFAULTS

event = ExternalModuleChosenEvent(userId="user123", companyId="company123", payload={"chatId": "chat123"})
message_manager = MessageManager(event)
```

## Example 2: Retrieving All Messages

```python
all_messages = message_manager.all()
for message in all_messages:
    print(f"Message Role: {message.role}, Message Content: {message.content}")
```

## Example 3: Filtering Messages

```python
filtered_manager = message_manager.filter(lambda m: m.role == Role.USER)
filtered_messages = filtered_manager.all()
for message in filtered_messages:
    print(f"Filtered Message Role: {message.role}, Message Content: {message.content}")
```

## Example 4: Creating a New Message

```python
new_message = message_manager.create(Role.USER, "Hello, this is a new message!")
print(f"New Message Role: {new_message.role}, Message Content: {new_message.content}")
```

## Example 5: Getting a Message by ID

```python
message_id = "message123"
message = message_manager.get(message_id)
print(f"Message ID: {message_id}, Message Role: {message.role}, Message Content: {message.content}")
```

## Example 6: Getting the First and Last Messages

```python
first_message = message_manager.first()
print(f"First Message Role: {first_message.role}, Message Content: {first_message.content}")

last_message = message_manager.last()
print(f"Last Message Role: {last_message.role}, Message Content: {last_message.content}")
```

## Example 7: Counting Messages

```python
total_messages = message_manager.count()
print(f"Total number of messages: {total_messages}")
```

## Example 8: Retrieving Message Values

```python
message_values = message_manager.values("role", "content", flat=True)
for value in message_values:
    print(f"Message Value: {value}")
```

## Example 9: Deleting All Messages

```python
deleted_count = message_manager.delete()
print(f"Total number of messages deleted: {deleted_count}")
```