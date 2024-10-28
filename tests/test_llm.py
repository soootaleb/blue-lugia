import re
import unittest

import unique_sdk

from blue_lugia.enums import Role
from blue_lugia.managers.llm import LanguageModelManager
from blue_lugia.managers.message import MessageManager
from blue_lugia.models.message import Message, MessageList
from tests.mocks.app import MockApp
from tests.mocks.event import MockEvent


class TestState(unittest.TestCase):
    def setUp(self) -> None:
        class MockMessageManager(MessageManager):
            def all(self, force_refresh: bool = False) -> MessageList:
                return MessageList(
                    [],
                    tokenizer=self.tokenizer,
                    logger=self.logger,
                )

        class MockLanguageModelManager(LanguageModelManager):
            def complete(self, *args, **kwargs) -> Message:
                return Message.ASSISTANT("DEFAULT_MOCK_ANSWER")

        self.state = MockApp("Tester").using(MockLanguageModelManager).using(MockMessageManager).create_state(MockEvent.create())

    def test_reformat(self) -> None:
        messages = MessageList(
            [
                Message.USER("Hello!"),
                Message.ASSISTANT("Hi!"),
            ],
            tokenizer=self.state.llm.tokenizer,
        )

        reformated = self.state.llm._reformat(messages)

        self.assertEqual(len(reformated), 2)
        self.assertEqual(reformated[0].role, Role.USER)
        self.assertEqual(reformated[1].role, Role.ASSISTANT)
        self.assertEqual(reformated[0].content, "Hello!")
        self.assertEqual(reformated[1].content, "Hi!")

        messages = MessageList(
            [
                Message.SYSTEM("SYS1"),
                Message.USER("Hello!"),
                Message.SYSTEM("SYS2"),
                Message.SYSTEM("SYS2"),
                Message.ASSISTANT("Hi!"),
            ],
            tokenizer=self.state.llm.tokenizer,
        )

        reformated = self.state.llm._reformat(messages)

        self.assertEqual(len(reformated), 3)
        self.assertEqual(reformated[0].role, Role.SYSTEM)
        self.assertEqual(reformated[0].content, "SYS1\nSYS2")
        self.assertEqual(reformated[1].role, Role.USER)
        self.assertEqual(reformated[1].content, "Hello!")
        self.assertEqual(reformated[2].role, Role.ASSISTANT)
        self.assertEqual(reformated[2].content, "Hi!")

    def _get_message(self, role: Role, content: str = "", citations: dict[str, int] | None = None, debug: dict | None = None) -> Message:
        return Message(
            role=role,
            content=content,
            citations=citations,
            tool_call_id="tool_call_id",
            remote=Message._Remote(
                event=MockEvent.create(),
                id=content,
                debug=debug or {},
            ),
        )

    def test_rereference_reindex(self) -> None:
        messages = MessageList(
            [
                Message.USER("What is the LAST sentence of the moon"),
                Message.ASSISTANT("I make a tool call to search for the first sentence of the moon"),
                Message.TOOL(
                    """<source4 id="4">First</source4>
                        <source10 id="10">Second</source10>
                        <source2 id="2">Third</source2>""",
                    tool_call_id="tool_call_id",
                ),
            ],
            tokenizer=self.state.llm.tokenizer,
        )

        rereferenced, existing_references, new_references = self.state.llm._rereference(messages)

        # We check that all XML sources are rewritten from 0 to n
        source_counter = 0
        for message in rereferenced:
            content = message.content
            sources = re.findall(r"<source\d+ id=\"\d+\">", content)
            for source in sources:
                source_id = int(re.findall(r"\d+", source)[0])
                self.assertEqual(source_id, source_counter)
                source_counter += 1

    def test_rereference_existing_and_new(self) -> None:
        messages = MessageList(
            [
                Message.USER("What is the SECOND sentence"),
                Message.ASSISTANT("I make a tool call to search for the SECOND sentence"),
                Message.TOOL(
                    """<source4 id="4">First</source4>
                        <source10 id="10">Second</source10>
                        <source2 id="2">Third</source2>""",
                    tool_call_id="tool_call_id",
                ),
                self._get_message(
                    Role.ASSISTANT,
                    content="The SECOND sentence is SECOND [source1]",  # Because the LLM has seen rereferenced messages, <source10> was <source1>
                    debug={
                        "_sources": [
                            unique_sdk.Integrated.SearchResult(id="4", chunkId="4", key="source_4", url="unique://content/4"),
                            unique_sdk.Integrated.SearchResult(id="10", chunkId="10", key="source_10", url="unique://content/10"),
                            unique_sdk.Integrated.SearchResult(id="2", chunkId="2", key="source_2", url="unique://content/2"),
                        ]
                    },
                ),
                Message.USER("What is the LAST sentence"),
                Message.ASSISTANT("I make a tool call to search for the LAST sentence"),
                Message.TOOL(
                    """<source60 id="60">ThirdLast</source60>
                        <source20 id="20">SecondLast</source20>
                        <source49 id="49">Last</source49>""",
                    tool_call_id="tool_call_id",
                ),
                self._get_message(
                    Role.ASSISTANT,
                    citations={
                        "[source5]": 1,
                    },
                    content="The LAST sentence is LAST [source5]",  # Because the LLM has seen rereferenced messages, <source10> was <source1>
                ),
            ]
        )

        rereferenced, existing_references, new_references = self.state.llm._rereference(messages)

        # We check that all XML sources are rewritten from 0 to n
        source_counter = 0
        for message in rereferenced:
            content = message.content
            sources = re.findall(r"<source\d+ id=\"\d+\">", content)
            for source in sources:
                source_id = int(re.findall(r"\d+", source)[0])
                self.assertEqual(source_id, source_counter)
                source_counter += 1

        # Check that existing_references only contains the references that appear in _sources
        first_reference, second_reference, last_reference = existing_references
        self.assertEqual(existing_references, messages.sources)
        self.assertEqual(first_reference.get("id"), "4")
        self.assertEqual(second_reference.get("id"), "10")
        self.assertEqual(last_reference.get("id"), "2")

        # We check that new_references only contains the new references that do not appear in _sources
        first_reference, second_reference, last_reference = new_references

        self.assertEqual(first_reference.get("id"), "60")
        self.assertEqual(second_reference.get("id"), "20")
        self.assertEqual(last_reference.get("id"), "49")

        self.assertIn("[source5]", rereferenced.last(lambda x: x.role == Role.ASSISTANT).content or "")

    def test_rereference_without_sources_in_context(self) -> None:
        messages = MessageList(
            [
                Message.USER("What is the SECOND sentence"),
                Message.ASSISTANT("I make a tool call to search for the SECOND sentence"),
                Message.TOOL(
                    """<source4 id="4">First</source4>
                        <source10 id="10">Second</source10>
                        <source2 id="2">Third</source2>""",
                    tool_call_id="tool_call_id_1",
                ),
                self._get_message(
                    Role.ASSISTANT,
                    content="The SECOND sentence is SECOND [source1]",  # Because the LLM has seen rereferenced messages, <source10> was <source1>
                    debug={
                        "_sources": [
                            unique_sdk.Integrated.SearchResult(id="4", chunkId="4", key="source_4", url="unique://content/4"),
                            unique_sdk.Integrated.SearchResult(id="10", chunkId="10", key="source_10", url="unique://content/10"),
                            unique_sdk.Integrated.SearchResult(id="2", chunkId="2", key="source_2", url="unique://content/2"),
                        ]
                    },
                ),
                Message.USER("What is the LAST sentence"),
                Message.ASSISTANT("I make a tool call to search for the LAST sentence"),
                Message.TOOL(
                    """<source60 id="60">ThirdLast</source60>
                        <source20 id="20">SecondLast</source20>
                        <source49 id="49">Last</source49>""",
                    tool_call_id="tool_call_id_2",
                ),
                self._get_message(
                    Role.ASSISTANT,
                    content="The LAST sentence is LAST [source5]",
                    debug={
                        "_sources": [
                            unique_sdk.Integrated.SearchResult(id="60", chunkId="60", key="source_60", url="unique://content/60"),
                            unique_sdk.Integrated.SearchResult(id="20", chunkId="20", key="source_20", url="unique://content/20"),
                            unique_sdk.Integrated.SearchResult(id="49", chunkId="49", key="source_49", url="unique://content/49"),
                        ]
                    },
                ),
                Message.USER("Now make some citations with sources that will not be in the context later."),
                self._get_message(
                    Role.ASSISTANT,
                    content="This message cited sources that are not anymore in context: [source2], [source0]. e.g it was streamed from within a tool.",
                    citations={
                        "[source2]": 1,
                        "[source0]": 2,
                    },
                    debug={
                        "_sources": [
                            unique_sdk.Integrated.SearchResult(id="400", chunkId="400", key="source_400", url="unique://content/400"),
                            unique_sdk.Integrated.SearchResult(id="1000", chunkId="1000", key="source_1000", url="unique://content/1000"),
                            unique_sdk.Integrated.SearchResult(id="200", chunkId="200", key="source_200", url="unique://content/200"),
                        ]
                    },
                ),
                Message.USER("Now generate some XML again"),
                Message.ASSISTANT("I make a tool call to generate some XML"),
                Message.TOOL(
                    """<source1000 id="1000">1000</source1000>
                        <source2000 id="2000">2000</source2000>
                        <source3000 id="3000">3000</source3000>""",
                    tool_call_id="tool_call_id_3",
                ),
            ]
        )

        rereferenced, existing_references, new_references = self.state.llm._rereference(messages)

        search_context = existing_references + new_references

        self.assertEqual(len(search_context), 12)

        last_ass_content = rereferenced.last(lambda x: x.role == Role.ASSISTANT and x.content.startswith("This message cited sources that are not anymore in context")).content

        tool_call_2 = rereferenced.last(lambda x: x.tool_call_id == "tool_call_id_2").content

        self.assertIn("[source2]", last_ass_content or "")
        self.assertIn("[source0]", last_ass_content or "")

        # test re-indexing before any citations were made out of context
        self.assertIn("</source3>", tool_call_2 or "")
        self.assertIn("</source4>", tool_call_2 or "")
        self.assertIn("</source5>", tool_call_2 or "")

        tool_call_3 = rereferenced.last(lambda x: x.tool_call_id == "tool_call_id_3").content

        # test re-indexing after some citations were made based on out-of-context sources
        # the difficulty is to keep the counter correct with some sources referencing in-context and out-of-context
        self.assertIn("</source9>", tool_call_3 or "")
        self.assertIn("</source10>", tool_call_3 or "")
        self.assertIn("</source11>", tool_call_3 or "")


if __name__ == "__main__":
    unittest.main()
