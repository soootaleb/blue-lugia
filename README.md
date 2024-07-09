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

def module(state: StateManager) -> bool:
    return True
```

Once you've created your module, you must register it as a Flask app to be served.

`App` inherits `Flask` so it can be instantiated as a Flask app.

The app name is used as the external module's name, especially for event target matching.

Module name is case insensitive.

```python
# app.py
from blue_lugia.app import App
from blue_lugia.state import StateManager
from .module import module

app = App("MyExternalModule").of(module)
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

## Example

Here are a bunch of code samples to help you get started.

```python

# The module is a function accepting a state manager
def module(state: StateManager[ModuleConfig]) -> None:
    # ============= LOGGING =======================

    # log messages with the state logger
    state.logger.debug(f"Just entered the module of app {state.app.name}")

    # create child loggers for better readability
    logger = state.logger.getChild("ChildLogger")

    # state exposes the configuration, based on default values set by ModuleConfig, overriden by envars, overriden by assistant config from the UI
    logger.debug(f"languageModel is {state.conf.languageModel}")

    # ===================== MODELS ========================

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

    # ===================== MANAGERS ========================

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

    # ====================== COMBINING ============================

    # Let's try to do some RAG

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
    formated_sources: str = chunks.xml()

    context.append(Message.SYSTEM(f"The available sources are: {formated_sources}"))

    # Format the retrieved data as a search context for the frontend to create the links
    search_context = chunks.as_context()

    # Use the LLM to answer directly to the frontend
    completion = llm.complete(context, out=state.last_ass_message, search_context=search_context)

    # Completion is already in frontend, but you could analyse it
    state.logger.debug(f"LLM responded with {completion.content}")

    # ============================ STATE ==============================

    # TODO

    state.files.uploaded.search().as_files().first()
    state.complete(out=state.last_ass_message)
```