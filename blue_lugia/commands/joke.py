from blue_lugia.config import ModuleConfig
from blue_lugia.models import Message
from blue_lugia.state import StateManager

"""
Makes a joke
"""


def joke(state: StateManager[ModuleConfig], *args: list[str]) -> None:
    """
    Returns a random joke.
    """

    state.context(
        [
            Message.USER("Tell me a joke"),
        ]
    ).complete(out=state.last_ass_message)
