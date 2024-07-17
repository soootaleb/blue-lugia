import contextlib
import json
import logging

import tiktoken
import unique_sdk
from openai import NotGiven

with contextlib.suppress(ImportError):
    from openai import OpenAI

from typing import Any, Callable, List, Literal, Tuple, Type

from pydantic import BaseModel

from blue_lugia.enums import Role
from blue_lugia.errors import LanguageModelManagerError, ParserError
from blue_lugia.managers.manager import Manager
from blue_lugia.models import Embedding, EmbeddingList, Message, MessageList


class LanguageModelManager(Manager):
    CONTEXT_WINDOW_SIZES = {
        "AZURE_GPT_4_0613": 8_192,
        "AZURE_GPT_4_0613_32K": 32_768,
        "AZURE_GPT_4_TURBO_1106": 128_000,
        "AZURE_GPT_4_TURBO_2024_0409": 128_000,
        "AZURE_GPT_35_TURBO_16K": 16_385,
        "AZURE_GPT_35_TURBO_0613": 4_096,
        "AZURE_GPT_4o_2024_0513": 128_000,
        "ptu-gpt-4o": 128_000,
        "pictet-ptu-gpt-4o": 128_000,
        "gpt-4": 8_192,
        "gpt-4o": 128_000,
        "gpt-4-turbo-2024-04-09": 128_000,
        "gpt-35-turbo": 16_385,
    }

    OUTPUT_MAX_TOKENS = {
        "AZURE_GPT_4_0613": 4_096,
        "AZURE_GPT_4_0613_32K": 4_096,
        "AZURE_GPT_4_TURBO_1106": 4_096,
        "AZURE_GPT_4_TURBO_2024_0409": 4_096,
        "AZURE_GPT_35_TURBO_16K": 4_096,
        "AZURE_GPT_35_TURBO_0613": 4_096,
        "AZURE_GPT_4o_2024_0513": 4_096,
        "ptu-gpt-4o": 4_096,
        "pictet-ptu-gpt-4o": 4_096,
        "gpt-4": 4_096,
        "gpt-4o": 4_096,
        "gpt-4-turbo-2024-04-09": 4_096,
        "gpt-35-turbo": 4_096,
    }

    AZURE_TO_CANONICAL_MODEL_NAME = {
        "AZURE_GPT_4_0613": "gpt-4",
        "AZURE_GPT_4_0613_32K": "gpt-4",
        "AZURE_GPT_4o_2024_0513": "gpt-4o",
        "AZURE_GPT_4_TURBO_1106": "gpt-4",
        "AZURE_GPT_4_TURBO_2024_0409": "gpt-4",
        "AZURE_GPT_35_TURBO_16K": "gpt-3.5-turbo",
        "AZURE_GPT_35_TURBO_0613": "gpt-3.5-turbo",
        "ptu-gpt-4o": "gpt-4o",
        "pictet-ptu-gpt-4o": "gpt-4o",
        "gpt-4": "gpt-4",
        "gpt-4o": "gpt-4o",
        "gpt-4-turbo-2024-04-09": "gpt-4",
        "gpt-35-turbo": "gpt-3.5-turbo",
    }

    _model: str
    _timeout: int
    _temperature: float

    _use_open_ai: bool
    _open_ai_api_key: str

    _parser: "Parser"

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        timeout: int = 600_000,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._temperature = temperature
        self._use_open_ai = False
        self._model = model
        self._timeout = timeout
        self._use_open_ai = False
        self._open_ai_api_key = ""
        self._parser = Parser(self)

    @property
    def tokenizer(self) -> tiktoken.Encoding:
        canonical_model_name = self.AZURE_TO_CANONICAL_MODEL_NAME.get(self._model, None)
        if not canonical_model_name:
            raise ValueError(f"BL::Manager::LLM::tokenizer::ModelNotSupported::{self._model}")
        else:
            return tiktoken.encoding_for_model(canonical_model_name)

    def _rm_titles(self, kv: dict[str, Any], prev_key: str = "") -> dict[str, Any]:
        new_kv = {}
        for k, v in kv.items():
            if k == "title":
                if isinstance(v, dict) and prev_key == "properties" and "title" in v:
                    new_kv[k] = self._rm_titles(v, k)
                else:
                    continue
            elif isinstance(v, dict):
                new_kv[k] = self._rm_titles(v, k)
            else:
                new_kv[k] = v
        return new_kv

    def _to_typed_messages(self, messages: List[dict[str, Any]] | List[Message]) -> MessageList:
        typed_messages = MessageList(
            [],
            tokenizer=self.tokenizer,
            logger=self.logger.getChild(MessageList.__name__),
        )

        for message in messages:
            if isinstance(message, dict):
                if "content" not in message and "text" not in message:
                    raise ValueError("BL::Manager::LLM::_to_typed_messages::MessageContentMissing")

                message_tool_calls = message.get("toolCalls", message.get("tool_calls", []))

                tool_calls = [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["function"]["name"],
                            "arguments": json.dumps(call["function"]["arguments"]),
                        },
                    }
                    for call in message_tool_calls
                ]

                typed_messages.append(
                    Message(
                        role=Role(message["role"].lower()),
                        content=message["content"] or message.get("text", ""),
                        logger=self.logger.getChild(Message.__name__),
                        tool_calls=tool_calls,
                        tool_call_id=message.get("toolCallId", message.get("tool_call_id")),
                    )
                )
            elif isinstance(message, Message):
                typed_messages.append(message)
            else:
                raise ValueError(f"BL::Manager::LLM::_to_typed_messages::InvalidMessageType::{type(message)}")

        return typed_messages

    @property
    def parser(self) -> "Parser":
        return Parser(self)

    def oai(self, key: str) -> "LanguageModelManager":
        llm = self.fork()
        llm._use_open_ai = True
        llm._open_ai_api_key = key
        return llm

    def using(self, model: str) -> "LanguageModelManager":
        llm = self.fork()
        llm._model = model
        return llm

    def fork(self) -> "LanguageModelManager":
        llm = self.__class__(event=self._event, model=self._model, temperature=self._temperature, timeout=self._timeout, logger=self.logger)
        llm._use_open_ai = self._use_open_ai
        llm._open_ai_api_key = self._open_ai_api_key
        return llm

    def _to_dict_messages(self, messages: List[Message] | List[dict], oai: bool = False) -> List[dict]:
        formated_messages = []

        for message in messages:
            if isinstance(message, Message):
                message_to_append = {
                    "role": message.role.value,
                    "content": message.content or "",
                }

                if message.tool_calls:
                    key = "tool_calls" if oai else "toolCalls"
                    message_to_append[key] = [
                        {
                            "id": call["id"],
                            "type": "function",
                            "function": {
                                "name": call["function"]["name"],
                                "arguments": json.dumps(call["function"]["arguments"]),
                            },
                        }
                        for call in message.tool_calls
                    ]

                if message.tool_call_id:
                    key = "tool_call_id" if oai else "toolCallId"
                    message_to_append[key] = message.tool_call_id

                formated_messages.append(message_to_append)

            else:
                formated_messages.append(message)

        return formated_messages

    def embed(self, messages: List[Message] | List[dict] | str | List[str]) -> EmbeddingList:
        texts = []

        flat_messages = messages if isinstance(messages, list) else [messages]

        for m in flat_messages:
            if isinstance(messages, Message):
                texts.append(messages.content)
            elif isinstance(messages, dict):
                dict_content = messages.get("content", messages.get("text", ""))
                if not dict_content:
                    self.logger.warning("BL::Manager::LLM::embed::EmptyMessageContent::UsingEmptyString")
                texts.append(dict_content)
            elif isinstance(messages, str):
                texts.append(messages)
            else:
                self.logger.warning("BL::Manager::LLM::embed::InvalidMessageType::UsingStrCastedString")
                texts.append(str(messages))

        embeddings = unique_sdk.Embeddings.create(
            user_id=self._event.user_id,
            company_id=self._event.company_id,
            texts=texts,
        )

        typed_embeddings = [Embedding(embedding, logger=self.logger.getChild(Embedding.__name__)) for embedding in embeddings.embeddings]

        return EmbeddingList(typed_embeddings, logger=self.logger.getChild(EmbeddingList.__name__))

    def _reformat(self, messages: MessageList) -> MessageList:
        """
        Will
        - extract system messages
        - deduplicate system messages by content
        - merge them in one system message
        - put it on top of the input messages

        Besides, this method truncates the input messages to fit the model's input size.
        It makes sure the system messages are not truncated.

        TODO: Count also tools and leave some space for the output of the model
        """
        self.logger.debug("Reformating context messages.")

        system_messages = messages.filter(lambda m: m.role == Role.SYSTEM)
        not_system_messages = messages.filter(lambda m: m.role != Role.SYSTEM)

        unique_system_messages = MessageList([], tokenizer=self.tokenizer, logger=self.logger.getChild(MessageList.__name__))

        # deduplicate system messages by content

        for message in system_messages:
            if message.content and not unique_system_messages.first(lambda m: str(m.content) == str(message.content)):
                unique_system_messages.append(message)

        system_tokens_count = len(unique_system_messages.tokens)

        self.logger.debug(f"Found {system_tokens_count} tokens of system messages.")

        # count tokens from system messages

        input_tokens_limit = self.CONTEXT_WINDOW_SIZES.get(self._model, 0) - self.OUTPUT_MAX_TOKENS.get(self._model, 0) - system_tokens_count

        if input_tokens_limit <= 0:
            raise ValueError(f"BL::Manager::LLM::complete::input_tokens_limit::{input_tokens_limit}")

        self.logger.debug(f"BL::Manager::LLM::complete::NonSystemMessagesTruncatedTo::{input_tokens_limit} tokens")

        not_system_messages = not_system_messages.keep(input_tokens_limit)

        # prepend system messages to input messages

        if unique_system_messages:
            not_system_messages.insert(
                0,
                Message.SYSTEM(
                    "\n".join([str(m.content) for m in unique_system_messages]),
                ),
            )

        self.logger.debug(f"BL::Manager::LLM::complete::MessagesReformatedTo::{len(not_system_messages.tokens)} tokens.")

        return not_system_messages

    def _verify_tools(self, tools: List[type[BaseModel]]) -> List[type[BaseModel]]:
        # must inherit base model
        for tool in tools:
            if not issubclass(tool, BaseModel):
                raise LanguageModelManagerError(f"BL::Manager::LLM::complete::InvalidToolBaseClass::{tool}")

        # tool name must be under or equal to 64 chars
        for tool in tools:
            if len(tool.__name__) > 64:
                raise LanguageModelManagerError(f"BL::Manager::LLM::complete::ToolNameTooLong::{tool}")

        # maximum of 128 tools
        if len(tools) > 128:
            raise LanguageModelManagerError(f"BL::Manager::LLM::complete::TooManyTools::{len(tools)}")
        elif len(tools) >= 10:
            self.logger.warning(f"BL::Manager::LLM::complete::TooManyTools::{len(tools)}")

        # tool description must be under or equal to 1024 chars
        for tool in tools:
            if tool.__doc__ and len(tool.__doc__) > 1024:
                raise LanguageModelManagerError(f"BL::Manager::LLM::complete::ToolDescriptionTooLong::{tool}")

        return tools

    def complete(
        self,
        messages: List[Message] | List[dict[str, Any]],
        tools: List[type[BaseModel]] | None = None,
        tool_choice: type[BaseModel] | None = None,
        max_tokens: int | Literal["auto"] | None = None,
        out: Message | None = None,
        search_context: List[unique_sdk.Integrated.SearchResult] = [],
        debug_info: dict[str, Any] | None = None,
        start_text: str = "",
        *args,
        **kwargs,
    ) -> Message:
        """
        Completes a communication or operation sequence by processing input messages and optionally using tools to generate or refine responses.

        This method orchestrates various components like message processing, tool interactions, and external API calls to generate a completed message based on input parameters
        and internal configurations.

        Args:
            messages (List[Message] | List[dict[str, Any]]): The list of messages or structured message data to process.
            tools (List[type[BaseModel]] | None): Optional list of tools (as model classes) to apply during the completion process.
            tool_choice (type[BaseModel] | None): Specific tool (model class) selected for applying in the completion process.
            max_tokens (int | Literal["auto"] | None): The maximum number of tokens to generate or process; 'auto' for automatic determination based on context.
            out (Message | None): Optional existing message object to update with the completion result.
            search_context (List[unique_sdk.Integrated.SearchResult]): Contextual data for search or reference during the completion.
            debug_info (dict[str, Any] | None): Additional debug information to pass through or generate during the process.
            start_text (str): Initial text to prepend to any generated content, setting the context or continuation tone.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Message: The completed message after processing, including any new content, tool interactions, and updates to existing messages.

        Raises:
            MessageFormatError: If there are issues with the message formatting or invalid roles.
            MessageRemoteError: For operations requiring a remote but none is available.

        Detailed explanation:
            The method handles a complex flow of data transformations and API interactions, starting from raw or semi-structured message inputs, applying tools as specified,
            and culminating in a synthesized output that may be a new message or an update to an existing one.
            It intelligently handles token limits, tool applications, and external integrations (e.g., OpenAI or unique_sdk integrations) based on
            the provided configurations and runtime conditions.
        """
        if debug_info is None:
            debug_info = {}

        options: dict[str, Any] = {
            "temperature": self._temperature,
        }

        if tools:
            options["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.__name__,
                        "description": tool.__doc__ or "",
                        "parameters": self._rm_titles(tool.model_json_schema()),
                    },
                }
                for tool in self._verify_tools(tools)
            ]

        typed_messages = self._to_typed_messages(messages)  # Returns a MessageList with the correct LLM tokenization

        context = self._reformat(typed_messages)

        formated_messages = self._to_dict_messages(context, oai=self._use_open_ai)

        if tool_choice:
            options["toolChoice"] = {
                "type": "function",
                "function": {"name": tool_choice.__name__},
            }

        if max_tokens is not None:
            options["maxTokens"] = max_tokens

        self.logger.debug(f"BL::Manager::LLM::complete::Model::{self._model}")

        if self._use_open_ai:
            client = OpenAI(api_key=self._open_ai_api_key)
            completion = client.chat.completions.create(
                model=self._model,
                messages=formated_messages,  # type: ignore
                tools=options.get("tools", NotGiven()),
                tool_choice=options.get("toolChoice", NotGiven()),
                max_tokens=options.get("max_tokens", NotGiven()),
                temperature=self._temperature,
            )

            return Message(
                role=Role(completion.choices[0].message.role.lower()),
                content=completion.choices[0].message.content,
                tool_calls=[
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": json.loads(call.function.arguments),
                        },
                    }
                    for call in completion.choices[0].message.tool_calls or []
                ],
                logger=self.logger.getChild(Message.__name__),
            )
        else:
            if out:
                completion = unique_sdk.Integrated.chat_stream_completion(
                    user_id=self._event.user_id,
                    company_id=self._event.company_id,
                    assistantId=self._event.payload.assistant_id,
                    assistantMessageId=out.id,
                    userMessageId=self._event.payload.user_message.id,
                    messages=formated_messages,
                    chatId=self._event.payload.chat_id,
                    searchContext=search_context,
                    debugInfo=debug_info,
                    startText=start_text,
                    model=self._model,
                    timeout=self._timeout,
                    options=options,  # type: ignore
                    temperature=self._temperature,
                )

                out.content = completion.message.text

                out_tool_calls_ids = [call["id"] for call in out._tool_calls]
                out._tool_calls = out._tool_calls + [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.loads(call.arguments),
                        },
                    }
                    for call in completion.toolCalls
                    if call.id not in out_tool_calls_ids
                ]

                return Message(
                    role=Role(completion.message.role.lower()),
                    content=(Message._Content(completion.message.text) if completion.message.text else None),
                    remote=Message._Remote(
                        event=self._event,
                        id=completion.message.id,
                        debug=completion.message.debugInfo,
                    ),
                    tool_calls=[
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.loads(call.arguments),
                            },
                        }
                        for call in completion.toolCalls
                    ],
                    logger=self.logger.getChild(Message.__name__),
                )

            else:
                completion = unique_sdk.ChatCompletion.create(
                    company_id=self._event.company_id,
                    model=self._model,
                    messages=formated_messages,
                    timeout=self._timeout,
                    options=options,  # type: ignore
                )

                return Message(
                    role=Role(completion.choices[0].message.role.lower()),
                    content=completion.choices[0].message.content,
                    tool_calls=[
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": json.loads(call.function.arguments),
                            },
                        }
                        for call in completion.choices[0].message.toolCalls
                    ],
                    logger=self.logger.getChild(Message.__name__),
                )


class Parser[T]:
    _llm: LanguageModelManager
    _schema: Type[BaseModel]
    _assertions: List[Tuple[Callable[[dict], bool], str] | Callable[[dict], bool]]
    _instructions: MessageList

    _logger: logging.Logger

    def __init__(self, llm: LanguageModelManager) -> None:
        self._logger = llm.logger.getChild(Parser.__name__)
        self._llm = llm
        self._instructions = MessageList([], tokenizer=llm.tokenizer, logger=self._logger.getChild(MessageList.__name__))
        self._assertions = []
        self._schema = BaseModel

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def into(self, schema: type[BaseModel]) -> "Parser":
        self._schema = schema
        return self

    def following(
        self,
        instructions: Message | MessageList,
    ) -> "Parser":
        if isinstance(instructions, Message):
            self._instructions = MessageList([instructions], tokenizer=self._llm.tokenizer, logger=self._logger)
        else:
            self._instructions = instructions
        return self

    def asserting(
        self,
        assertions: List[Tuple[Callable[[dict], bool], str] | Callable[[dict], bool]],
    ) -> "Parser":
        self._assertions = assertions
        return self

    def parse(self, query: Message) -> BaseModel:
        llm = self._llm

        completion = llm.complete(
            [
                *self._instructions,
                query,
            ],
            tools=[self._schema],
            tool_choice=self._schema,
        )

        try:
            args = completion.tool_calls[0]["function"]["arguments"]

            for assert_arg in self._assertions:
                if isinstance(assert_arg, tuple):
                    assert assert_arg[0](args), assert_arg[1]
                else:
                    assert assert_arg(args), "Assertion failed."

            return self._schema(**args)  # type: ignore
        except AssertionError as e:
            raise e
        except Exception:
            raise ParserError("BL::Parser::parse::Error parsing the user message.")
