# blue-lugia

![Tests](https://github.com/soootaleb/blue-lugia/actions/workflows/test.yaml/badge.svg)
![Lint](https://github.com/soootaleb/blue-lugia/actions/workflows/lint.yaml/badge.svg)

A library to build unique applications

For a concrete usage example, you can see the Petal external module or the upload_in_chat module.

## Setup

Install python version with pyenv
```bash
pyenv install 3.12
pyenv local 3.12

```

Install dependencies
```bash
poetry env use 3.12
poetry install
```

To use the poetry venv
```bash
poetry shell
```

## Getting started

An external module is a python function that takes a `state: StateManager` argument.

```python
# module.py
from blue_lugia.state import StateManager

def module(state: StateManager) -> None:
    pass
```

Once you've created your module, you must register it as a Flask app to be served.

`App` inherits `Flask` so it can be instantiated as a Flask app.

The app name is used as the external module's name, especially for event target matching.

Module name is case insensitive.

```python
# app.py
from blue_lugia.app import App
from blue_lugia.state import StateManager
from my_external_module.module import module

app = App("MyExternalModule").of(module)
```

## Hello World

Make your module stream a response to the user using the context, which defaults to the conversation history.

In other words, make a conversational agent.

```python
def module(state: StateManager[ModuleConfig]) -> None:
    state.stream()
```


## Examples

Here are a bunch of code samples.

**Logging**

State has a logger, and you can get children out of it for better readability.

```python
def module(state: StateManager[ModuleConfig]) -> None:

    # log messages with the state logger
    state.logger.debug(f"Just entered the module of app {state.app.name}")

    # create child loggers for better readability
    logger = state.logger.getChild("ChildLogger")

    # state exposes the configuration, based on default values set by ModuleConfig, overriden by envars, overriden by assistant config from the UI
    logger.debug(f"languageModel is {state.conf.languageModel}")

```

**Models**

Models are used to represent data in the conversation.
Models and their associated lists have their methods to allow handling of remote entites.

```python
def module(state: StateManager[ModuleConfig]) -> None:

    # You generally manipulate models Message, File
    message: Message = Message(Role.USER, "Hello") or Message.USER("Hello")

    # Models have methods to handle them
    message.append("World")

    # And properties you can find using autocompletion
    state.logger.debug(message.content)

    # Models also have their associated lists
    history = MessageList([Message.SYSTEM("You are a helpful assistant"), Message.USER("Who are you ?")])

    # With their methods
    user_messages: MessageList = history.filter(lambda x: x.role == Role.USER)
    first_message: Message | None = history.first()
    first_system_message: Message | None = history.first(lambda x: x.role == Role.SYSTEM)
    truncated_messages: MessageList = history.keep(1000)

    # And their properties
    messages_tokens = history.tokens
```

**Managers**

Managers are used to interact with the API, and they expose methods to retrieve, create, update, delete the models.

```python
def module(state: StateManager[ModuleConfig]) -> None:

    # Managers are used to interact with the API
    files = state.files
    messages = state.messages
    llm = state.llm

    # They expose methods to retrieve, create, update, delete the models
    messages_in_chat: MessageList = messages.all()

    # The managers return models or list of models
    user_messages_in_chat: MessageList = messages.filter(lambda x: x.role == Role.USER).all()
    last_user_message: Message | None = messages.last(lambda x: x.role == Role.USER)  # equivalent to state.last_usr_message
    last_assistant_message: Message | None = messages.last(lambda x: x.role == Role.ASSISTANT)  # equivalent to state.last_ass_message

    # Note that managers have "configuration methods" and "execution methods"
    # For example, Manager.filter() does not execute a query, but instead returns a new manager with filters ready to be applied
    files: FileManager = files.filter(key__contains=".xlsx")

    # The files manager encapsulates both Search & Content APIs
    # Search returns a ChunkList while Content returns a FileList
    searching_chunks: ChunkList = files.search("What's directive 51 ?")
    retrieving_files: FileList = files.fetch()

    # Objects returned by a manager are generally compatible with methods of other managers
    completion: Message = llm.complete([Message.USER("Tell me a joke")])
    state.last_ass_message.update(completion.content)

    # LLM Manager streams to frontend if you provide a message to stream to
    llm.complete([Message.USER("Tell me a story between the moon, the earth and the sun")], out=state.last_ass_message)
```

**Simple RAG**

A simple RAG will combine the use of managers and models to retrieve data an make a completion.

```python
def module(state: StateManager[ModuleConfig]) -> None:
    # Retrieve some chunks
    chunks: ChunkList = state.files.search("What's directive 51 ?")

    # Prepare some prompting
    context: MessageList = MessageList(
        [
            Message.SYSTEM("Your role is to summarize the informatin asked by the user using bullet points."),
            Message.SYSTEM("You MUST cite your sources using [source0], [source1], [source2], etc"),
        ]
    )

    # You can manipulate the retrieved chunks before exposing it to the context
    chunks: ChunkList = chunks.sort(lambda chunk: chunk.order)

    # Format the sources to be exposed to the LLM
    formatted_sources: str = chunks.xml()

    context.append(Message.SYSTEM(f"The available sources are: {formatted_sources}"))

    # Format the retrieved data as a search context for the frontend to create the links
    search_context = chunks.as_context()

    # Use the LLM to answer directly to the frontend
    completion = llm.complete(context, out=state.last_ass_message, search_context=search_context)

    # Completion is already in frontend, but you could analyse it
    state.logger.debug(f"LLM responded with {completion.content}")

```

**State**

The state exposes a more abstract API that does more logic out of the box.
When created, the state builds the context as the conversation history.

```python
def module(state: StateManager[ModuleConfig]) -> None:
    state.complete(out=state.last_ass_message)
```

State exposes a method to stream to the last assistant message by default.
Since it also have the whole conversation history, this is make a conversational agent.

```python
def module(state: StateManager[ModuleConfig]) -> None:
    state.stream()
```

State also expose the possibility to make a completion when the LLM makes a tool call.
The loop will execute the tools until there is not more tool calls but a text completion instead

```python
def module(state: StateManager[ModuleConfig]) -> None:
    state.loop(out=state.last_ass_message)
```

> In this example we don't provide any tools to the state so no tool call will be possible.

## Tool

Tools can be declared and used in order to leverage LLMs function calling.

**Create a tool**

Tools are models that inherit the pydantic `BaseModel` class.
They represent a function that can be called by the LLM.
They also implement the execution of the tool.

- The class name is the function name
- The class doctstring is the function description
- The model fields are the function arguments
- Each field type is the argument type
- Each field description is the argument description

```python
class SumTool(BaseModel):
    """
    Use this tool to sum two numbers
    """

    x: int = Field(..., description="left hand side of the sum")
    y: int = Field(..., description="right hand side of the sum")

    def run(self, call_id: str, state: StateManager, extra: dict, out: Message | None):
        return self.x + self.y

    @classmethod
    def on_validation_error(cls, call_id: str, args: dict, state: StateManager, extra: dict, out: Message | None):
        validation_error = extra.get("validation_error") # you can find the pydantic validation error here

        # you can use the state to stream a message to the user
        state.last_ass_message.append("Ooops, something went wrong, gimme a sec...")

        # args is the dict returned by the LLM that didn't match the tool signature
        try:
            x = int(args.get("x", 0))
        except ValueError:
            x = 0

        try:
            y = int(args.get("y", 0))
        except ValueError:
            y = 0

        # And finally you can return a value so that even if the LLM call was not perfect, the tool calling falled back and the assistant can go on
        return x + y
```

**Use a tool**

Once you've declared a tool you must register it in the state to use it.

```python
def module(state: StateManager[ModuleConfig]) -> None:
    state.register(SumTool).loop(
        [
            Message.USER("What's the sum of 82395 and 31852 ?")
        ]
    )
```

You can also use the tool in a more granual manner

```python
def module(state: StateManager[ModuleConfig]) -> None:
    state.register(SumTool)
    
    completion = state.complete(
        [
            Message.USER("What's the sum of 82395 and 31852 ?")
        ],
        tool_choice=SumTool # Will force the LLM to call the tool
    )

    tools_called, tools_not_called, complete = state.call(completion)

    if tools_called:
        # tools_called is a list of tools that were called
        tool_execution_result: int = tools_called[0].get("call").get("run") # first tool call > execution > run method (tool can have pre_run_hook and post_run_hook)
    elif tools_not_called:
        # tools_not_called is a list of tools that were not called
        tool_execution_result: int = tools_not_called[0].get("handled") # first tool not called > handled method

    state.last_ass_message.append(f"The sum is {tool_execution_result}")
```


## App

[App](./doc/app.md)

## StateManager

[StateManager](./doc/state_manager.md)

## ModuleConfig

[ModuleConfig](./doc/module_config.md)

## Managers

Managers allow you to interact with Unique environments.
They rely on method chaining to configure the final call to Unique APIs.

### Messages

[Messages](./doc/managers/messages.md)

### LLM

[LanguageModelManager](./doc/managers/llm.md)

### Files

[Files](./doc/managers/files.md)

### Storage

[Storage](./doc/managers/storage.md)

## Commands

If the config settings `ALLOW_COMMANDS` is set to a true value, the external module will route commands accordingly.

## Models

### Event

[Event](./doc/models/event.md)

### Messages

[Messages](./doc/models/messages.md)

### Files

[Files](./doc/models/files.md)
