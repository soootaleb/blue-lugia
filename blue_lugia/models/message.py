import json
import logging
import re
from typing import Any, Callable, Iterable, List, Optional, SupportsIndex, Type, TypeVar

import tiktoken
import unique_sdk
from pydantic import BaseModel

from blue_lugia.enums import Role
from blue_lugia.errors import MessageFormatError, MessageRemoteError
from blue_lugia.models import ExternalModuleChosenEvent
from blue_lugia.models.model import Model

Parsed = TypeVar("Parsed", bound=BaseModel)


class Message(Model):
    """
    Represents a message within a system, encapsulating data along with operations
    related to message handling and processing in a communication or processing environment.

    Properties:
        role: Returns the role of the message.
        debug: Retrieves debug information, primarily from the remote linkage.
        content: Gets or sets the message content, handling conversion to _Content class as needed.
        id: Returns the unique identifier of the message, derived from the remote connection if available.
        tool_call_id: Accesses the identifier for the tool call associated with the message.
        tool_calls: Lists all tool interaction data linked with the message.
        is_command: Determines if the message starts with a command indicator.
        language: Extracts language preference from embedded or debug information.

    Nested Classes:
        _Remote: Handles connection-specific data such as event linkage and debugging information.
        _Content: Enhances string content with methods for JSON conversion and pretty printing.

    Methods:
        __init__: Initializes a new Message instance with designated role, content, and additional properties.
        update: Modifies the content and/or debug information of the message.
        append: Adds additional content to the existing message content.
        prepend: Prefixes content to the existing message content.
        delete: Removes the message, typically from a remote system or database.
        USER: Class method to create a user-type message.
        SYSTEM: Class method to create a system-type message.
        ASSISTANT: Class method to create an assistant-type message with tool interactions.
        TOOL: Class method to create a tool-type message with a specific tool call identifier.
        fork: Creates a copy of the current message, optionally including remote and tool call data.
        __str__: Provides a brief string representation of the message content.
        __repr__: Offers a detailed string representation for debugging or logging.

    Raises:
        MessageFormatError: For invalid roles or missing required attributes in certain contexts.
        MessageRemoteError: For operations that require a valid remote connection but none is present.
    """

    class _Remote:
        """
        Encapsulates remote-related information for a Message, including unique identifiers and event details.

        Properties:
            id: Returns the unique identifier of the remote session.
            event: Retrieves the event tied to this remote session.
            debug: Accesses the debug information associated with this remote session.
        """

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
        """
        Enhances basic string operations to include JSON conversion and pretty printing, tailored for message content that might include structured data.

        Methods:
            json: Converts the content (assumed to be in JSON format) into a Python dictionary.
            pprint: Returns a pretty-printed version of the JSON content.
            __getitem__: Allows slicing and indexing on the content, returning processed subsections as new _Content instances.
        """

        def json(self) -> dict[str, Any]:
            self = self.replace("\n", "").strip("`")
            if self.startswith("json"):
                self = self[4:]
            self = re.sub(r"(?<=\d),(?=\d)", "", self)
            return json.loads(self)

        def parse(self, into: Type[Parsed]) -> Parsed:
            return into(**self.json())

        def pprint(self, indent: int = 2) -> str:
            return "```json{}{}{}```".format("\n", json.dumps(self.json(), indent=indent, ensure_ascii=False), "\n")

        def __getitem__(self, key: SupportsIndex | slice) -> "Message._Content":
            return Message._Content(super().__getitem__(key))

    _role: Role
    _content: Optional[_Content]
    _original_content: Optional[_Content]

    _tool_calls: List[dict[str, Any]]
    _tool_call_id: Optional[str]

    _sources: List[unique_sdk.Integrated.SearchResult]
    _citations: dict[str, int]

    _remote: _Remote | None = None

    def __init__(
        self,
        role: Role,
        content: Optional[str | _Content] = None,
        remote: _Remote | None = None,
        tool_call_id: Optional[str] = None,
        tool_calls: List[dict[str, Any]] | None = None,
        citations: dict[str, int] | None = None,
        sources: List[unique_sdk.Integrated.SearchResult] | None = None,
        original_content: Optional[str | _Content] = None,
        **kwargs: logging.Logger,
    ) -> None:
        """
        Initializes a new instance of the Message class.

        Args:
            role (Role): The role of the message, defining how it interacts within the system (e.g., USER, SYSTEM).
            content (Optional[str | _Content]): The main content of the message, which can be plain text or structured (_Content).
            remote (_Remote | None): Remote connection data, providing linkage to external events and debug information.
            tool_call_id (Optional[str]): A unique identifier for a tool interaction specific to this message.
            tool_calls (List[dict[str, Any]] | None): Detailed records of tool interactions associated with the message.
            **kwargs: Standard logging options or other additional parameters.

        Raises:
            MessageFormatError: If the role is invalid or required attributes are missing.
        """
        super().__init__(**kwargs)

        self._remote = remote

        self._tool_calls = tool_calls or []
        self._tool_call_id = tool_call_id

        self._sources = sources or []
        self._citations = citations or {}

        if role.value.lower() not in [r.value.lower() for r in Role]:  # python 3.11 does not allow the in operator to work with enums
            raise MessageFormatError(f"BL::Model::Message::init::InvalidRole::{role.value}")
        else:
            self._role = role
            self.content = content if content else None
            self.original_content = original_content if original_content else self.content

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
    def sources(self) -> List[unique_sdk.Integrated.SearchResult]:
        return self.debug.get("_sources", []) or self._sources

    @property
    def citations(self) -> dict[str, int]:
        return self.debug.get("_citations") or self._citations

    @property
    def content(self) -> Optional[_Content]:
        return self._content

    @property
    def original_content(self) -> Optional[_Content]:
        return self._original_content

    @content.setter
    def content(self, value: str | _Content | None) -> None:
        self._content = Message._Content(value) if value is not None else None

    @original_content.setter
    def original_content(self, value: str | _Content | None) -> None:
        self._original_content = Message._Content(value) if value is not None else None

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
        params = re.search(r"\{.*\}", chosen_module_response.replace("\n", ""))
        params = params.group() if params else "{}"
        params = json.loads(params)

        if "language" in params:
            return params.get("language", "English")
        elif "Language: " in chosen_module_response:
            return chosen_module_response.split("Language: ")[1]
        else:
            return "English"

    def to_dict(self) -> dict:
        base = {
            "role": self.role.value,
            "content": self.content,
            "original_content": self.original_content,
        }

        if self._tool_calls:
            base["tool_calls"] = self.tool_calls

        if self._tool_call_id:
            base["tool_call_id"] = self.tool_call_id

        if self._remote:
            base["remote"] = {
                "id": self._remote._id,
                "debug": self._remote._debug,
            }

        return base

    def as_dict(self) -> dict:
        return self.to_dict()

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def update(self, content: str | _Content | None = None, debug: dict[str, Any] | None = None, references: List[Any] | None = None) -> "Message":
        """
        Updates the content of the message and optionally merges new debug information into the existing debug data.

        Args:
            content (str | _Content | None): New content to replace the existing content of the message.
            debug (dict[str, Any] | None): Additional debug information to merge with existing debug data.

        Returns:
            Message: The updated message instance, reflecting new content and debug information.
        """

        if debug is None:
            debug = {}

        args = {}

        if content is not None:
            self.content = content
            args["text"] = self.content

        if references:
            args["references"] = references

        if self._remote:
            self._remote._debug = (self._remote._debug or {}) | debug

            unique_sdk.Message.modify(
                user_id=self._remote._event.user_id,
                company_id=self._remote._event.company_id,
                chatId=self._remote._event.payload.chat_id,
                id=self._remote._id,
                debugInfo=self._remote._debug,
                **args,
            )

        elif debug:
            self.logger.warning("BL::Model::Message::update::NoRemoteCounterPart::Setting debug info on a message without a remote counterpart.")

        return self

    def append(self, content: str, new_line: bool = True) -> "Message":
        """
        Appends additional content to the end of the current message content, optionally separated by new lines.

        Args:
            content (str): Content to append.
            new_line (bool): If True, appends the new content on a new line.

        Returns:
            Message: The message instance with updated content.
        """
        int_content = self.content or ""
        if new_line:
            int_content += "\n\n"
        int_content += content
        return self.update(int_content)

    def prepend(self, content: str, new_line: bool = True) -> "Message":
        """
        Prepends additional content to the beginning of the current message content, optionally separated by new lines.

        Args:
            content (str): Content to prepend.
            new_line (bool): If True, prepends the new content on a new line.

        Returns:
            Message: The message instance with updated content.
        """
        int_content = self.content or ""
        if new_line:
            content += "\n\n"
        int_content = content + int_content
        return self.update(int_content)

    def delete(self) -> "Message":
        """
        Deletes the message from the remote system or database, assuming a valid remote session is available.

        Raises:
            MessageRemoteError: If the message does not have a remote counterpart but an operation requiring one is attempted.

        Returns:
            Message: The message instance after the deletion operation, typically used for cleanup or confirmation.
        """
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
        cls, content: str | _Content | None, sources: List[unique_sdk.Integrated.SearchResult] | None = None, **kwargs: Any
    ) -> "Message":
        """
        Factory method to create a user-type message.

        Args:
            content (str | _Content | None): The content of the message.
            **kwargs: Additional attributes or configurations specific to the user message.

        Returns:
            Message: A new message instance with the role set to USER.
        """
        return cls(role=Role.USER, content=content, sources=sources, **kwargs)

    @classmethod
    def SYSTEM(  # noqa: N802
        cls, content: str | _Content | None, sources: List[unique_sdk.Integrated.SearchResult] | None = None, **kwargs: Any
    ) -> "Message":
        """
        Factory method to create a system-type message.

        Args:
            content (str | _Content | None): The content of the message.
            **kwargs: Additional attributes or configurations specific to the system message.

        Returns:
            Message: A new message instance with the role set to SYSTEM.
        """
        return cls(role=Role.SYSTEM, content=content, sources=sources, **kwargs)

    @classmethod
    def ASSISTANT(  # noqa: N802
        cls,
        content: str | _Content | None,
        tool_calls: List[dict[str, Any]] = [],
        sources: List[unique_sdk.Integrated.SearchResult] | None = None,
        **kwargs: Any,
    ) -> "Message":
        """
        Factory method to create an assistant-type message that may include tool interactions.

        Args:
            content (str | _Content | None): The content of the message.
            tool_calls (List[dict[str, Any]]): A list of tool interaction details.
            **kwargs: Additional attributes or configurations specific to the assistant message.

        Returns:
            Message: A new message instance with the role set to ASSISTANT.
        """
        return cls(role=Role.ASSISTANT, content=content, tool_calls=tool_calls, sources=sources, **kwargs)

    @classmethod
    def TOOL(  # noqa: N802
        cls,
        content: str | _Content | None,
        tool_call_id: str,
        citations: dict[str, int] | None = None,
        sources: List[unique_sdk.Integrated.SearchResult] | None = None,
        **kwargs: Any,
    ) -> "Message":
        """
        Factory method to create a tool-type message with a specific tool call identifier.

        Args:
            content (str | _Content | None): The content of the message.
            tool_call_id (str): The unique identifier for a tool interaction.
            **kwargs: Additional attributes or configurations specific to the tool message.

        Returns:
            Message: A new message instance with the role set to TOOL.
        """
        return cls(role=Role.TOOL, content=content, tool_call_id=tool_call_id, citations=citations, sources=sources, **kwargs)

    def fork(self) -> "Message":
        """
        Creates a deep copy of the current message, including all properties and nested data, suitable for independent modifications without affecting the original instance.

        Returns:
            Message: A new message instance that is a deep copy of the current message.
        """
        return self.__class__(
            role=Role(self.role.value),
            content=self.__class__._Content(self.content) if self.content else None,
            original_content=self.__class__._Content(self.original_content) if self.original_content else None,
            remote=(self.__class__._Remote(self._remote._event, self._remote._id, self.debug.copy()) if self._remote else None),
            citations=self.citations.copy(),
            tool_call_id=self._tool_call_id,
            sources=[s.copy() for s in self.sources],
            tool_calls=[tc.copy() for tc in self._tool_calls],
            logger=self.logger.getChild(self.__class__.__name__),
        )

    def __str__(self) -> str:
        content = self.content.strip("\n") if self.content else ""
        return f"{self.role.value.upper()}: {content[:30]}"

    def __repr__(self) -> str:
        content = self.content.strip("\n") if self.content else ""
        return f"{self.role.value.upper()}: {content[:30]}"


class MessageList(List[Message], Model):
    """
    A specialized list for managing collections of Message objects, with added functionality
    for handling messages in a structured format.

    Properties;
        tokenizer: Returns the tokenizer set for encoding the message content.
        tokens: Aggregates tokens from all messages in the list using the set tokenizer.

    Methods:
        __init__: Initializes a new MessageList with optional iterable of messages and a tokenizer.
        fork: Creates a copy of the message list, optionally modifying the copied version.
        using: Sets or updates the tokenizer used for the message list.
        first: Returns the first message from the list that meets specified conditions.
        last: Returns the last message from the list that meets specified conditions.
        filter: Returns a new MessageList containing messages that meet specified conditions.
        keep: Modifies the message list to fit within a specified token limit.
        expand: Expands messages in the list by adding detailed entries for tool calls.
        append: Appends a new message to the message list.
        extend: Extends the message list by adding multiple messages from an iterable.
    """

    _expanded: bool
    _tokenizer: str | tiktoken.Encoding | None

    def __init__(
        self,
        iterable: Iterable[Message] = [],
        tokenizer: str | tiktoken.Encoding | None = None,
        **kwargs,
    ) -> None:
        """
        Initializes a new instance of MessageList.

        Args:
            iterable (Iterable[Message]): An optional iterable of messages to populate the list.
            tokenizer (str | tiktoken.Encoding | None): The tokenizer to use for encoding the messages.
            **kwargs: Additional keyword arguments passed to the Model initializer.
        """
        list.__init__(self, iterable)
        Model.__init__(self, **kwargs)
        self._expanded = False
        self._tokenizer = tokenizer

    @property
    def tokenizer(self) -> tiktoken.Encoding | None:
        """
        Gets the current tokenizer used for encoding message contents.

        Returns:
            tiktoken.Encoding | None: The tokenizer object if set, otherwise None.
        """
        if isinstance(self._tokenizer, str):
            return tiktoken.encoding_for_model(self._tokenizer)
        else:
            return self._tokenizer

    @property
    def tokens(self) -> list[int]:
        """
        Aggregates all tokens from messages in the list using the set tokenizer.

        Returns:
            list[int]: A list of token ids from all messages.

        Raises:
            ValueError: If no tokenizer is set for the message list.
        """
        if not self.tokenizer:
            raise ValueError("BL::Model::MessageList::tokens::NoTokenizer")

        all_tokens = []
        for message in self:
            if message.content or message.tool_calls:
                if message.content:
                    all_tokens += self.tokenizer.encode(message.content)
                if message.tool_calls:
                    all_tokens += self.tokenizer.encode(json.dumps(message.tool_calls, ensure_ascii=False))
                if message.tool_call_id:
                    all_tokens += self.tokenizer.encode(message.tool_call_id)
        return all_tokens

    @property
    def sources(self) -> List[unique_sdk.Integrated.SearchResult]:
        return [source for message in self for source in message.sources]

    def to_dict(self) -> dict:
        return {
            "expanded": self._expanded,
            "tokenizer": str(self._tokenizer),
            "messages": [m.to_dict() for m in self],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def fork(self) -> "MessageList":
        """
        Creates a copy of the current MessageList, maintaining the tokenizer and any expanded state.

        Returns:
            MessageList: A new instance of MessageList with identical properties and contents.
        """
        forked = self.__class__([o.fork() for o in self], self._tokenizer, logger=self.logger)
        forked._expanded = self._expanded
        return forked

    def using(self, tokenizer: str | tiktoken.Encoding) -> "MessageList":
        """
        Sets or updates the tokenizer used for encoding the messages in the list.

        Args:
            tokenizer (str | tiktoken.Encoding): The tokenizer to set.

        Returns:
            MessageList: The current instance with the updated tokenizer.
        """
        self._tokenizer = tokenizer
        return self

    def first(self, lookup: Callable[[Message], bool] | None = None) -> Message | None:
        """
        Retrieves the first message from the list that satisfies a specified condition.

        Args:
            lookup (Callable[[Message], bool] | None): A function to determine if a message satisfies the condition.

        Returns:
            Message | None: The first message that meets the condition, or None if no such message exists.
        """
        if lookup:
            return next(filter(lookup, self), None)
        else:
            return self[0] if len(self) else None

    def last(self, lookup: Callable[[Message], bool] | None = None) -> Message | None:
        """
        Retrieves the last message from the list that satisfies a specified condition.

        Args:
            lookup (Callable[[Message], bool] | None): A function to determine if a message satisfies the condition.

        Returns:
            Message | None: The last message that meets the condition, or None if no such message exists.
        """
        if lookup:
            return next(filter(lookup, reversed(self)), None)
        else:
            return self[-1] if len(self) else None

    def filter(self, f: Callable[[Message], bool]) -> "MessageList":
        """
        Filters the messages in the list according to a specified condition and returns a new MessageList containing the filtered messages.

        Args:
            f (Callable[[Message], bool]): The condition to apply to each message.

        Returns:
            MessageList: A new MessageList containing only the messages that meet the condition.
        """
        return MessageList(filter(f, self), self._tokenizer, logger=self.logger)

    def truncate(self, max_tokens: int, in_place: bool = False) -> "MessageList":
        """
        Reduces the list to fit within a specified maximum number of tokens, optionally modifying the original list.

        Args:
            max_tokens (int): The maximum number of tokens allowed in the list.
            in_place (bool): If True, modifications are made directly to this list; if False, a new list is returned.

        Returns:
            MessageList: The modified list, either the original or a new instance, depending on the value of in_place.
        """
        if in_place:
            self.logger.debug(f"BL::Model::MessageList::keep::{max_tokens} tokens out of {len(self.tokens)} tokens along {len(self)} messages.")
            while len(self.tokens) > max_tokens:
                if len(self):
                    first_non_system_message = self.first(lambda x: x.role != Role.SYSTEM)

                    if not first_non_system_message:
                        self.logger.warning("BL::Model::MessageList::keep::No non-system message found in the message list when truncating.")
                        break

                    first_non_system_message_index = self.index(first_non_system_message)

                    removed_message = self.pop(first_non_system_message_index)

                    self.logger.debug(f"BL::Model::MessageList::keep::Removing message {removed_message.role} with {len(removed_message.tool_calls)} tool calls.")

                    for tc in removed_message.tool_calls:
                        while found_tc := next(
                            filter(lambda x: x.tool_call_id == tc["id"], self),
                            None,
                        ):
                            if found_tc:
                                self.logger.debug(f"BL::Model::MessageList::keep::Removing tool call {found_tc.tool_call_id}")
                                self.remove(found_tc)

            return self

        else:
            return self.fork().truncate(max_tokens, in_place=True)

    def keep(self, max_tokens: int, in_place: bool = False) -> "MessageList":
        self.logger.warning("BL::Model::MessageList::keep::Deprecated::Use truncate instead.")
        return self.truncate(max_tokens, in_place)

    def expand(self, in_place: bool = False) -> "MessageList":
        """
        Expands the messages in the list by adding detailed entries for each tool call, referenced in the messages' debug information.

        Args:
            legacy_key (str): The key in the debug information under which older tool calls are stored.
            in_place (bool): If True, the expansion is done in the current list; if False, a new list is returned.

        Returns:
            MessageList: The expanded message list, either the original or a new instance, depending on the value of in_place.
        """
        self.logger.debug("BL::Model::MessageList::expand")

        if in_place:
            if not self._expanded:
                for message in self:
                    if message.debug:
                        tools_called = message.debug.get("_tool_calls", [])
                        message_index = self.index(message)

                        self[message_index + 1 : message_index + 1] = [
                            Message(
                                role=Role(value=tc["role"]),
                                content=tc.get("content", None),
                                original_content=tc.get("original_content", None),
                                tool_calls=tc.get("tools_called", []),
                                tool_call_id=tc.get("tool_call_id", None),
                                sources=tc.get("sources", []),
                                citations=tc.get("citations", {}),
                                logger=self.logger.getChild(Message.__name__),
                            )
                            for tc in tools_called
                        ]

                self._expanded = True

            return self
        else:
            return self.fork().expand(in_place=True)

    def append(self, object: Message) -> "MessageList":
        super().append(object)
        return self

    def extend(self, iterable: Iterable[Message]) -> "MessageList":
        super().extend(iterable)
        return self
