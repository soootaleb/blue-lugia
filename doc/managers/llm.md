# LanguageModelManager Library Documentation

## Overview
The `LanguageModelManager` class is designed to manage interactions with language models, including OpenAI's models and custom models from `unique_sdk`. It provides functionalities to set up, call, and parse responses from these models. This documentation provides a detailed overview of the methods and properties available in the `LanguageModelManager` class.

## Initialization
### `__init__`
Initializes the `LanguageModelManager` instance.

**Parameters:**
- `event` (ExternalModuleChosenEvent): The event object containing user and company information.
- `model` (Model): The language model to be used. Default is `DEFAULTS.llm_model`.
- `temperature` (float): The temperature setting for the language model. Default is 0.0.
- `timeout` (int): The timeout setting for the language model. Default is `DEFAULTS.llm_timeout`.

## Properties
### `parser`
Returns a new `Parser` instance for parsing model responses.

## Methods
### `oai`
Sets up the manager to use OpenAI with the provided API key.

**Parameters:**
- `key` (str): The OpenAI API key.

**Returns:**
- `LanguageModelManager`: A new instance of `LanguageModelManager` with OpenAI configured.

### `complete`
Completes the response using the language model.

**Parameters:**
- `messages` (List[Message] | List[dict]): List of messages to send to the model.
- `tools` (List[Tool]): List of tools to be used by the model. Default is an empty list.
- `tool_choice` (list): Optional tool choice settings. Default is an empty list.
- `max_tokens` (int | Literal["auto"]): Maximum number of tokens for the response. Default is None.

**Returns:**
- `Message`: The completed message response from the model.

### `using`
Sets the language model to be used.

**Parameters:**
- `model` (Model): The language model to be used.

**Returns:**
- `LanguageModelManager`: The current instance of `LanguageModelManager` with the specified model.

## Parser Class
### `into`
Sets the schema to be used by the parser.

**Parameters:**
- `schema` (Type[BaseModel]): The schema to be used.

**Returns:**
- `Parser`: The current instance of `Parser` with the specified schema.

### `following`
Sets the instructions to be followed by the parser.

**Parameters:**
- `instructions` (List[Message._Content | str | Message] | Message._Content | str | Message): The instructions to be followed.

**Returns:**
- `Parser`: The current instance of `Parser` with the specified instructions.

### `asserting`
Sets the assertions to be checked by the parser.

**Parameters:**
- `assertions` (List[Tuple[Callable[[dict], bool], str] | Callable[[dict], bool]]): The assertions to be checked.

**Returns:**
- `Parser`: The current instance of `Parser` with the specified assertions.

### `parse`
Parses the query using the set schema, instructions, and assertions.

**Parameters:**
- `query` (Message._Content | str | Message): The query to be parsed.

**Returns:**
- `BaseModel`: The parsed response according to the set schema.

# Usage Examples

## Example 1: Basic Initialization

```python
from blue_lugia.models import ExternalModuleChosenEvent
from blue_lugia.enums import Model
from blue_lugia.config import DEFAULTS

event = ExternalModuleChosenEvent(userId="user123", companyId="company123", payload={"chatId": "chat123"})
llm_manager = LanguageModelManager(event)
```

## Example 2: Calling the Language Model

```python
from blue_lugia.models import Message, Tool
from blue_lugia.enums import Role

messages = [
    Message(role=Role.USER, content="What is the weather like today?")
]
tools = []

response = llm_manager.call(messages, tools)
for call in response:
    print(f"Tool Name: {call.name}, Arguments: {call.arguments}")
```

## Example 3: Using OpenAI

```python
llm_manager_oai = llm_manager.oai(key="your_openai_api_key")
messages = [
    Message(role=Role.USER, content="Tell me a joke.")
]
response = llm_manager_oai.complete(messages)
print(f"Response: {response.content}")
```

## Example 4: Using a Specific Model

```python
from blue_lugia.enums import Model

llm_manager_custom = llm_manager.using(model=Model.GPT3)
messages = [
    Message(role=Role.USER, content="Summarize the latest news.")
]
response = llm_manager_custom.complete(messages)
print(f"Response: {response.content}")
```

## Example 5: Parsing a Response

```python
from pydantic import BaseModel

class MySchema(BaseModel):
    summary: str

parser = llm_manager.parser.into(MySchema).following("Please summarize the following text.").asserting([
    (lambda x: 'summary' in x, "Summary field is missing.")
])

query = Message.USER("Here is a long text to be summarized...")
parsed_response = parser.parse(query)
print(f"Parsed Summary: {parsed_response.summary}")
```

## Example 6: Streaming a Response

```python
messages = [
    Message(role=Role.USER, content="Continue writing this story.")
]
response = llm_manager.stream(messages)
print(f"Streamed Response: {response.content}")
```