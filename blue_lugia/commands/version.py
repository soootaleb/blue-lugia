import inspect
import json
import os
from typing import Callable

import toml

from blue_lugia.app import App
from blue_lugia.config import ModuleConfig
from blue_lugia.state import StateManager
from blue_lugia.utils import get_version

"""
Returns versions
"""


def version(state: StateManager[ModuleConfig], *args: list[str]) -> None:
    """
    Display the versions of the module.
    """

    version = get_version(state, *args)

    if version is not None:
        state.last_ass_message.append(
            f"```json\n{json.dumps(version, indent=2, ensure_ascii=False)}"
        )
    else:
        state.last_ass_message.append("Error fetching version!")
