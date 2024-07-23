# State Managers

## Overview

This module defines abstract and concrete state managers responsible for handling the conversation history, messages, and interactions within a chatbot framework. The state managers are designed to integrate with a unique SDK and utilize various components like message managers, language model managers, file managers, and storage managers.

## Usage

### Overview
This README provides a guide for developers on how to use the `StateManager` to interact with a language model (LLM). This involves defining tools, running them, and handling documents within the state. The examples will demonstrate summarizing documents and performing operations on binary numbers.

### Table of Contents
1. [Initialization](#initialization)
2. [Defining Tools](#defining-tools)
   - [SummarizeTool](#summarizetool)
   - [SumBinaryNumbers](#sumbinarynumbers)
3. [Using the State Manager](#using-the-state-manager)
   - [Uploading Files](#uploading-files)
   - [Running Tools](#running-tools)
   - [Context Management](#context-management)
4. [Example Play Function](#example-play-function)

### Initialization
To begin, ensure you have the necessary imports and have initialized the `StateManager` object.

```python
from pydantic import BaseModel, Field
from blue_lugia.models import Message
from blue_lugia.state import StateManager
```

### Defining Tools

#### SummarizeTool
The `SummarizeTool` is designed to summarize the content of a specified document.

A tool must extend `pydantic.BaseModel`

- The function name is the class name __class__.__name__
- The function description is the class description __doc__
- The arguments are the class fields
- The type of the arguments is the field type
- The description of the arguments is the field description

`pre_run_hook` is executed when the tool is selected (provided as a tool_call by the LLM)
If it returns `False`, the tool will not be executed (`post_run_hook` will still be executed)

`run` is the main logic of the tool executed with the arguments provded by the LLM.
It takes
- the tool call ID from the LLM (you may want to refer to it using the llm manager)
- the state manager with its config, managers, context, etc
- extra arguments that can be provided by the user using `state.extra()`
- an output message that can be updated during the execution
If it returns `False` the loop over tools will not continue to execute other tools.

`post_run_hook` is executed after the tool is executed. It can be used to clean up or to decide if the loop over tools should continue.


```python
class SummarizeTool(BaseModel):
    """
    Summarize the document asked by the user.
    This tool must be used to identify the document identifier that relates to the user query.
    It's mandatory that the document id provided is available in the list provided.
    """

    document_id: str = Field(..., description="the document id to summarize")

    def pre_run_hook(self, call_id: str, state: StateManager, extra: dict | None = None, out: Message | None = None):
        """
        If this method returns False, the tool will not run.
        The post run hook will still be called.
        """
        pass

    def run(self, call_id: str, state: StateManager, extra: dict | None = None, out: Message | None = None):
        """
        Main logic of the tool.
        Summarizes the content of the document with the given document_id.
        """
        document = state.files.get_by_id(self.document_id)
        if out:
            out.update("_Summarizing document..._")
        completion = state.llm.complete(
            [
                Message.SYSTEM("Your role is to summarize the document."),
                Message.USER(document.content),
            ],
            out=out,
        )
        if not out:
            return completion

    def post_run_hook(self, call_id: str, state: StateManager, extra: dict | None = None, out: Message | None = None):
        """
        If this method returns False, the loop over tools will not continue.
        Returned messages are still added to the context.
        """
        pass
```

#### SumBinaryNumbers
The `SumBinaryNumbers` tool sums two binary numbers. This is an example to show how other operations can be performed using the state manager.

```python
class SumBinaryNumbers(BaseModel):
    x: str = Field(..., description="first binary number")
    y: str = Field(..., description="second binary number")

    def pre_run_hook(self, call_id: str, state: StateManager, extra: dict | None = None):
        """
        Hook to be run before the main logic. Can be used for setup tasks.
        """
        print("Pre run hook")

    def run(self, call_id: str, state: StateManager, extra: dict | None = None):
        """
        Main logic of the tool.
        Converts binary numbers to integers, sums them, and returns the result.
        """
        x = int(self.x, 2)
        y = int(self.y, 2)
        return x + y
```

### Using the State Manager

#### Fetching Files
To interact with documents, refer to the [files manager](./managers/files.md)

```python
files = state.files.uploaded.values("id", "name")
```

#### Running Tools
Register and run tools using the state manager. The `register` method registers a tool, and `loop` method runs the tool in the context of the state manager.

```python
state.context(Message.SYSTEM(f"The documents available are {files}"), prepend=True)
    .register(SummarizeTool)
    .loop(out=state.last_ass_message)
```

#### Context Management
Manage the context by expanding, keeping messages, and appending new ones. This is useful for maintaining conversation history or the sequence of operations.

```python
context = state.ctx.expand().keep(3000).append(Message.SYSTEM(f"Available documents: {files}"))
state.context(context).register(SummarizeTool).loop(" ".join(args), state.last_ass_message, "_Generating answer..._")
```

### Example Play Function
Below is an example of a play function demonstrating the use of the state object. The `play` function simulates the registration and execution of tools within the state.

```python
def play(state: StateManager, args: list[str] = []):
    """
    Development purpose only, use at your own risk
    """

    # Retrieve the list of uploaded files
    files = state.files.uploaded.values("id", "name")

    # Register and run the SummarizeTool
    state.context(Message.SYSTEM(f"The documents available are {files}"), prepend=True)
        .register(SummarizeTool)
        .loop(out=state.last_ass_message)

    # Alternatively, register and run the SumBinaryNumbers tool
    # Example usage: sum_tool = SumBinaryNumbers(x="1010", y="1101")
    # sum_tool.run("call_id_example", state)
```


## Classes

### StateManager

An abstract base class defining the interface for state management. It initializes various components and provides methods for managing the conversation history and messages.

#### Attributes

- `event`: `ExternalModuleChosenEvent` - The event triggering the state manager.
- `messages`: `MessageManager` - Manages the messages.
- `files`: `FileManager` - Manages file interactions.
- `llm`: `LanguageModelManager` - Manages interactions with the language model.
- `storage`: `StorageManager` - Manages storage operations.
- `conf`: `ConfType` - Configuration specific to the event.
- `config`: `ConfType` - Alias for `conf`.
- `cfg`: `ConfType` - Alias for `conf`.
- `last_ass_message`: `Message` - The last assistant message.
- `last_usr_message`: `Message` - The last user message.

#### Methods

- `clear() -> int`: Clears the messages.
- `pre_module_hook()`: Placeholder for pre-module actions.
- `post_module_hook()`: Saves the conversation history.
- `load_conversation_history() -> list[dict[str, Any]]`: Abstract method to load conversation history.
- `save_conversation_history() -> None`: Abstract method to save conversation history.
- `preprocess(content: str | None) -> str | None`: Preprocesses content before displaying it.
- `postprocess(content: str | None) -> str | None`: Postprocesses content after fetching it.
- `history() -> list[dict[str, Any]]`: Returns the entire conversation history.
- `truncated_history(cfg: ModuleConfig, system_message: str | None = None) -> list[dict[str, Any]]`: Returns the truncated conversation history.
- `last_user_question() -> str`: Returns the last user question.
- `add_assistant_message(content: str, func_calls: list[FunctionCall]) -> dict[str, Any]`: Adds an assistant message and returns it.
- `add_tool_message(tool_output: ToolOutput, func_call: FunctionCall) -> dict[str, Any]`: Adds a tool message and returns it.
- `notify(content: str, message_id: str | None = None) -> None`: Posts a notification for the user.
- `modify(content: str, message_id: str | None = None) -> None`: Modifies a message.
- `list() -> list[unique_sdk.Message]`: Lists messages and handles postprocessing.
- `reset() -> None`: Resets the state manager. Use it to clear the context, messages and tools. Context will however be reset based on the chat state.
- `fork() -> StateManager`: Forks the state manager. Use it from within a tool to create a new state manager with the same configuration and context and avoid side effects.

### StateManager

A concrete implementation of `StateManager` that fetches conversation history directly from the visible messages on the platform.

#### Methods

- `load_conversation_history() -> list[dict[str, Any]]`: Initializes the conversation history from the platform.
- `save_conversation_history() -> None`: Does not save the history.

### StateManager

An alternative state manager that fetches conversation history from visible messages and any tool calls stored in debug info fields.

#### Attributes

- `_key`: `str` - Key for storing tool calls in debug info.

#### Methods

- `load_conversation_history() -> list[dict[str, Any]]`: Initializes conversation history from the platform and debug info store.
- `save_conversation_history() -> None`: Saves the conversation history to the debug info store.

## Usage Example

```python
from your_module import StateManager, StateManager, StateManager
from blue_lugia.models import ExternalModuleChosenEvent

# Example event and configuration
event = ExternalModuleChosenEvent(...)
conf = YourConfigurationClass(...)

# Initialize the default state manager
state_manager = StateManager(event, conf)

# Load conversation history
history = state_manager.load_conversation_history()

# Add a new assistant message
state_manager.add_assistant_message("Hello, how can I help you today?", [])

# Save conversation history
state_manager.save_conversation_history()
