import json
import logging
import re
from typing import Any, Callable, Iterable, List, Optional, SupportsIndex

import tiktoken
import unique_sdk  # type: ignore

from blue_lugia.enums import Role
from blue_lugia.errors import MessageFormatError, MessageRemoteError
from blue_lugia.models import ExternalModuleChosenEvent
from blue_lugia.models.model import Model


class Message(Model):
    class _Remote:
        _id: str
        _event: ExternalModuleChosenEvent
        _debug: dict[str, Any]

        def __init__(self, event: ExternalModuleChosenEvent, id: str, debug: dict[str, Any]) -> None:
            self._event = event
            self._id = id
            self._debug = debug or {}

        @property
        def id(self) -> str:
            return self._id

        @property
        def event(self) -> ExternalModuleChosenEvent:
            return self._event

        @property
        def debug(self) -> dict[str, Any]:
            return self._debug

    class _Content(str):
        def json(self) -> dict[str, Any]:
            self = self.replace("\n", "").strip("`")
            if self.startswith("json"):
                self = self[4:]
            self = re.sub(r"(?<=\d),(?=\d)", "", self)
            return json.loads(self)

        def pprint(self, indent: int = 2) -> str:
            return "```json{}{}{}```".format("\n", json.dumps(self.json(), indent=indent), "\n")

        def __getitem__(self, key: SupportsIndex | slice) -> "Message._Content":
            return Message._Content(super().__getitem__(key))

    _role: Role
    _content: Optional[_Content]

    _tool_calls: List[dict[str, Any]]
    _tool_call_id: Optional[str]

    _remote: _Remote | None = None

    def __init__(
        self,
        role: Role,
        content: Optional[str | _Content] = None,
        remote: _Remote | None = None,
        tool_call_id: Optional[str] = None,
        tool_calls: List[dict[str, Any]] | None = None,
        **kwargs: logging.Logger,
    ) -> None:
        super().__init__(**kwargs)

        self._remote = remote

        self._tool_calls = tool_calls or []
        self._tool_call_id = tool_call_id

        if role.value.lower() not in [r.value.lower() for r in Role]:  # python 3.11 does not allow the in operator to work with enums
            raise MessageFormatError(f"BL::Model::Message::init::InvalidRole::{role.value}")
        else:
            self._role = role
            self.content = content if content else None

        if self.role == Role.TOOL and not self._tool_call_id:
            raise MessageFormatError("BL::Model::Message::init::ToolMessageWithoutToolCallId")

        if self.role != Role.ASSISTANT and self._tool_calls:
            raise MessageFormatError("BL::Model::Message::init::NonAssistantMessageWithToolCalls")

    @property
    def role(self) -> Role:
        return self._role

    @property
    def debug(self) -> dict:
        if self._remote:
            return self._remote._debug
        else:
            self.logger.warning("BL::Model::Message::debug::NoRemoteCounterPart")
            return {}

    @property
    def content(self) -> Optional[_Content]:
        return self._content

    @content.setter
    def content(self, value: str | _Content | None) -> None:
        self._content = Message._Content(value)

    @property
    def id(self) -> str | None:
        return self._remote._id if self._remote else None

    @property
    def tool_call_id(self) -> Optional[str]:
        return self._tool_call_id

    @property
    def tool_calls(self) -> List[dict]:
        return self._tool_calls

    @property
    def is_command(self) -> bool:
        if not self.content:
            return False
        return self.content.startswith("!") or self.content.startswith("/")

    @property
    def language(self) -> str:
        chosen_module_response: str = self.debug.get("chosenModuleResponse", "")
        params = re.search(r"\{.*\}", chosen_module_response)
        params = params.group() if params else "{}"
        params = json.loads(params)
        return params.get("language", "English")

    def update(self, content: str | _Content | None, debug: dict[str, Any] | None = None) -> "Message":
        if debug is None:
            debug = {}
        self.content = content
        if self._remote:
            self._remote._debug = (self._remote._debug or {}) | debug
            unique_sdk.Message.modify(
                user_id=self._remote._event.user_id,
                company_id=self._remote._event.company_id,
                chatId=self._remote._event.payload.chat_id,
                id=self._remote._id,
                text=self.content or "",
                debugInfo=self._remote._debug,
                references=[],
            )
        return self

    def append(self, content: str, new_line: bool = True) -> "Message":
        int_content = self.content or ""
        if new_line:
            int_content += "\n\n"
        int_content += content
        return self.update(int_content)

    def prepend(self, content: str, new_line: bool = True) -> "Message":
        int_content = self.content or ""
        if new_line:
            content += "\n\n"
        int_content = content + int_content
        return self.update(int_content)

    def delete(self) -> "Message":
        if not self._remote:
            raise MessageRemoteError("BL::Model::Message::delete::RemoteError::Message has no remote counter part")

        unique_sdk.Message.delete(
            id=self._remote._id,
            user_id=self._remote._event.user_id,
            company_id=self._remote._event.company_id,
            chatId=self._remote._event.payload.chat_id,
        )

        return self

    @classmethod
    def USER(  # noqa: N802
        cls, content: str | _Content | None, **kwargs: Any
    ) -> "Message":
        return cls(Role.USER, content, **kwargs)

    @classmethod
    def SYSTEM(  # noqa: N802
        cls, content: str | _Content | None, **kwargs: Any
    ) -> "Message":
        return cls(Role.SYSTEM, content, **kwargs)

    @classmethod
    def ASSISTANT(  # noqa: N802
        cls,
        content: str | _Content | None,
        tool_calls: List[dict[str, Any]] = [],
        **kwargs: Any,
    ) -> "Message":
        return cls(Role.ASSISTANT, content, tool_calls=tool_calls, **kwargs)

    @classmethod
    def TOOL(  # noqa: N802
        cls, content: str | _Content | None, tool_call_id: str, **kwargs: Any
    ) -> "Message":
        return cls(Role.TOOL, content, tool_call_id=tool_call_id, **kwargs)

    def fork(self) -> "Message":
        return Message(
            role=Role(self.role.value),
            content=Message._Content(self.content) if self.content else None,
            remote=(Message._Remote(self._remote._event, self._remote._id, self.debug.copy()) if self._remote else None),
            tool_call_id=self._tool_call_id,
            tool_calls=[tc.copy() for tc in self._tool_calls],
            logger=self.logger.getChild(Message.__name__),
        )

    def __str__(self) -> str:
        content = self.content.strip("\n") if self.content else ""
        return f"{self.role.value.upper()}: {content[:30]}"

    def __repr__(self) -> str:
        content = self.content.strip("\n") if self.content else ""
        return f"{self.role.value.upper()}: {content[:30]}"


class MessageList(List[Message], Model):
    _expanded: bool
    _tokenizer: str | tiktoken.Encoding | None

    def __init__(
        self,
        iterable: Iterable[Message] = [],
        tokenizer: str | tiktoken.Encoding | None = None,
        **kwargs,
    ) -> None:
        list.__init__(self, iterable)
        Model.__init__(self, **kwargs)
        self._expanded = False
        self._tokenizer = tokenizer

    @property
    def tokenizer(self) -> tiktoken.Encoding | None:
        if isinstance(self._tokenizer, str):
            return tiktoken.encoding_for_model(self._tokenizer)
        else:
            return self._tokenizer

    @property
    def tokens(self) -> list[int]:
        if not self.tokenizer:
            raise ValueError("No tokenizer set for MessageList")

        all_tokens = []
        for message in self:
            if message.content or message.tool_calls:
                if message.content:
                    all_tokens += self.tokenizer.encode(message.content)
                if message.tool_calls:
                    all_tokens += self.tokenizer.encode(json.dumps(message.tool_calls))
                if message.tool_call_id:
                    all_tokens += self.tokenizer.encode(message.tool_call_id)
        return all_tokens

    def fork(self) -> "MessageList":
        forked = MessageList([o.fork() for o in self], self._tokenizer, logger=self.logger)
        forked._expanded = self._expanded
        return forked

    def using(self, tokenizer: str | tiktoken.Encoding) -> "MessageList":
        self._tokenizer = tokenizer
        return self

    def first(self, lookup: Callable[[Message], bool] | None = None) -> Message | None:
        if lookup:
            return next(filter(lookup, self), None)
        else:
            return self[0] if len(self) else None

    def last(self, lookup: Callable[[Message], bool] | None = None) -> Message | None:
        if lookup:
            return next(filter(lookup, reversed(self)), None)
        else:
            return self[-1] if len(self) else None

    def filter(self, f: Callable[[Message], bool]) -> "MessageList":
        return MessageList(filter(f, self), self._tokenizer, logger=self.logger)

    def keep(self, max_tokens: int, in_place: bool = False) -> "MessageList":
        if in_place:
            self.logger.debug(f"Keeping {max_tokens} tokens from {len(self.tokens)} tokens along {len(self)} messages.")
            while len(self.tokens) > max_tokens:
                if len(self):
                    first_non_system_message = self.first(lambda x: x.role != Role.SYSTEM)

                    if not first_non_system_message:
                        self.logger.warning("No non-system message found in the message list when truncating.")
                        break

                    first_non_system_message_index = self.index(first_non_system_message)

                    removed_message = self.pop(first_non_system_message_index)

                    self.logger.debug(f"Removing message {removed_message.role} with {len(removed_message.tool_calls)} tool calls.")

                    for tc in removed_message.tool_calls:
                        while found_tc := next(
                            filter(lambda x: x.tool_call_id == tc["id"], self),
                            None,
                        ):
                            if found_tc:
                                self.logger.debug(f"Removing tool call {found_tc.tool_call_id}")
                                self.remove(found_tc)

            return self

        else:
            return self.fork().keep(max_tokens, in_place=True)

    def expand(self, legacy_key: str = "state_manager_tool_calls", in_place: bool = False) -> "MessageList":
        self.logger.debug("Expanding message list")

        if in_place:
            if not self._expanded:
                for message in self:
                    if message.debug:
                        tools_called = message.debug.get("_tool_calls", [])
                        message_index = self.index(message)

                        self[message_index + 1 : message_index + 1] = [
                            Message(
                                role=Role(value=tc["role"]),
                                content=(Message._Content(tc["content"]) if tc["content"] else None),
                                tool_calls=tc.get("tools_called", []),
                                tool_call_id=tc.get("tool_call_id", None),
                                logger=self.logger.getChild(Message.__name__),
                            )
                            for tc in tools_called
                        ]

                        # Load UIC older tool calls
                        tools_called = message.debug.get(legacy_key, "[]")
                        message_index = self.index(message)

                        self[message_index + 1 : message_index + 1] = [
                            Message(
                                role=Role(value=tc["role"]),
                                content=(Message._Content(tc["content"]) if tc["content"] else None),
                                tool_calls=[
                                    {
                                        "id": tcall["id"],
                                        "type": tcall["type"],
                                        "function": {
                                            "name": tcall["function"]["name"],
                                            "arguments": json.loads(tcall["function"]["arguments"]),
                                        },
                                    }
                                    for tcall in tc.get("toolCalls", [])
                                ],
                                tool_call_id=tc.get("toolCallId", None),
                                logger=self.logger.getChild(Message.__name__),
                            )
                            for tc in json.loads(tools_called)
                        ]

                self._expanded = True

            return self
        else:
            return self.fork().expand(legacy_key, in_place=True)

    def append(self, object: Message) -> "MessageList":
        super().append(object)
        return self

    def extend(self, iterable: Iterable[Message]) -> "MessageList":
        super().extend(iterable)
        return self
