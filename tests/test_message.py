import unittest
from typing import cast

import unique_sdk

from blue_lugia.enums import Role
from blue_lugia.errors import MessageFormatError
from blue_lugia.models.message import Message
from tests.mocks.event import MockEvent


class TestMessage(unittest.TestCase):
    def setUp(self) -> None:
        self.event = MockEvent.create()

    def test_sources(self) -> None:
        message = Message(
            role=Role.ASSISTANT,
            content=None,
            remote=Message._Remote(
                id="1",
                event=self.event,
                debug={
                    "_sources": [
                        unique_sdk.Integrated.SearchResult(
                            id="1",
                            chunkId="1",
                            key="key1",
                            url="url1",
                        ),
                        unique_sdk.Integrated.SearchResult(
                            id="2",
                            chunkId="2",
                            key="key2",
                            url="url2",
                        ),
                    ]
                },
            ),
        )

        sources = message.sources

        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0].get("id"), "1")
        self.assertEqual(sources[0].get("chunkId"), "1")
        self.assertEqual(sources[0].get("key"), "key1")
        self.assertEqual(sources[0].get("url"), "url1")

        self.assertEqual(sources[1].get("id"), "2")
        self.assertEqual(sources[1].get("chunkId"), "2")
        self.assertEqual(sources[1].get("key"), "key2")
        self.assertEqual(sources[1].get("url"), "url2")

    def test_factory_user(self) -> None:
        message = Message.USER("What's the weather in Bangkok?")

        self.assertEqual(message.role, Role.USER)
        self.assertEqual(message.content, "What's the weather in Bangkok?")

    def test_factory_system(self) -> None:
        message = Message.SYSTEM("This is a system message.")

        self.assertEqual(message.role, Role.SYSTEM)
        self.assertEqual(message.content, "This is a system message.")

    def test_factory_tool(self) -> None:
        message = Message.TOOL("This is a tool message.", tool_call_id="tc1")

        self.assertEqual(message.role, Role.TOOL)
        self.assertEqual(message.content, "This is a tool message.")
        self.assertEqual(message.tool_call_id, "tc1")

    def test_fork(self) -> None:
        message = Message(
            role=Role.USER,
            content="What's the weather in Bangkok?",
            remote=Message._Remote(
                id="1",
                event=self.event,
                debug={"key": "value"},
            ),
        )
        forked_message = message.fork()

        self.assertEqual(forked_message.role, Role.USER)
        self.assertEqual(forked_message.content, "What's the weather in Bangkok?")

        self.assertNotEqual(id(message), id(forked_message))

        self.assertEqual(message._remote.id, forked_message._remote.id)  # type: ignore
        self.assertNotEqual(id(message._remote), id(forked_message._remote))

        self.assertEqual(message.content, forked_message.content)
        self.assertNotEqual(id(message.content), id(forked_message.content))

        self.assertEqual(message.debug, forked_message.debug)
        self.assertNotEqual(id(message.debug), id(forked_message.debug))

    def test_factory_assistant(self) -> None:
        message = Message.ASSISTANT(
            "This is an assistant message.",
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
        )

        self.assertEqual(message.role, Role.ASSISTANT)
        self.assertEqual(message.content, "This is an assistant message.")
        self.assertEqual(len(message.tool_calls), 1)
        self.assertEqual(message.tool_calls[0]["id"], "tc1")
        self.assertEqual(message.tool_calls[0]["type"], "function")
        self.assertEqual(message.tool_calls[0]["function"]["name"], "get_weather")
        self.assertEqual(message.tool_calls[0]["function"]["arguments"]["location"], "Bangkok")

    def test_is_command(self) -> None:
        self.assertFalse(Message.USER("What's the weather in Bangkok?").is_command)
        self.assertTrue(Message.USER("/command").is_command)
        self.assertTrue(Message.USER("/command with arguments").is_command)
        self.assertTrue(Message.USER("!command").is_command)
        self.assertTrue(Message.USER("!command with arguments").is_command)

    def test_update(self) -> None:
        message = Message(role=Role.USER, content="What's the weather in Bangkok?")
        message.update(content="What's the weather in Paris?")
        self.assertEqual(message.content, "What's the weather in Paris?")

    def test_content(self) -> None:
        message = Message(role=Role.USER, content="What's the weather in Bangkok?")
        self.assertEqual(message.content, "What's the weather in Bangkok?")

    def test_debug(self) -> None:
        message = Message(
            role=Role.USER,
            content="What's the weather in Bangkok?",
            remote=Message._Remote(
                id="1",
                event=self.event,
                debug={
                    "chosenModuleResponse": 'ExternalModule { "language": "French" }',
                },
            ),
        )

        self.assertEqual(message.debug, {"chosenModuleResponse": 'ExternalModule { "language": "French" }'})

        message = Message(role=Role.USER, content="What's the weather in Bangkok?")

        self.assertEqual(message.debug, {})

    def test_append(self) -> None:
        message = Message(role=Role.USER, content="What's the weather in Bangkok?")
        message.append("This is an assistant message.")
        self.assertEqual(message.content, "What's the weather in Bangkok?\n\nThis is an assistant message.")

        message = Message(role=Role.USER, content="What's the weather in Bangkok?")
        message.append("This is an assistant message.", new_line=False)
        self.assertEqual(message.content, "What's the weather in Bangkok?This is an assistant message.")

    def test_id(self) -> None:
        message = Message(
            role=Role.USER,
            content="What's the weather in Bangkok?",
            remote=Message._Remote(
                id="1",
                event=self.event,
                debug={
                    "chosenModuleResponse": 'ExternalModule { "language": "French" }',
                },
            ),
        )

        self.assertEqual(message.id, "1")

        self.assertIsNone(Message(role=Role.USER, content="What's the weather in Bangkok?").id)

    def test_language(self) -> None:
        message_without_lang = Message(role=Role.USER, content="What's the weather in Bangkok?")

        message_with_lang = Message(
            role=Role.USER,
            content="Quelle est la météo à Bangkok?",
            remote=Message._Remote(
                id="1",
                event=self.event,
                debug={
                    "chosenModuleResponse": 'ExternalModule { "language": "French" }',
                },
            ),
        )

        self.assertEqual(message_with_lang.language, "French")
        self.assertEqual(message_without_lang.language, "English")

    def test_constructor(self) -> None:
        with self.assertRaises(MessageFormatError) as e:

            class InvalidRole:
                value = "INVALID_ROLE"

            invalid_role = cast(Role, InvalidRole)
            Message(role=invalid_role, content="What's the weather in Bangkok?", tool_call_id="tc1")
        self.assertEqual(str(e.exception), f"BL::Model::Message::init::InvalidRole::{InvalidRole.value}")

        with self.assertRaises(MessageFormatError) as e:
            Message(role=Role.TOOL, content="What's the weather in Bangkok?")
        self.assertEqual(str(e.exception), "BL::Model::Message::init::ToolMessageWithoutToolCallId")

        with self.assertRaises(MessageFormatError) as e:
            Message(role=Role.USER, content="What's the weather in Bangkok?", tool_calls=[{"id": "tc1"}])
        self.assertEqual(str(e.exception), "BL::Model::Message::init::NonAssistantMessageWithToolCalls")


if __name__ == "__main__":
    unittest.main()
