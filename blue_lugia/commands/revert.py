from blue_lugia.config import ModuleConfig
from blue_lugia.state import StateManager

"""
Remove messages from the conversation to revert the chat into a previous state
"""


def revert(state: StateManager[ModuleConfig], args: list[str] = []) -> None:
    """
    Removes the last N couples of (user question, assistant answer).
    """

    pairs_to_remove = 1

    if len(args):
        try:
            pairs_to_remove = int(args[0])
        except Exception:
            state.last_ass_message.update("Failed to parse the provided argument(s)")

    pairs_to_remove += 1

    for _ in range(0, pairs_to_remove):
        state.messages.all(force_refresh=True)

        state.last_ass_message.delete()
        state.last_usr_message.delete()
