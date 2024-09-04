from pydantic import BaseModel, Field

from blue_lugia.app import App
from blue_lugia.config import ModuleConfig
from blue_lugia.models import Message
from blue_lugia.state import StateManager


class Describe(BaseModel):
    """Use this tool if the user asks to describe an image. The user can provide the image as a URL or a file name"""

    image: str = Field(..., title="Can be the URL of an image of the name of a file provided by the user")
    is_file_name: bool = Field(False, title="If the image is a file name")

    def run(self, call_id: str, state: StateManager, extra: dict, *args) -> Message:
        image = state.files.filter(key=self.image).fetch().first() if self.is_file_name else self.image

        return state.llm.complete(
            [
                Message.SYSTEM("Your role is to help the user with the image provided"),
                Message.USER(state.last_usr_message.content, image=image),
            ],
            out=state.last_ass_message,
        )

    def post_run_hook(self, *args) -> bool:
        return False


def module(state: StateManager[ModuleConfig]) -> None:
    uploaded_files_names = state.files.uploaded.values("name", flat=True)

    state.context([Message.SYSTEM(f"Here is a list of uploaded files: {', '.join(uploaded_files_names)}")]).register(Describe).loop()


app = App("Petal").threaded(False).of(module)  # .listen()
