# from typing import Any, List, Literal

# from pydantic import BaseModel

# from blue_lugia.managers import LanguageModelManager
# from blue_lugia.models.message import Message


# class MockLanguageModelManager(LanguageModelManager):
#     _answer: Message

#     def __init__(self, model: str, temperature: float = 0, timeout: int = 600000, **kwargs) -> None:
#         super().__init__(model, temperature, timeout, **kwargs)

#         self._answer = Message.ASSISTANT("DEFAULT_MOCK_ANSWER")

#     def respond_with(self, answer: Message) -> "MockLanguageModelManager":
#         self._answer = answer
#         return self

#     def complete(
#         self,
#         messages: List[Message] | List[dict[str, Any]],
#         tools: List[type[BaseModel]] | None = None,
#         tool_choice: type[BaseModel] | None = None,
#         max_tokens: int | None | Literal["auto"] = None,
#         out: Message | None = None,
#         search_context: Any = None,
#         debug_info: dict[str, Any] | None = None,
#         start_text: str = "",
#         *args,
#         **kwargs,
#     ) -> Message:
#         return self._answer
