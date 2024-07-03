from pydantic import BaseModel, Field

from blue_lugia.managers import LanguageModelManager
from blue_lugia.models import Message
from blue_lugia.state import StateManager

"""
Playground for experimenting with the assistant
"""


class MockLLM(LanguageModelManager):
    def complete(
        self,
        out: Message | None = None,
        *args,
        **kwargs,
    ) -> Message:
        mock = kwargs.get("mock", False)

        if mock:
            if out:
                out.content = "Mock content"
                out._tool_calls = [
                    {
                        "id": "mock_id1",
                        "type": "function",
                        "function": {
                            "name": "SummarizeTool",
                            "arguments": {"document_id": "cont_mtgwqtiyguxh6ucbrtn7rjck"},
                        },
                    },
                    {
                        "id": "mock_id2",
                        "type": "function",
                        "function": {
                            "name": "SummarizeTool",
                            "arguments": {"document_id": "cont_mtgwqtiyguxh6ucbrtn7rjck"},
                        },
                    },
                ]

            return Message.ASSISTANT(
                content="Mock content",
                remote=(
                    Message._Remote(
                        id=out._remote.id,
                        event=out._remote.event,
                        debug=out._remote.debug,
                    )
                    if out and out._remote
                    else None
                ),
                tool_calls=[
                    {
                        "id": "mock_id1",
                        "type": "function",
                        "function": {
                            "name": "SummarizeTool",
                            "arguments": {"document_id": "cont_mtgwqtiyguxh6ucbrtn7rjck"},
                        },
                    },
                    {
                        "id": "mock_id2",
                        "type": "function",
                        "function": {
                            "name": "SummarizeTool",
                            "arguments": {"document_id": "cont_mtgwqtiyguxh6ucbrtn7rjck"},
                        },
                    },
                ],
                logger=self.logger.getChild(Message.__name__),
            )
        else:
            return super().complete(out=out, *args, **kwargs)


class SummarizeTool(BaseModel):
    """
    Summarize the document asked by the user.
    This tool must be used to identify the document identifier that relates to the user query.
    It's mandatory that the document id provided is available in the list provided.
    """

    document_id: str = Field(..., description="the document id to summarize")

    def pre_run_hook(
        self,
        call_id: str,
        state: StateManager,
        extra: dict | None = None,
        out: Message | None = None,
    ) -> None:
        """
        If this method returns False, the tool will not run.
        The post run hook will still be called.
        """

        if extra is None:
            extra = {}

        all_tool_calls = extra["tool_calls"]

        summarize_tool_calls = list(
            filter(
                lambda x: x["function"]["name"] == self.__class__.__name__,
                all_tool_calls,
            )
        )

        summarize_tool_calls_count = len(summarize_tool_calls)

        break_loop = summarize_tool_calls_count == 1

        extra["break_loop"] = break_loop

    def run(
        self,
        call_id: str,
        state: StateManager,
        extra: dict | None = None,
        out: Message | None = None,
    ) -> Message | dict | str | None:
        """
        A tool should always return a viable response.
        That's because the context must always have tool messages after tool calls.
        If the tool is called and it doesn't return a message, the context will be empty.
        If this method returns False, it'll still be added to the context.

        This method can technically alter the state.ctx but it's not recommended.

        If you want a potential loop of completions to be stoped, return False in the Tool.post_run_hook method.

        Return:
            - Message
            - dict
            - str
            - None
        """

        if extra is None:
            extra = {}

        document = state.files.get_by_id(self.document_id)

        if not document:
            return "_Document not found_"
        else:
            document = document.truncate(500)

        return state.llm.complete(
            messages=[
                Message.SYSTEM("Your role is to summarize the document."),
                Message.USER(document.content),
            ],
            search_context=document.as_context(),
            out=out if extra["break_loop"] else None,
        )

    def post_run_hook(
        self,
        call_id: str,
        state: StateManager,
        extra: dict | None = None,
        out: Message | None = None,
    ) -> bool:
        """
        If this method returns False, the loop over tools will not continue.
        Returned messages are still added to the context
        """
        if extra is None:
            extra = {}

        return not extra.get("break_loop")


def play(state: StateManager, args: list[str] = []) -> None:
    """
    Development purpose only, use at your own risk
    """

    files = state.files.uploaded.values("id", "name")

    state.context(
        # Message.SYSTEM(f"The documents available are {files}"), prepend=True
        [
            Message.SYSTEM(f"The documents available are {files}"),
            Message.USER("Summarize the document two times using tools."),
        ],
    ).register(SummarizeTool)

    # .loop(
    #     out=state.last_ass_message,
    # )

    completion = state.complete(out=state.last_ass_message)

    state.call(
        completion,
        out=state.last_ass_message,
        extra={
            "tool_calls": completion.tool_calls,
            "loop_iteration": 0,
        },
    )

    # state.stream()

    # files = state.files.uploaded.search().as_files()

    # if not files:
    #     raise

    # state.llm.complete(
    #     [
    #         Message.SYSTEM("Your role is to provide a reference to the document that answers the user's question"),
    #         Message.SYSTEM("Here are the sources you must cite using source0, source1, source2, etc:"),
    #         Message.SYSTEM(files.xml),
    #         Message.USER("Provide one quote from the Earth and cite a source."),
    #     ],
    #     out=state.last_ass_message,
    #     search_context=files.as_context(),
    # )

    return
