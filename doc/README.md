# Blue Lugia

For a concrete usage example, you can see the Petal external module or the upload_in_chat module.

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

[App](./app.md)

## StateManager

[StateManager](./state_manager.md)

## ModuleConfig

[ModuleConfig](./module_config.md)

## Managers

Managers allow you to interact with Unique environments.
They rely on method chaining to configure the final call to Unique APIs.

### Messages

[Messages](./managers/messages.md)

### LLM

[LanguageModelManager](./managers/llm.md)

### Files

[Files](./managers/files.md)

### Storage

[Storage](./managers/storage.md)

## Commands

If the config settings `ALLOW_COMMANDS` is set to a true value, the external module will route commands accordingly.

## Models

### Event

[Event](./models/event.md)

### Messages

[Messages](./models/messages.md)

### Files

[Files](./models/files.md)