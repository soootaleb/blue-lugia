import contextlib
import json
import re
import xml.etree.ElementTree as ET  # noqa: N817

import tiktoken
import unique_sdk
from openai import NotGiven

with contextlib.suppress(ImportError):
    from openai import OpenAI

from typing import Any, List, Literal, Tuple, TypeVar

from pydantic import BaseModel

from blue_lugia.enums import Role
from blue_lugia.errors import LanguageModelManagerError
from blue_lugia.managers.manager import Manager
from blue_lugia.models import Embedding, EmbeddingList, Message, MessageList

ToolType = TypeVar("ToolType", bound=BaseModel)


class LanguageModelManager(Manager):
    CONTEXT_WINDOW_SIZES = {
        "AZURE_GPT_4_0613": 8_192,
        "AZURE_GPT_4_0613_32K": 32_768,
        "AZURE_GPT_4_TURBO_1106": 128_000,
        "AZURE_GPT_4_TURBO_2024_0409": 128_000,
        "AZURE_GPT_35_TURBO_16K": 16_385,
        "AZURE_GPT_35_TURBO_0613": 4_096,
        "AZURE_GPT_4o_2024_0513": 128_000,
        "AZURE_GPT_4o_2024_0806": 128_000,
        "ptu-gpt-4o": 128_000,
        "pictet-ptu-gpt-4o": 128_000,
        "gpt-4": 8_192,
        "gpt-4o": 128_000,
        "gpt-4o-mini": 128_000,
        "gpt-4o-2024-08-06": 128_000,
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
        "AZURE_GPT_4o_2024_0806": 16_384,
        "ptu-gpt-4o": 4_096,
        "pictet-ptu-gpt-4o": 4_096,
        "gpt-4": 4_096,
        "gpt-4o": 4_096,
        "gpt-4o-mini": 16_384,
        "gpt-4o-2024-08-06": 16_384,
        "gpt-4-turbo-2024-04-09": 4_096,
        "gpt-35-turbo": 4_096,
    }

    AZURE_TO_CANONICAL_MODEL_NAME = {
        "AZURE_GPT_4_0613": "gpt-4",
        "AZURE_GPT_4_0613_32K": "gpt-4",
        "AZURE_GPT_4o_2024_0513": "gpt-4o",
        "AZURE_GPT_4o_2024_0806": "gpt-4o",
        "AZURE_GPT_4_TURBO_1106": "gpt-4",
        "AZURE_GPT_4_TURBO_2024_0409": "gpt-4",
        "AZURE_GPT_35_TURBO_16K": "gpt-3.5-turbo",
        "AZURE_GPT_35_TURBO_0613": "gpt-3.5-turbo",
        "ptu-gpt-4o": "gpt-4o",
        "pictet-ptu-gpt-4o": "gpt-4o",
        "gpt-4": "gpt-4",
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o",
        "gpt-4o-2024-08-06": "gpt-4o",
        "gpt-4-turbo-2024-04-09": "gpt-4",
        "gpt-35-turbo": "gpt-3.5-turbo",
    }

    _model: str
    _seed: int | None
    _timeout: int
    _temperature: float
    _context_max_tokens: int | None

    _use_open_ai: bool
    _open_ai_api_key: str

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        timeout: int = 600_000,
        context_max_tokens: int | None = None,
        seed: int | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._temperature = temperature
        self._use_open_ai = False
        self._model = model
        self._seed = seed
        self._timeout = timeout
        self._use_open_ai = False
        self._open_ai_api_key = ""
        self._context_max_tokens = context_max_tokens

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
                            "arguments": json.dumps(call["function"]["arguments"], ensure_ascii=False),
                        },
                    }
                    for call in message_tool_calls
                ]

                typed_messages.append(
                    Message(
                        role=Role(message["role"].lower()),
                        content=message["content"] or message.get("text", ""),
                        sources=message.get("sources", []),
                        citations=message.get("citations", {}),
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

    def oai(self, key: str) -> "LanguageModelManager":
        llm = self.fork()
        llm._use_open_ai = True
        llm._open_ai_api_key = key
        return llm

    def using(self, model: str) -> "LanguageModelManager":
        llm = self.fork()
        llm._model = model
        return llm

    def seed(self, seed: int) -> "LanguageModelManager":
        llm = self.fork()
        llm._seed = seed
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
                    "content": message.original_content or message.content or "",
                }

                if message.tool_calls:
                    key = "tool_calls" if oai else "toolCalls"
                    message_to_append[key] = [
                        {
                            "id": call["id"],
                            "type": "function",
                            "function": {
                                "name": call["function"]["name"],
                                "arguments": json.dumps(call["function"]["arguments"], ensure_ascii=False),
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
        """
        self.logger.debug(f"BL::Manager::LLM::reformat::Reformating {len(messages)} messages")

        system_messages = messages.filter(lambda m: m.role == Role.SYSTEM)
        not_system_messages = messages.filter(lambda m: m.role != Role.SYSTEM)

        unique_system_messages = MessageList([], tokenizer=self.tokenizer, logger=self.logger.getChild(MessageList.__name__))

        # deduplicate system messages by content
        for message in system_messages:
            if message.content and not unique_system_messages.first(lambda m: str(m.content) == str(message.content)):
                unique_system_messages.append(message)

        system_tokens_count = len(unique_system_messages.tokens)

        self.logger.debug(f"BL::Manager::LLM::reformat::SystemMessageTokensFound::{system_tokens_count}")

        context_window = self.CONTEXT_WINDOW_SIZES.get(self._model, 0)

        if self._context_max_tokens:
            if self._context_max_tokens <= context_window:
                context_window = self._context_max_tokens
            else:
                self.logger.warning(f"BL::Manager::LLM::reformat::ContextMaxTokensExceedsModelLimit::{self._context_max_tokens}")

        self.logger.debug(f"BL::Manager::LLM::reformat::ContextMaxTokensSet::{self._context_max_tokens}")

        history_tokens_limit = context_window - self.OUTPUT_MAX_TOKENS.get(self._model, 0) - system_tokens_count

        if history_tokens_limit <= 0:
            raise ValueError(f"BL::Manager::LLM::reformat::input_tokens_limit::{history_tokens_limit}")

        self.logger.debug(f"BL::Manager::LLM::reformat::NonSystemMessagesTruncatedTo::{history_tokens_limit} tokens")

        final_history = not_system_messages.truncate(history_tokens_limit)

        if unique_system_messages:
            final_history.insert(
                0,
                Message.SYSTEM(
                    "\n".join([str(m.content) for m in unique_system_messages]),
                ),
            )

        self.logger.debug(f"BL::Manager::LLM::reformat::ContextTruncatedTo::{len(final_history.tokens)} tokens.")

        return final_history

    def _rereference(self, messages: MessageList) -> Tuple[MessageList, List[unique_sdk.Integrated.SearchResult], List[unique_sdk.Integrated.SearchResult]]:
        processed_messages = messages.fork()
        references = []

        found_sources_counter = 0

        for index, message in enumerate(processed_messages):
            sources = re.findall(r"<source\d+[^>]*>.*?</source\d+>", message.content or "", re.DOTALL)

            for source in sources:
                elem = ET.fromstring(source)
                elem.tag = f"source{found_sources_counter}"

                if message.content:
                    message.content = message.content.replace(source, ET.tostring(elem, encoding="unicode"))

                    if message.original_content:
                        message.original_content = message.original_content.replace(source, ET.tostring(elem, encoding="unicode"))

                if found_sources_counter >= len(messages.sources):
                    references.append(
                        unique_sdk.Integrated.SearchResult(
                            id=elem.get("id", f"source_{found_sources_counter}"),
                            chunkId=elem.get("chunkId", elem.get("id", f"source_{found_sources_counter}")),
                            key=elem.get("label", elem.get("display", elem.get("key", elem.get("title", f"source_{found_sources_counter}")))),
                            url=elem.get("url", f'unique://content/{elem.get("id", f"source_{found_sources_counter}")}'),
                        )
                    )

                found_sources_counter += 1

            if message.role == Role.USER:
                references.extend(message.sources)

            messages_before_current = MessageList(messages[:index], tokenizer=self.tokenizer, logger=self.logger.getChild(MessageList.__name__))
            references_index = len(messages_before_current.sources) if message.sources else 0

            for citation in message.citations:
                citation_number = int(re.findall(r"\d+", citation)[0])
                message.original_content = message.original_content.replace(citation, f"[source{references_index + citation_number}]")

        return processed_messages, messages.sources, references

    def _verify_tools(self, tools: List[type[BaseModel]]) -> List[type[BaseModel]]:
        # must inherit base model
        for tool in tools:
            if not issubclass(tool, BaseModel):
                raise LanguageModelManagerError(f"BL::Manager::LLM::verify_tools::InvalidToolBaseClass::{tool}")

        # tool name must be under or equal to 64 chars
        for tool in tools:
            if len(tool.__name__) > 64:
                raise LanguageModelManagerError(f"BL::Manager::LLM::verify_tools::ToolNameTooLong::{tool}")

        # maximum of 128 tools
        if len(tools) > 128:
            raise LanguageModelManagerError(f"BL::Manager::LLM::verify_tools::TooManyTools::{len(tools)}")
        elif len(tools) >= 10:
            self.logger.warning(f"BL::Manager::LLM::verify_tools::TooManyTools::{len(tools)}")

        # tool description must be under or equal to 1024 chars
        for tool in tools:
            if tool.__doc__ and len(tool.__doc__) > 1024:
                raise LanguageModelManagerError(f"BL::Manager::LLM::verify_tools::ToolDescriptionTooLong::{tool}")

        return tools

    def _complete_openai(
        self,
        formated_messages: List[dict],
        options: dict[str, Any],
        references: Tuple[List[unique_sdk.Integrated.SearchResult], List[unique_sdk.Integrated.SearchResult]],
        completion_name: str = "",
    ) -> Message:
        existing_references, new_references = references

        search_context = existing_references + new_references

        self.logger.debug(f"BL::Manager::LLM::complete({completion_name})::streaming::SearchContext::{len(search_context)}")

        client = OpenAI(api_key=self._open_ai_api_key)
        completion = client.chat.completions.create(
            model=self._model,
            messages=formated_messages,  # type: ignore
            tools=options.get("tools", NotGiven()),
            tool_choice=options.get("toolChoice", NotGiven()),
            max_tokens=options.get("max_tokens", NotGiven()),
            response_format=options.get("response_format", NotGiven()),
            temperature=self._temperature,
        )

        completion_sources = re.findall(r"\[source\d+\]", completion.choices[0].message.content or "", re.DOTALL)
        debug_sources = {}
        source_index = 1
        for source in completion_sources:
            if source not in debug_sources:
                debug_sources[source] = source_index
                source_index += 1

        return Message(
            role=Role(completion.choices[0].message.role.lower()),
            content=completion.choices[0].message.content,
            sources=new_references,
            citations=debug_sources,
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

    def _complete_streaming(
        self,
        formated_messages: List[dict],
        options: dict[str, Any],
        out: Message,
        debug_info: dict[str, Any],
        start_text: str,
        references: Tuple[List[unique_sdk.Integrated.SearchResult], List[unique_sdk.Integrated.SearchResult]],
        completion_name: str = "",
        search_context: List[unique_sdk.Integrated.SearchResult] | None = None,
    ) -> Message:
        existing_references, new_references = references

        search_context = search_context or (existing_references + new_references)

        self.logger.debug(f"BL::Manager::LLM::complete({completion_name})::streaming::SearchContext::{len(search_context)}")

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

        completion_sources = re.findall(r"\[source\d+\]", completion.message.originalText or "", re.DOTALL)
        debug_sources = {}
        source_index = 1
        for source in completion_sources:
            if source not in debug_sources:
                debug_sources[source] = source_index
                source_index += 1

        out.content = completion.message.text
        out.original_content = completion.message.originalText
        out._sources = new_references
        out._citations = debug_sources
        out.debug["_sources"] = new_references
        out.debug["_citations"] = debug_sources

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
            if call.id not in [call["id"] for call in out._tool_calls]
        ]

        typed_message = Message(
            role=Role(completion.message.role.lower()),
            content=(Message._Content(completion.message.text) if completion.message.text else None),
            original_content=completion.message.originalText,
            sources=new_references,
            citations=debug_sources,
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

        typed_message.update(debug={"_sources": new_references, "_citations": debug_sources})

        return typed_message

    def _complete_basic(
        self,
        formated_messages: List[dict],
        references: Tuple[List[unique_sdk.Integrated.SearchResult], List[unique_sdk.Integrated.SearchResult]],
        options: dict[str, Any],
        completion_name: str = "",
        search_context: List[unique_sdk.Integrated.SearchResult] | None = None,
    ) -> Message:
        existing_references, new_references = references

        search_context = search_context or (existing_references + new_references)

        self.logger.debug(f"BL::Manager::LLM::complete({completion_name})::basic::SearchContext::{len(search_context)}")

        completion = unique_sdk.ChatCompletion.create(
            company_id=self._event.company_id,
            model=self._model,
            messages=formated_messages,
            timeout=self._timeout,
            options=options,  # type: ignore
        )

        completion_sources = re.findall(r"\[source\d+\]", completion.choices[0].message.content or "", re.DOTALL)
        debug_sources = {}
        source_index = 1
        for source in completion_sources:
            if source not in debug_sources:
                debug_sources[source] = source_index
                source_index += 1

        return Message(
            role=Role(completion.choices[0].message.role.lower()),
            content=completion.choices[0].message.content,
            citations=debug_sources,
            sources=new_references,
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

    def _build_options(
        self,
        formated_messages: List[dict],
        tools: List[type[BaseModel]] | None = None,
        tool_choice: type[BaseModel] | None = None,
        schema: type[BaseModel] | None = None,
        max_tokens: int | Literal["auto"] | None = None,
        output_json: bool = False,
        completion_name: str = "",
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "temperature": self._temperature,
        }

        if self._seed is not None:
            options["seed"] = self._seed

        if tools:
            options["tools"] = []

            for tool in self._verify_tools(tools):
                tool_config = getattr(tool, "Config", None)
                tool_config_strict = getattr(tool_config, "bl_fc_strict", True)

                options["tools"].append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.__name__,
                            "strict": tool_config_strict,
                            "description": tool.__doc__ or "",
                            "parameters": self._rm_titles(tool.model_json_schema()),
                        },
                    }
                )

        if tool_choice:
            options["toolChoice"] = {
                "type": "function",
                "function": {"name": tool_choice.__name__},
            }

        if max_tokens is not None:
            options["maxTokens"] = max_tokens

        if output_json:
            messages_contents = "\n".join([message["content"].lower() for message in formated_messages])

            if "json" in messages_contents:
                options["response_format"] = {"type": "json_object"}
            else:
                raise LanguageModelManagerError(
                    f"BL::Manager::LLM::complete({completion_name})::JSONPromptMissing::The word 'json' must be present in the messages when you use the output_json flag."
                )

        if schema:
            bl_schema_config = getattr(schema, "Config", None)
            bl_schema_strict = getattr(bl_schema_config, "bl_schema_strict", True)

            if bl_schema_strict:
                schema.model_config["extra"] = "forbid"

            json_schema = {"name": schema.__name__, "strict": bl_schema_strict, "schema": self._rm_titles(schema.model_json_schema())}

            options["response_format"] = {
                "type": "json_schema",
                "json_schema": json_schema,
            }

        return options

    def complete(
        self,
        messages: List[Message] | List[dict[str, Any]],
        tools: List[type[BaseModel]] | None = None,
        tool_choice: type[BaseModel] | None = None,
        schema: type[BaseModel] | None = None,
        max_tokens: int | Literal["auto"] | None = None,
        out: Message | None = None,
        debug_info: dict[str, Any] | None = None,
        start_text: str = "",
        output_json: bool = False,
        completion_name: str = "",
        search_context: List[unique_sdk.Integrated.SearchResult] | None = None,
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
            debug_info (dict[str, Any] | None): Additional debug information to pass through or generate during the process.
            start_text (str): Initial text to prepend to any generated content, setting the context or continuation tone.
            output_json (bool): Flag to indicate if the output should be in JSON format. Relies on OpenAI response_format option.
            completion_name (str): Optional name or identifier for the completion operation. It'll help debug in the logs.
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

        typed_messages = self._to_typed_messages(messages)  # Returns a MessageList with the correct LLM tokenization

        context = self._reformat(typed_messages)

        context, existing_references, new_references = self._rereference(messages=context)

        formated_messages = self._to_dict_messages(context, oai=self._use_open_ai)

        options = self._build_options(
            formated_messages=formated_messages,
            tools=tools,
            tool_choice=tool_choice,
            schema=schema,
            max_tokens=max_tokens,
            output_json=output_json,
            completion_name=completion_name,
        )

        self.logger.debug(f"BL::Manager::LLM::complete({completion_name})::Model::{self._model}")

        if self._use_open_ai:
            return self._complete_openai(formated_messages=formated_messages, options=options, references=(existing_references, new_references), completion_name=completion_name)
        elif out:
            return self._complete_streaming(
                formated_messages=formated_messages,
                options=options,
                out=out,
                debug_info=debug_info,
                start_text=start_text,
                references=(existing_references, new_references),
                completion_name=completion_name,
                search_context=search_context,
            )
        else:
            return self._complete_basic(
                formated_messages=formated_messages,
                options=options,
                references=(existing_references, new_references),
                completion_name=completion_name,
                search_context=search_context,
            )

    def parse(self, message_or_messages: Message | List[Message] | List[dict[str, Any]], into: type[ToolType], completion_name: str = "") -> ToolType:
        messages = message_or_messages if isinstance(message_or_messages, list) else [message_or_messages]
        return into(**(self.complete(messages=messages, schema=into, completion_name=completion_name).content).json())
