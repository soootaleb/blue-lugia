import json

from blue_lugia.config import ModuleConfig
from blue_lugia.state import StateManager


def prompt(state: StateManager[ModuleConfig], args: list[str] = []) -> None:
    """
    Defines what version of prompts to use

    It should correspond to a sheet name
    """

    if not len(args):
        state.last_ass_message.update("Please specify a prompt version")

    stored = state.storage.set("prompt_version", args[0]) if len(args) else state.storage.get("prompt_version")

    state.last_ass_message.update(f"""```\n{json.dumps(stored, indent=2, ensure_ascii=False)}""")
