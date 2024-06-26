import json

from blue_lugia.config import ModuleConfig
from blue_lugia.state import StateManager


def set(state: StateManager[ModuleConfig], args: list[str] = []) -> None:
    """
    Define the value for a key in the storage.

    `!store set key value`
    """

    state.storage.set(args[0], args[1])

    state.last_ass_message.update(f"""```\n{json.dumps(state.storage.data, indent=2)}""")


def get(state: StateManager[ModuleConfig], args: list[str] = []) -> None:
    """
    Retrieve the value of a key in the storage

    `!store get key`

    Can be used to retrieve the whole store

    `!store get`
    """

    stored = state.storage.get(args[0]) if len(args) else state.storage.data

    state.last_ass_message.update(f"""```\n{json.dumps(stored, indent=2)}""")
