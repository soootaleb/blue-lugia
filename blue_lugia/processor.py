from typing import Any, Optional

from blue_lugia.enums import Role
from blue_lugia.managers.llm import LanguageModelManager
from blue_lugia.models import Message
from blue_lugia.models.message import MessageList
from blue_lugia.state import StateManager


class Processor:
    _state: StateManager

    def __init__(self, state: StateManager) -> None:
        self._state = state

    @property
    def state(self) -> StateManager:
        return self._state

    def __call__(self) -> None:
        pass


# class MessageUpdateProcessor(Processor):
#     def __call__(self) -> None:
#         message_update = Message.update

#         def before_updating_message(self: Message, content: str | Message._Content | None, debug: dict[str, Any] | None = None) -> Message:
#             content = f"PREPENDED - {self.content}"
#             message_update(self, content, debug)
#             return self

#         Message.update = before_updating_message


class LLMCompleteProcessor(Processor):
    def __call__(self) -> None:
        llm_reformat = LanguageModelManager._reformat
        llm_complete = LanguageModelManager.complete

        # Before sending a message to LLM, we potentially remove the disclaimer
        def after_reformating_llm(self: LanguageModelManager, messages: MessageList) -> MessageList:
            reformated = llm_reformat(self, messages)
            for message in reformated:
                if message.content:
                    message.content = message.content.replace("DISCLAIMER", "")
            return reformated

        # When LLM returns a completion, we potentially add a disclaimer to it.
        def after_completing_llm(self: LanguageModelManager, *args, **kwargs) -> Message:
            completion = llm_complete(self, *args, **kwargs)
            completion.append("DISCLAIMER")
            return completion

        LanguageModelManager._reformat = after_reformating_llm
        LanguageModelManager.complete = after_completing_llm

