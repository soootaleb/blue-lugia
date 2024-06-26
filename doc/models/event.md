# Event Models Documentation

## Overview

This module defines various Pydantic models used for representing messages and events within a chatbot framework. These models ensure data validation and structure for user and assistant messages, payloads, and events.

## Classes

### UserMessage

A Pydantic model representing a user message.

#### Attributes

- `id`: `str` - The unique identifier for the message.
- `text`: `str` - The text content of the message.
- `createdAt`: `str` - The timestamp when the message was created.

### AssistantMessage

A Pydantic model representing an assistant message.

#### Attributes

- `id`: `str` - The unique identifier for the message.
- `createdAt`: `str` - The timestamp when the message was created.

### Payload

A Pydantic model representing the payload of an event.

#### Attributes

- `name`: `str` - The name of the event.
- `description`: `str` - The description of the event.
- `configuration`: `dict[str, Any]` - The configuration settings for the event.
- `chatId`: `str` - The unique identifier for the chat.
- `assistantId`: `str` - The unique identifier for the assistant.
- `userMessage`: `UserMessage` - The user message associated with the event.
- `assistantMessage`: `AssistantMessage` - The assistant message associated with the event.

### ExternalModuleChosenEvent

A Pydantic model representing an external module chosen event.

#### Attributes

- `id`: `str` - The unique identifier for the event.
- `version`: `str` - The version of the event.
- `event`: `str` - The type of event.
- `createdAt`: `int` - The timestamp when the event was created.
- `userId`: `str` - The unique identifier for the user.
- `companyId`: `str` - The unique identifier for the company.
- `payload`: `Payload` - The payload containing detailed information about the event.

## Usage Example

```python
from your_module import UserMessage, AssistantMessage, Payload, ExternalModuleChosenEvent

# Example user message
user_message = UserMessage(
    id="user123",
    text="Hello, how can I help you?",
    createdAt="2023-05-30T12:00:00Z"
)

# Example assistant message
assistant_message = AssistantMessage(
    id="assistant123",
    createdAt="2023-05-30T12:01:00Z"
)

# Example payload
payload = Payload(
    name="example_event",
    description="An example event",
    configuration={"key": "value"},
    chatId="chat123",
    assistantId="assistant123",
    userMessage=user_message,
    assistantMessage=assistant_message
)

# Example external module chosen event
event = ExternalModuleChosenEvent(
    id="event123",
    version="1.0",
    event="module_chosen",
    createdAt=1672531199,
    userId="user123",
    companyId="company123",
    payload=payload
)

# Accessing event attributes
print(event.id)
print(event.payload.userMessage.text)
