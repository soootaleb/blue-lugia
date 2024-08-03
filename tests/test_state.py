import unittest

from blue_lugia.enums import Role
from blue_lugia.managers.llm import LanguageModelManager
from blue_lugia.managers.message import MessageManager
from blue_lugia.models.message import Message, MessageList
from blue_lugia.state import StateManager
from tests.mocks.app import MockApp
from tests.mocks.event import MockEvent


class TestState(unittest.TestCase):
    def _get_state(self, messages: list) -> StateManager:
        class MockMessageManager(MessageManager):
            def all(self, force_refresh: bool = False) -> MessageList:
                self.logger.debug(f"MockMessageManager.all() with {len(messages)} messages")
                self._all = MessageList(
                    messages,
                    tokenizer=self.tokenizer,
                    logger=self.logger,
                )
                self.logger.debug(f"MockMessageManager._all is {len(self._all)} messages")
                return self._all

        class MockLanguageModelManager(LanguageModelManager):
            def complete(self, *args, **kwargs) -> Message:
                return Message.ASSISTANT("DEFAULT_MOCK_ANSWER")

        return MockApp("Tester").using(MockLanguageModelManager).using(MockMessageManager).create_state(MockEvent.create())

    def test_context(self) -> None:
        state = self._get_state(
            [
                Message.USER("Hello!"),
                Message.ASSISTANT("Hi!"),
            ]
        )

        self.assertEqual(len(state.ctx), 2)

        state.context([
            Message.USER("How are you?"),
        ])

        self.assertEqual(len(state.ctx), 1)
        self.assertEqual(state.ctx.first().role, Role.USER)
        self.assertEqual(state.ctx.first().content, "How are you?")

        state.context([
            Message.ASSISTANT("I'm fine, thank you!"),
        ], append=True)

        self.assertEqual(len(state.ctx), 2)
        self.assertEqual(state.ctx.last().role, Role.ASSISTANT)
        self.assertEqual(state.ctx.last().content, "I'm fine, thank you!")

        state.context([
            Message.SYSTEM("System message 1"),
            Message.SYSTEM("System message 2"),
        ], prepend=True)

        self.assertEqual(len(state.ctx), 4)
        self.assertEqual(state.ctx.first().role, Role.SYSTEM)
        self.assertEqual(state.ctx.first().content, "System message 1")
        self.assertEqual(state.ctx[1].role, Role.SYSTEM)
        self.assertEqual(state.ctx[1].content, "System message 2")

        state.context([
            Message.ASSISTANT("Goodbye!"),
        ], append=True)

        self.assertEqual(len(state.ctx), 5)
        self.assertEqual(state.ctx.last().role, Role.ASSISTANT)
        self.assertEqual(state.ctx.last().content, "Goodbye!")

        with self.assertRaises(ValueError):
            state.context([], append=True, prepend=True)


if __name__ == "__main__":
    unittest.main()
