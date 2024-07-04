import datetime
from typing import Optional

from pydantic import BaseModel, Field

from blue_lugia.app import App
from blue_lugia.config import ModuleConfig
from blue_lugia.models import Message
from blue_lugia.models.event import AssistantMessage, ExternalModuleChosenEvent, Payload, UserMessage
from blue_lugia.state import StateManager


class CommandError(Exception):
    def handle(self, state: StateManager) -> None:
        state.last_ass_message.append(f"Woopsies, here is a command error: {self}")


class CustomConfig(ModuleConfig):
    TEST_MESSAGE: str = "CustomConfig"
    IN_MESSAGE: str = "InMessage"


class SumTool(BaseModel):
    """Add two numbers"""

    x: int = Field(..., description="first value")
    y: int = Field(..., description="second value")

    def run(self, call_id: str, state: StateManager, *args, **kwargs) -> int:
        # state.last_ass_message.update(f"The sum of {self.x} and {self.y} is {self.x + self.y}")
        return self.x + self.y

    def post_run_hook(self, call_id: str, state: StateManager, *args, **kwargs) -> Optional[bool]:
        pass
        # return False

    @classmethod
    def on_validation_error(cls, call_id: str, arguments: dict, state: StateManager, extra: dict | None = None, out: Message | None = None) -> bool:
        if extra is None:
            extra = {}
        validation_error = extra.get("validation_error")
        state.last_ass_message.append(f"Tool {cls.__name__} not called because of validation error {validation_error}")
        return False


def hello(state: StateManager[CustomConfig], args: list[str] = []) -> None:
    """
    Just say hello
    """
    state.last_ass_message.update(f"World: {', '.join(args)}")

    raise CommandError(f"Bye world ({state.conf.TEST_MESSAGE}, {state.conf.IN_MESSAGE})")


def add(state: StateManager[CustomConfig], args: list[str] = []) -> None:
    # state._llm = state.llm.oai(state.conf.OPENAI_API_KEY).using("gpt-4o")

    state.context([Message.SYSTEM("Your role is to make a tool call to add the two numbers provided by the user"), Message.USER(" ".join(args))]).register(SumTool).loop(
        tool_choice=SumTool
    )


def module(state: StateManager) -> None:
    state.complete(out=state.last_ass_message)


app = App("Petal").configured(CustomConfig).register("hello", hello).register("add", add).handle(CommandError).threaded(False).of(module).listen()
