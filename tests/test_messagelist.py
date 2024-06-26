import json
import unittest

from blue_lugia.enums import Role
from blue_lugia.models.message import Message, MessageList
from tests.mocks.event import MockEvent
from tests.mocks.tokenizer import Tokenizer


class TestMessageList(unittest.TestCase):
    def setUp(self) -> None:
        self.event = MockEvent.create()

    def test_tokens(self) -> None:
        messages = MessageList(
            [
                Message.USER("ABC"),
                Message.ASSISTANT("DEFG", tool_calls=[{}]),
                Message.TOOL("HIJK", tool_call_id="tc1"),
            ],
            tokenizer=Tokenizer(),
        )

        self.assertEqual(messages.tokens, [65, 66, 67, 68, 69, 70, 71, 91, 123, 125, 93, 72, 73, 74, 75, 116, 99, 49])

    def test_fork(self) -> None:
        messages = MessageList([Message(role=Role.USER, content="What's the weather in Bangkok?")])

        forked_messages = messages.fork()

        self.assertEqual(len(forked_messages), 1)
        self.assertNotEqual(id(messages), id(forked_messages))
        self.assertNotEqual(id(messages[0]), id(forked_messages[0]))

    def test_first(self) -> None:
        first, second, third = [
            Message.USER("ABC"),
            Message.ASSISTANT("DEFG", tool_calls=[{}]),
            Message.TOOL("HIJK", tool_call_id="tc1"),
        ]

        messages = MessageList([first, second, third])

        self.assertEqual(messages.first(), first)
        self.assertEqual(messages.first(lambda m: m.role == Role.ASSISTANT), second)
        self.assertIsNone(messages.first(lambda m: m.role == Role.SYSTEM))

    def test_last(self) -> None:
        first, second, third = [
            Message.USER("ABC"),
            Message.ASSISTANT("DEFG", tool_calls=[{}]),
            Message.TOOL("HIJK", tool_call_id="tc1"),
        ]

        messages = MessageList([first, second, third])

        self.assertEqual(messages.last(), third)
        self.assertEqual(messages.last(lambda m: m.role == Role.ASSISTANT), second)
        self.assertIsNone(messages.last(lambda m: m.role == Role.SYSTEM))

    def test_filter(self) -> None:
        first, second, third = [
            Message.USER("ABC"),
            Message.ASSISTANT("DEFG", tool_calls=[{}]),
            Message.TOOL("HIJK", tool_call_id="tc1"),
        ]

        messages = MessageList([first, second, third])

        self.assertEqual(messages.filter(lambda m: m.role == Role.USER), [first])
        self.assertEqual(messages.filter(lambda m: m.role == Role.ASSISTANT), [second])
        self.assertEqual(messages.filter(lambda m: m.role == Role.TOOL), [third])
        self.assertEqual(messages.filter(lambda m: m.role == Role.SYSTEM), [])

    def test_append(self) -> None:
        messages = MessageList([Message.USER("ABC")])

        messages.append(Message.ASSISTANT("DEFG", tool_calls=[{}]))

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1].role, Role.ASSISTANT)
        self.assertEqual(messages[1].content, "DEFG")

    def test_extend(self) -> None:
        messages = MessageList([Message.USER("ABC")])

        messages.extend([Message.ASSISTANT("DEFG", tool_calls=[{}]), Message.TOOL("HIJK", tool_call_id="tc1")])

        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[1].role, Role.ASSISTANT)
        self.assertEqual(messages[1].content, "DEFG")
        self.assertEqual(messages[2].role, Role.TOOL)
        self.assertEqual(messages[2].content, "HIJK")

    def test_expand(self) -> None:
        messages = MessageList(
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
        )

        messages = messages.expand()
        messages = messages.expand()  # Should not expand more than once

        self.assertEqual(len(messages), 3)

        user, assistant, tool = messages

        self.assertEqual(user.role, Role.USER)
        self.assertEqual(user.content, "What's the weather in Bangkok?")

        self.assertEqual(assistant.role, Role.ASSISTANT)
        self.assertEqual(assistant.content, "This message has tool calls.")
        self.assertEqual(assistant.tool_calls[0]["id"], "tc1")
        self.assertEqual(assistant.tool_calls[0]["function"]["name"], "get_weather")

        self.assertEqual(tool.role, Role.TOOL)
        self.assertEqual(tool.content, json.dumps({"weath": "WINDY", "temp": 30}))
        self.assertEqual(tool.tool_call_id, "tc1")

    def test_keep(self) -> None:
        first, second, third, last = [
            Message.USER("ABC"),
            Message.ASSISTANT(
                "DEFG",
                tool_calls=[
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
            ),
            Message.TOOL("HIJK", tool_call_id="tc1"),
            Message.ASSISTANT("LMNOP"),
        ]

        messages = MessageList([first, second, third, last], tokenizer=Tokenizer())

        total_tokens_count = len(messages.tokens)
        second_tokens_count = len(MessageList([second], tokenizer=Tokenizer()).tokens)
        third_tokens_count = len(MessageList([third], tokenizer=Tokenizer()).tokens)
        last_tokens_count = len(MessageList([last], tokenizer=Tokenizer()).tokens)

        truncated = messages.keep(total_tokens_count)
        self.assertEqual(len(truncated.tokens), total_tokens_count)

        truncated = messages.keep(last_tokens_count)
        self.assertEqual(len(truncated.tokens), last_tokens_count)

        # the tool call should not remain even if there is enough space
        # that's because there is no space for the assistant message that has the tool call
        # hence the assistant message should be truncated, and the tool call should be removed
        truncated = messages.keep(third_tokens_count + last_tokens_count)
        self.assertEqual(len(truncated.tokens), last_tokens_count)

        # the tool call should remain because there is enough space
        truncated = messages.keep(second_tokens_count + third_tokens_count + last_tokens_count)
        self.assertEqual(len(truncated.tokens), second_tokens_count + third_tokens_count + last_tokens_count)

        # keep all if enough space
        truncated = messages.keep(total_tokens_count)
        self.assertEqual(len(truncated.tokens), total_tokens_count)


if __name__ == "__main__":
    unittest.main()
