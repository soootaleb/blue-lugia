import json
import unittest

from blue_lugia.enums import Role
from blue_lugia.managers.llm import LanguageModelManager
from blue_lugia.managers.message import MessageManager
from blue_lugia.models.message import Message, MessageList
from blue_lugia.state import StateManager
from tests.mocks.app import MockApp
from tests.mocks.event import MockEvent


class TestApp(unittest.TestCase):
    def setUp(self) -> None:
        self.event = MockEvent.create()

    def test_mocking(self) -> None:
        class MockMessageManager(MessageManager):
            def all(self, force_refresh: bool = False) -> MessageList:
                return MessageList(
                    [
                        Message.USER("Hello, world!"),
                        Message.ASSISTANT(""),
                    ],
                    tokenizer=self.tokenizer,
                    logger=self.logger,
                )

        class MockLanguageModelManager(LanguageModelManager):
            def complete(self, *args, **kwargs) -> Message:
                return Message.ASSISTANT("DEFAULT_MOCK_ANSWER")

        def module(state: StateManager) -> None:
            completion = state.complete()

            self.assertTrue(completion.content == "DEFAULT_MOCK_ANSWER")
            self.assertEqual(len(state.ctx), 2)

            first, second = state.ctx

            self.assertEqual(first.role, Role.USER)
            self.assertEqual(first.content, "Hello, world!")

            self.assertEqual(second.role, Role.ASSISTANT)
            self.assertEqual(second.content, "DEFAULT_MOCK_ANSWER")

        MockApp("Tester").using(MockLanguageModelManager).using(MockMessageManager).of(module)._run_module(self.event)

    def test_expand(self) -> None:
        class MockMessageManager(MessageManager):
            def all(self, force_refresh: bool = False) -> MessageList:
                return MessageList(
                    [
                        Message(
                            role=Role.USER,
                            content="What's the weather in Bangkok?",
                            remote=Message._Remote(
                                id="1",
                                event=self.event,
                                debug={
                                    "_tool_calls": [
                                        {
                                            "role": "assistant",
                                            "content": "This message has tool calls.",
                                            "tools_called": [
                                                {
                                                    "id": "tc1",
                                                    "type": "function",
                                                    "function": {
                                                        "name": "get_weather",
                                                        "arguments": {
                                                            "location": "Bangkok",
                                                        },
                                                    },
                                                }
                                            ],
                                        },
                                        {
                                            "role": "tool",
                                            "content": json.dumps({"weath": "WINDY", "temp": 30}),
                                            "tool_call_id": "tc1",
                                        },
                                    ],
                                },
                            ),
                        )
                    ],
                    tokenizer=self.tokenizer,
                    logger=self.logger,
                )

        class MockLanguageModelManager(LanguageModelManager):
            def complete(self, *args, **kwargs) -> Message:
                return Message.ASSISTANT("DEFAULT_MOCK_ANSWER")

        def module(state: StateManager) -> None:
            self.assertEqual(len(state.ctx), 3)

            state.ctx.expand()

            self.assertEqual(len(state.ctx), 3)

            user, assistant, tool = state.ctx

            self.assertEqual(user.role, Role.USER)
            self.assertEqual(user.content, "What's the weather in Bangkok?")

            self.assertEqual(assistant.role, Role.ASSISTANT)
            self.assertEqual(assistant.content, "This message has tool calls.")
            self.assertEqual(assistant.tool_calls[0]["id"], "tc1")
            self.assertEqual(assistant.tool_calls[0]["function"]["name"], "get_weather")

            self.assertEqual(tool.role, Role.TOOL)
            self.assertEqual(tool.content, json.dumps({"weath": "WINDY", "temp": 30}))
            self.assertEqual(tool.tool_call_id, "tc1")

        MockApp("Tester").using(MockLanguageModelManager).using(MockMessageManager).of(module)._run_module(self.event)


if __name__ == "__main__":
    unittest.main()
