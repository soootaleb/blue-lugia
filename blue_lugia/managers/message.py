from typing import Any, Callable, Iterable, List

import tiktoken
import unique_sdk

from blue_lugia.enums import Role
from blue_lugia.errors import (
    ChatMessageManagerError,
    MessageFormatError,
)
from blue_lugia.managers.manager import Manager
from blue_lugia.models import Message, MessageList


class MessageManager(Manager):
    _all: MessageList
    _retrieved: bool

    _tokenizer: str | tiktoken.Encoding | None

    def __init__(
        self,
        tokenizer: str | tiktoken.Encoding | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._tokenizer = tokenizer
        self._all = MessageList([], tokenizer, logger=self.logger.getChild(MessageList.__name__))
        self._retrieved = False

    @property
    def tokenizer(self) -> tiktoken.Encoding | None:
        if isinstance(self._tokenizer, str):
            return tiktoken.encoding_for_model(self._tokenizer)
        else:
            return self._tokenizer

    def using(self, model: str | tiktoken.Encoding) -> "MessageManager":
        self._tokenizer = model
        return self

    def all(self, force_refresh: bool = False) -> MessageList:
        if not self._retrieved or force_refresh:
            if force_refresh:
                self._all = MessageList(
                    [],
                    self.tokenizer,
                    logger=self.logger.getChild(MessageList.__name__),
                )

            try:
                retrieved = unique_sdk.Message.list(
                    user_id=self._event.user_id,
                    company_id=self._event.company_id,
                    chatId=self._event.payload.chat_id,
                )

            except Exception as e:
                self.logger.error(f"BL::Manager::ChatMessage::all::ListError::{e}")
                retrieved = []

            for m in retrieved:
                original_citations = (m.debugInfo or {}).get("_citations", {})

                if m.text and original_citations:
                    original_content = m.text

                    for original_source, sup in original_citations.items():
                        original_content = original_content.replace(f"<sup>{sup}</sup>", original_source)

                else:
                    original_content = None

                try:
                    created = Message(
                        role=Role(m.role.lower()),
                        content=m.text,
                        original_content=original_content,
                        remote=Message._Remote(self._event, m.id, m.debugInfo),  # type: ignore
                        logger=self.logger.getChild(Message.__name__),
                    )
                    self._all.append(created)
                except MessageFormatError as e:
                    raise ChatMessageManagerError(f"BL::Manager::ChatMessage::all::ListError::{e}")

            self._retrieved = True

        return self._all

    def filter(self, f: Callable[[Message], bool]) -> "MessageManager":
        all_messages = self.all()
        filtered_messages = MessageList(
            filter(f, all_messages),
            self.tokenizer,
            logger=self.logger.getChild(MessageList.__name__),
        )
        manager = MessageManager(
            event=self._event,
            tokenizer=self.tokenizer,
            logger=self.logger.getChild(MessageManager.__name__),
        )
        manager._all = filtered_messages
        manager._retrieved = True
        return manager

    def __getitem__(self, index: int) -> Message:
        return self.all()[index]

    def count(self) -> int:
        return len(self.all())

    def first(self, lookup: Callable[[Message], bool] | None = None) -> Message | None:
        return self.all().first(lookup)

    def last(self, lookup: Callable[[Message], bool] | None = None) -> Message | None:
        return self.all().last(lookup)

    def get(self, message_id: str) -> Message:
        retrieved = unique_sdk.Message.retrieve(
            user_id=self._event.user_id,
            company_id=self._event.company_id,
            chatId=self._event.payload.chat_id,
            id=message_id,
        )

        return Message(
            role=Role(retrieved.role.lower()),
            content=retrieved.text,
            remote=Message._Remote(self._event, retrieved.id, retrieved.debugInfo),  # type: ignore
            logger=self.logger.getChild(Message.__name__),
        )

    def values(self, *args, **kwargs) -> List:
        mapped = []

        flat = kwargs.get("flat", False)

        for f in self.all():
            mapped.append({arg: getattr(f, arg) for arg in args})

        if flat and len(args) == 1:
            return [item[args[0]] for item in mapped]
        elif flat and len(args) == 0:
            return [item for item in mapped]
        elif flat and len(args) > 1:
            raise ChatMessageManagerError("BL::Manager::ChatMessage::values::InvalidArgs::flat=True requires at most one argument.")
        else:
            return mapped

    def create(self, role_or_message: Role | Message, text: str = "", debug: dict[str, Any] | None = None) -> Message:
        if debug is None:
            debug = {}

        if isinstance(role_or_message, Message):
            role = role_or_message.role
            content = role_or_message.content
        elif isinstance(role_or_message, Role):
            role = role_or_message
            content = text
        else:
            raise ChatMessageManagerError("BL::Manager::ChatMessage::create::TypeError::role_or_message must be of type Role or Message")

        try:
            created = unique_sdk.Message.create(
                user_id=self._event.user_id,
                company_id=self._event.company_id,
                chatId=self._event.payload.chat_id,
                assistantId=self._event.payload.assistant_id,
                text=content,
                role=role.value.upper(),
                debugInfo=debug,
            )  # type: ignore

            int_created = Message(
                role=role,
                content=content,
                remote=Message._Remote(self._event, created.id, created.debugInfo),
                logger=self.logger.getChild(Message.__name__),
            )

        except Exception as e:
            self.logger.error(f"BL::Manager::ChatMessage::create::CreateError::{e}")
            int_created = Message(
                role=role,
                content=content,
                remote=None,
                logger=self.logger.getChild(Message.__name__),
            )

        self._all.append(int_created)

        return int_created

    def delete(self) -> int:
        deleted = 0
        for message in self.all():
            try:
                message.delete()
            except Exception:
                pass
            else:
                deleted += 1

        self._all = MessageList([], self.tokenizer, logger=self.logger.getChild(MessageList.__name__))

        return deleted

    def append(self, message: Message) -> "MessageManager":
        self._all.append(message)
        return self

    def extend(self, messages: Iterable[Message]) -> "MessageManager":
        self._all.extend(messages)
        return self
