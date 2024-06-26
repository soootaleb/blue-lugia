from blue_lugia.config import ModuleConfig
from blue_lugia.state import StateManager

"""
Execute arbitrary commands
"""


def clear(state: StateManager[ModuleConfig], *args: list[str]) -> None:
    """
    Clear the chat, remove all messages.
    Does not remove uploaded files.
    """

    state.last_ass_message.update("You'll need to refresh the page.")

    state.clear()
