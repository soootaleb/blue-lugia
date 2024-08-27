from pydantic import BaseModel, Field

from blue_lugia.app import App
from blue_lugia.config import ModuleConfig
from blue_lugia.models import Message
from blue_lugia.state import StateManager


class CitedSourcesFromToolMessage(BaseModel):
    """Use this tool to add a tool message that cites sources that won't appear in the context later."""

    search: str = Field(..., description="The text to search in the file.")
    file_name: str = Field(..., description="The name of the file to search in.")

    def run(self, call_id: str, state: StateManager, extra: dict, out: Message, *args) -> Message | None:
        sources = state.files.uploaded.filter(key=self.file_name).search(self.search).truncate(1000)

        state.last_ass_message.append("_Using CitedSourcesFromToolMessage_")

        completion = state.llm.complete(
            completion_name="tool",
            messages=[
                Message.SYSTEM("Your must always cite your sources using [source0], [source1], [source2], etc."),
                Message.SYSTEM("The sources available are:"),
                Message.SYSTEM(sources.xml()),
                Message.USER(self.search),
            ],
        )

        return state.llm.complete(
            completion_name='summarize',
            messages=[
                Message.SYSTEM("Your role is to summarize the user message and keep the cited sources as-is."),
                Message.USER(completion.content, sources=completion.sources),
            ],
        )


class CitedSourcesStreamed(BaseModel):
    """Use this tool to trigger a completion citing sources but without a completion after."""

    search: str = Field(..., description="The text to search in the file.")
    file_name: str = Field(..., description="The name of the file to search in.")

    def run(self, call_id: str, state: StateManager, extra: dict, out: Message, *args) -> bool:
        sources = state.files.uploaded.filter(key=self.file_name).search(self.search).truncate(1000)

        state.last_ass_message.append("_Using CitedSourcesStreamed_")

        state.llm.complete(
            completion_name="tool",
            messages=[
                Message.SYSTEM("Your must always cite your sources using [source0], [source1], [source2], etc."),
                Message.SYSTEM("The sources available are:"),
                Message.SYSTEM(sources.xml()),
                Message.USER(self.search),
            ],
            out=out,
            start_text=out.content or "",
        )

        return False


class XMLSourcesFromToolMessage(BaseModel):
    """Use this tool to read an uploaded file."""

    file_name: str = Field(..., description="The name of the file to read.")

    def run(self, call_id: str, state: StateManager, extra: dict, out: Message, *args) -> str:
        state.last_ass_message.append("_Using XMLSourcesFromToolMessage_")
        return state.files.uploaded.filter(key=self.file_name).first().truncate(3000).xml()


def module(state: StateManager[ModuleConfig]) -> None:
    files_names = ", ".join([file["name"] for file in state.files.uploaded.values("name")])

    state.context(
        [
            Message.SYSTEM("Your role is to help the developer test the management of sources."),
            Message.SYSTEM("Your must always cite your sources using [source0], [source1], [source2], etc."),
            Message.SYSTEM("The sources are provided as XML tages like <source0>, <source1>, <source2>, etc."),
            Message.SYSTEM("You must follow the user instructions to retrieve information in various ways that will introduce sources in the context."),
            Message.SYSTEM(f"The available uploaded files are: {files_names}"),
        ],
        prepend=True,
    ).register([CitedSourcesFromToolMessage, CitedSourcesStreamed, XMLSourcesFromToolMessage]).loop(out=state.last_ass_message, completion_name="root")

    return


app = App("Petal").threaded(False).of(module) # .listen()
