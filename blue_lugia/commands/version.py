import inspect
import json
import os
from typing import Callable

import toml

from blue_lugia.app import App
from blue_lugia.config import ModuleConfig
from blue_lugia.state import StateManager

"""
Returns versions
"""


def version(state: StateManager[ModuleConfig], *args: list[str]) -> None:
    """
    Return versions by looking for a pyproject.toml file in the parent directory of the module file.
    """

    version = {}

    app: App = state.app

    if app._module:
        module: Callable = app._module
        module_file_path = inspect.getfile(module)
        parent = os.path.dirname(module_file_path)

        if not os.path.exists(os.path.join(parent, "pyproject.toml")):
            parent = os.path.dirname(parent)

        pyproject = os.path.join(parent, "pyproject.toml")

        try:
            with open(pyproject) as file:
                version = toml.load(file)
        except FileNotFoundError:
            state.logger.debug(f"Could not find pyproject.toml in {parent}")
            pass

    state.last_ass_message.append(f"```json\n{json.dumps(version, indent=2, ensure_ascii=False)}")
