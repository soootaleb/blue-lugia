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
    Returns the version of blue-lugia
    """

    # target pyproject.toml that is in the lib

    current_script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(current_script_path)
    project_root = os.path.dirname(os.path.dirname(script_dir))
    pyproject_toml_path = os.path.join(project_root, "pyproject.toml")

    with open(pyproject_toml_path) as file:
        data = toml.load(file)

    version = {
        "blue-lugia": data["tool"]["poetry"]["version"],
    }

    app: App = state.app

    if app._module:
        module: Callable = app._module
        module_file_path = inspect.getfile(module)
        parent = os.path.dirname(os.path.dirname(module_file_path))
        pyproject = os.path.join(parent, "pyproject.toml")

        try:
            with open(pyproject) as file:
                data = toml.load(file)
                version[app.name] = data["tool"]["poetry"]["version"]
        except FileNotFoundError:
            state.logger.debug(f"Could not find pyproject.toml in {parent}")
            pass

    state.last_ass_message.append(f"```json\n{json.dumps(version, indent=2)}")
