from pydantic import BaseModel, Field

from blue_lugia.app import App
from blue_lugia.config import ModuleConfig
from blue_lugia.enums import Role
from blue_lugia.models import Message
from blue_lugia.state import StateManager


class SearchInFile(BaseModel):
    """Use this tool to search data in an uploaded file."""

    search: str = Field(..., description="The text to search in the file.")
    file_name: str = Field(..., description="The name of the file to search in.")

    def run(self, call_id: str, state: StateManager, extra: dict, out: Message, *args) -> Message | None:
        sources = state.files.uploaded.filter(key=self.file_name).search(self.search).truncate(1000)

        return state.llm.complete(
            completion_name="tool",
            messages=[
                Message.SYSTEM("Your must always cite your sources using [source0], [source1], [source2], etc. The sources available are:"),
                Message.SYSTEM(sources.xml()),
                Message.USER(self.search),
            ],
            out=out,
            start_text=out.content or ""
        )

    def post_run_hook(self, *args) -> bool:
        return False


def module(state: StateManager[ModuleConfig]) -> None:
    files_names = ", ".join([file["name"] for file in state.files.uploaded.values("name")])

    state.context(
        [
            Message.SYSTEM("After a tool call, you must keep the sources cited by the tool as-is."),
            Message.SYSTEM(f"The available uploaded files are: {files_names}"),
        ],
        prepend=True,
    ).register(SearchInFile).loop(out=state.last_ass_message, completion_name="root")

    return


app = App("Petal").threaded(False).of(module).listen()
