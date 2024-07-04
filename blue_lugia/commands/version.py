import os

import toml

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
    pyproject_toml_path = os.path.join(project_root, 'pyproject.toml')

    with open(pyproject_toml_path) as file:
        data = toml.load(file)

    version = data["tool"]["poetry"]["version"]

    state.last_ass_message.append(version)
