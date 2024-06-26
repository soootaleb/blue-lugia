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