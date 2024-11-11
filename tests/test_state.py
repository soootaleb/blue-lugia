import unittest
import json

from pydantic import BaseModel, Field

from blue_lugia.enums import Role
from blue_lugia.managers.llm import LanguageModelManager
from blue_lugia.managers.message import MessageManager
from blue_lugia.models.message import Message, MessageList
from blue_lugia.state import StateManager
from tests.mocks.app import MockApp
from tests.mocks.event import MockEvent


EVENT = MockEvent.create(company_id="239838098572185649", user_id="265926492368670744")


class MockTool(BaseModel):
    """Just a simple tool to mock the LLM"""

    mock: str = Field(..., description="Given a simple random string")

    def run(self, call_id: str, state: StateManager, extra: dict, out: Message | None = None) -> str:
        return f"MOCKED: {self.mock}"


class TestState(unittest.TestCase):
    def _get_state(self, messages: list) -> StateManager:
        class MockMessageManager(MessageManager):
            def all(self, force_refresh: bool = False) -> MessageList:
                self._all = MessageList(
                    messages,
                    tokenizer=self.tokenizer,
                    logger=self.logger,
                )
                self._retrieved = True
                return self._all

        class MockLanguageModelManager(LanguageModelManager):
            def complete(self, *args, **kwargs) -> Message:
                kwargs.pop("out")
                return super().complete(*args, **kwargs)

        class ForkableStateManager(StateManager):
            def fork(self) -> "ForkableStateManager":
                forked = super().fork()
                forked.messages._all = self.messages.all().fork()
                forked.messages._retrieved = True
                forked._ctx = self.ctx.fork()
                return forked  # type: ignore

        return MockApp("Tester").using(MockLanguageModelManager).using(MockMessageManager).managed(ForkableStateManager).create_state(EVENT)

    def test_context(self) -> None:
        state = self._get_state(
            [
                Message.USER("Hello!"),
                Message.ASSISTANT("Hi!"),
            ]
        )

        self.assertEqual(len(state.ctx), 2)

        state.context(
            [
                Message.USER("How are you?"),
            ]
        )

        self.assertEqual(len(state.ctx), 1)
        self.assertEqual(state.ctx.first().role, Role.USER)
        self.assertEqual(state.ctx.first().content, "How are you?")

        state.context(
            [
                Message.ASSISTANT("I'm fine, thank you!"),
            ],
            append=True,
        )

        self.assertEqual(len(state.ctx), 2)
        self.assertEqual(state.ctx.last().role, Role.ASSISTANT)
        self.assertEqual(state.ctx.last().content, "I'm fine, thank you!")

        state.context(
            [
                Message.SYSTEM("System message 1"),
                Message.SYSTEM("System message 2"),
            ],
            prepend=True,
        )

        self.assertEqual(len(state.ctx), 4)
        self.assertEqual(state.ctx.first().role, Role.SYSTEM)
        self.assertEqual(state.ctx.first().content, "System message 1")
        self.assertEqual(state.ctx[1].role, Role.SYSTEM)
        self.assertEqual(state.ctx[1].content, "System message 2")

        state.context(
            [
                Message.ASSISTANT("Goodbye!"),
            ],
            append=True,
        )

        self.assertEqual(len(state.ctx), 5)
        self.assertEqual(state.ctx.last().role, Role.ASSISTANT)
        self.assertEqual(state.ctx.last().content, "Goodbye!")

        with self.assertRaises(ValueError):
            state.context([], append=True, prepend=True)

    def test_fork(self) -> None:
        state = self._get_state(
            [Message.SYSTEM("Your role is to make a mock tool call"), Message.USER("Make a mock tool call with mock message 'hello mock'"), Message.ASSISTANT("")]
        )

        state.register(MockTool)

        completion = state.complete()

        state.call(completion)

        forked = state.fork()

        assert True


if __name__ == "__main__":
    unittest.main()
