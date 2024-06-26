# ModuleConfig Documentation

## Overview

The `ModuleConfig` class is a configuration dataclass used for setting up the language model and other related configurations for the assistant. It provides methods to create a configuration from a dictionary or an event and to convert the configuration back to a dictionary.

## Class: ModuleConfig

A dataclass for managing the configuration settings of the language model and related functionalities.

### Attributes

- `languageModel`: `str` - The top-level language model for the assistant. Default is `"AZURE_GPT_4_TURBO_2024_0409"`.
- `ALLOW_COMMANDS`: `str | bool | None` - Configuration for allowing commands. Default is `None`.
- `ON_FAILURE_MESSAGE_OVERRIDE`: `str | None` - Message override on failure. Default is `None`.
- `ON_FAILURE_DISPLAY_ERROR`: `str | bool | None` - Configuration for displaying error on failure. Default is `None`.
- `CONTEXT_WINDOW_TOKEN_LIMIT`: `int` - Token limit for the context window. Default is `16,000`.
- `CONTEXT_WINDOW_N_MIN_MESSAGES`: `int` - Minimum number of messages in the context window. Default is `2`.
- `CONTEXT_WINDOW_N_MAX_MESSAGES`: `int` - Maximum number of messages in the context window. Default is `10`.
- `INSERT_TRUNCATION_MESSAGE`: `bool` - Whether to insert a truncation message. Default is `True`.
- `FUNCTION_CALL_MAX_ITERATIONS`: `int` - Maximum number of iterations for function calls. Default is `5`.
- `ON_FAILURE`: `str` - Default failure message. Default is `"Sorry, I was unable to resolve your request. Please try rephrasing your question or asking another question. If this message persists, you may try starting a new conversation."`.

### Methods

- `from_dict(data: dict[str, Any]) -> ModuleConfig`: Class method to create a `ModuleConfig` instance from a dictionary. Filters out any keys that are not in the constructor.
- `from_event(event: ExternalModuleChosenEvent) -> ModuleConfig`: Class method to create a `ModuleConfig` instance from an `ExternalModuleChosenEvent`.
- `to_dict() -> dict[str, Any]`: Converts the `ModuleConfig` instance to a dictionary.

## Usage Example

```python
from your_module import ModuleConfig
from your_module.schemas import ExternalModuleChosenEvent

# Example dictionary configuration
config_dict = {
    "languageModel": "AZURE_GPT_4_TURBO_2024_0409",
    "ALLOW_COMMANDS": True,
    "CONTEXT_WINDOW_TOKEN_LIMIT": 8000
}

# Create ModuleConfig from dictionary
config = ModuleConfig.from_dict(config_dict)

# Create ModuleConfig from event
event = ExternalModuleChosenEvent(payload={"configuration": config_dict})
config_from_event = ModuleConfig.from_event(event)

# Convert ModuleConfig to dictionary
config_as_dict = config.to_dict()
