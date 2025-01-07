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
- `messages` (list[Message] | list[dict]): list of messages to send to the model.
- `tools` (list[Tool]): list of tools to be used by the model. Default is an empty list.
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
- `schema` (type[BaseModel]): The schema to be used.

**Returns:**
- `Parser`: The current instance of `Parser` with the specified schema.

### `following`
Sets the instructions to be followed by the parser.

**Parameters:**
- `instructions` (list[Message._Content | str | Message] | Message._Content | str | Message): The instructions to be followed.

**Returns:**
- `Parser`: The current instance of `Parser` with the specified instructions.

### `asserting`
Sets the assertions to be checked by the parser.

**Parameters:**
- `assertions` (list[tuple[Callable[[dict], bool], str] | Callable[[dict], bool]]): The assertions to be checked.

**Returns:**
- `Parser`: The current instance of `Parser` with the specified assertions.

### `parse`
Parses the query using the set schema, instructions, and assertions.

**Parameters:**
- `query` (Message._Content | str | Message): The query to be parsed.

**Returns:**
- `BaseModel`: The parsed response according to the set schema.

# Tool Calling

## Defining a tool

Tools are pydantic BaseModel

- The tool name is the class name
- The tool description is the docstring
- The tool arguments are the fields, their types and descriptions

```python
class SumTool(BaseModel):
    """Add two numbers"""
    x: int = Field(..., description="first value")
    y: int = Field(..., description="second value")
```

## Configure the tool

You can configure the tool with the `Config` inner class.


- `bl_fc_strict` will allow you to set `strict: False` when passing the tool schema to OpenAI.
- `bl_schema_strict` will allow you to set `strict: False` when using `response_format: json_schema`.


```python
class SumTool(BaseModel):
    """Add two numbers"""

    class Config:
        bl_fc_strict = False
```

## Running a tool

Create a `run` method in the tool class in order to execute it with the parameters

```python
...
    # The run method is executed by state.call(completion). The tool call formulated by the LLM results in an instance of the tool, so you can access arguments with self.x
    # What's returned by this method is considered the "tool response", so the state.call() will append a message { role: TOOL, content: run() } to the context
    def run(self, call_id: str, state: StateManager, *args, **kwargs) -> int:
        # state.last_ass_message.update(f"The sum of {self.x} and {self.y} is {self.x + self.y}")
        return self.x + self.y
```

## Using a tool

You need to register it with the state first

```python
state.register(SumTool)
```

Then it's passed when completing

```python
state.complete(message)
```

You can force its use with `tool_choice`

```python
completion = state.complete(messages, tool_choice=SumTool)
```

When you get a completion, it may have tool calls. You can run the associated tools with their arguments

```python
tools_called, tools_not_called, complete = state.call(completion)
```

## Forcing json output

You can force json output from OpenAI messages if you don't need to run a tool

```python
completion = state.complete(messages, output_json=True)
```

The json is in the message content, you can structure it

```python
data = completion.content.json()
```

> Beware that the messages you pass MUST include the "json" keyword as a prompt, or OpenAI will return an error.

## JSON Schema

A more reliable way to get json output is to use the `response_format: json_schema` option from OpenAI.

You can leverage it by passing a pydantic BaseModel to the completion method `schema` argument

```python
completion = state.complete(messages, schema=SumTool)
```

By default you're guaranteed to get a string respecting the schema, but you can smooth this by configuring your tool / schema

```python
class SumTool(BaseModel):
    """Add two numbers"""

    class Config:
        bl_schema_strict = False
```

Then you can retrieve the data from the content

```python
data = completion.content.json()
```

## LLM Parse

LLM exposes a utility method to get a pydantic model from a completion

```python
parsed = state.llm.parse(completion, schema=SumTool)
```

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