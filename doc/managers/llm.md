# LanguageModelManager

## Overview
`LanguageModelManager` is a class that facilitates interaction with various language models, supporting multiple configurations, tokenization, embedding, and response generation. It abstracts underlying model complexities, offering functionalities such as:

- Tokenization handling
- Context window size management
- Model registration and selection
- Message formatting and reformatting
- Tool integration and execution
- Streaming and non-streaming completions
- Embedding generation

## Class Definition
```python
class LanguageModelManager(Manager)
```
This class extends `Manager` and provides functionalities for managing and interfacing with language models.

## Attributes

### Static Attributes
- `DEV_MESSAGE_MODELS`: List of models using developer-specific message formats.
- `CONTEXT_WINDOW_SIZES`: Dictionary mapping model names to their respective context window sizes.
- `OUTPUT_MAX_TOKENS`: Dictionary mapping model names to their maximum output token limits.
- `AZURE_TO_CANONICAL_MODEL_NAME`: Mapping between Azure model names and their canonical names.

### Instance Attributes
- `_model` (str): The model in use.
- `_seed` (int | None): Seed for randomization.
- `_timeout` (int): Timeout for model interactions.
- `_temperature` (float): Temperature for response generation.
- `_context_max_tokens` (int | None): Maximum context tokens.
- `_use_open_ai` (bool): Whether OpenAI API is used.
- `_open_ai_api_key` (str): API key for OpenAI.
- `_streaming_allowed` (bool): Whether streaming responses are allowed.

## Methods

### Initialization
```python
__init__(
    self,
    model: str,
    temperature: float = 0.0,
    timeout: int = 600_000,
    context_max_tokens: int | None = None,
    seed: int | None = None,
    streaming_allowed: bool = True,
    **kwargs,
) -> None
```
Initializes an instance of `LanguageModelManager` with the specified model and configurations.

### Properties
```python
@property
def tokenizer(self) -> tiktoken.Encoding
```
Returns the tokenizer associated with the current model.

```python
@property
def models(self) -> dict[str, Any]
```
Returns metadata of supported models.

```python
@property
def models_names(self) -> list[str]
```
Returns a list of available model names.

### Message Handling
```python
def _to_typed_messages(self, messages: list[dict[str, Any]] | list[Message]) -> MessageList
```
Converts raw messages to `MessageList` with appropriate typing.

```python
def _to_dict_messages(self, messages: list[Message] | list[dict], oai: bool = False) -> list[dict]
```
Formats messages for API consumption.

```python
def _reformat(self, messages: MessageList) -> MessageList
```
Processes messages by deduplicating system messages, truncating context to fit model constraints, and removing empty messages.

```python
def _rereference(self, messages: MessageList) -> tuple[MessageList, list, list]
```
Handles message citations and source references.

### Model Configuration
```python
def register(self, model: str, input_max_tokens: int, output_max_tokens: int, canonical_name: str, uses_dev_messages: bool = False, in_place: bool = False) -> "LanguageModelManager"
```
Registers a new model with specified parameters.

```python
def fork(self) -> "LanguageModelManager"
```
Creates a copy of the current `LanguageModelManager` instance.

### Model Interaction
```python
def complete(
    self,
    messages: list[Message] | list[dict[str, Any]],
    tools: list[type[BaseModel]] | None = None,
    tool_choice: type[BaseModel] | None = None,
    schema: type[BaseModel] | None = None,
    max_tokens: int | Literal["auto"] | None = None,
    out: Message | None = None,
    debug_info: dict[str, Any] | None = None,
    start_text: str = "",
    output_json: bool = False,
    completion_name: str = "",
    search_context: list | None = None,
    raise_on_empty_completion: type[Exception] | None = None,
    *args,
    **kwargs,
) -> Message
```
Processes and completes a set of input messages using the configured model.

```python
def parse(self, message_or_messages: Message | list[Message] | list[dict[str, Any]], into: type[ToolType], completion_name: str = "") -> ToolType
```
Parses messages into a structured tool output.

### Streaming and Tool Handling
```python
def prevent_streaming(self) -> "LanguageModelManager"
```
Disables streaming responses.

```python
def allow_streaming(self) -> "LanguageModelManager"
```
Enables streaming responses.

```python
def _verify_tools(self, tools: list[type[BaseModel]]) -> list[type[BaseModel]]
```
Validates the list of tools to be used in message processing.

## Usage Examples

### Simple Completion
```python
response = state.llm.complete(messages=[{"role": "user", "content": "Hello!"}])
print(response.content)
```

### Streaming Completion
```python
out_message = Message(role="assistant", content="")
state.llm.complete(messages=[{"role": "user", "content": "Tell me a story."}], out=out_message)
print(out_message.content)
```

### Registering a New Model
```python
state.llm.register("custom-gpt", input_max_tokens=2048, output_max_tokens=512, canonical_name="gpt-4")
```

### Registering the Latest Models
```python
state.llm.register("AZURE_GPT_o1_2024_1217", input_max_tokens=200_000, output_max_tokens=100_000, canonical_name="gpt-o1", uses_dev_messages=True)
```

> The latest model use a "developer" role instead of a "system" role. You can tune this with the uses_dev_messages arguments. Source: [OpenAI Changelog](https://platform.openai.com/docs/changelog)

### Changing Model Configuration
```python
state.llm = state.llm.using("gpt-4-turbo").tmp(temperature=0.7).seed(42)
```

### Disabling and Enabling Streaming
```python
state.llm = state.llm.prevent_streaming()
state.llm = state.llm.allow_streaming()
```

## Exception Handling
- `LanguageModelManagerError`: Raised for general errors.
- `ValueError`: Raised when an unsupported model is specified.

## Dependencies
- `tiktoken`
- `unique_sdk`
- `pydantic`
- `openai`
- `blue_lugia` modules

## Conclusion
The `LanguageModelManager` class provides a robust and extensible interface for interacting with language models. It abstracts complexities while allowing fine-grained control over model behaviors, making it suitable for production-level deployments requiring advanced language processing capabilities.

