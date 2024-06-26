# Message Models Documentation

## Overview

This module defines the `Message` and `MessageList` classes, which are used to handle individual messages and lists of messages within a chatbot framework. The `Message` class includes methods for manipulating and interacting with message content, while the `MessageList` class provides utility methods for working with lists of messages.

## Classes

### Message

The `Message` class represents a single message within the chatbot framework. It includes methods for updating, appending, and deleting messages, as well as properties for accessing message content, role, and other metadata.

#### Attributes

- `role`: `Role` - The role of the message (e.g., USER, SYSTEM, ASSISTANT).
- `content`: `Optional[_Content]` - The content of the message.
- `id`: `Optional[str]` - The unique identifier of the message.
- `debug`: `dict` - Debug information associated with the message.
- `is_command`: `bool` - Indicates whether the message is a command.

#### Methods

- `__init__(role: Role, content: Optional[str | _Content], remote=None) -> None`: Initializes a new message.
- `update(content: str | _Content, debug={}) -> Message`: Updates the content and debug information of the message.
- `append(content: str, new_line=True) -> Message`: Appends content to the message.
- `prepend(content: str, new_line=True) -> Message`: Prepends content to the message.
- `delete()`: Deletes the message.
- `USER(cls, content: str | _Content) -> Message`: Class method to create a user message.
- `SYSTEM(cls, content: str | _Content) -> Message`: Class method to create a system message.
- `ASSISTANT(cls, content: str | _Content) -> Message`: Class method to create an assistant message.
- `__str__() -> str`: Returns a string representation of the message.

### MessageList

The `MessageList` class is a list of `Message` objects with additional utility methods.

#### Methods

- `first() -> Message`: Returns the first message in the list.
- `last() -> Message`: Returns the last message in the list.

## Usage Example

```python
from your_module import Message, MessageList, Role

# Create messages
user_message = Message.USER("Hello, how can I help you?")
system_message = Message.SYSTEM("System initialized.")
assistant_message = Message.ASSISTANT("Sure, I can help with that.")

# Update message content
user_message.update("Hello, how can I assist you?")

# Append and prepend content
user_message.append("Additional information.")
user_message.prepend("Important: ")

# Delete a message
assistant_message.delete()

# Create a message list
messages = MessageList([user_message, system_message, assistant_message])

# Access first and last messages
first_message = messages.first()
last_message = messages.last()

# Print message details
print(user_message)
print(system_message)
print(assistant_message)
