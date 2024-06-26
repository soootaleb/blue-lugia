from blue_lugia.app import App
from blue_lugia.config import ModuleConfig
from blue_lugia.state import StateManager


class CommandError(Exception):
    def handle(self, state: StateManager) -> None:
        state.last_ass_message.append(f"Woopsies, here is a command error: {self}")


class CustomConfig(ModuleConfig):
    TEST_MESSAGE: str = "CustomConfig"
    IN_MESSAGE: str = "InMessage"


def module(state: StateManager) -> None:
    state.complete(out=state.last_ass_message)


def hello(state: StateManager[CustomConfig], args: list[str] = []) -> None:
    state.last_ass_message.update(f"World: {', '.join(args)}")

    raise CommandError(f"Bye world ({state.conf.TEST_MESSAGE}, {state.conf.IN_MESSAGE})")


app = App("Petal").configured(CustomConfig).register("hello", hello).handle(CommandError).threaded(False).of(module)
