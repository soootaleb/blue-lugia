from blue_lugia.config import ModuleConfig
from blue_lugia.state import StateManager


def replay(state: StateManager[ModuleConfig]) -> bool:
    """
    Unstable.
    The module will actually execute at the end of this command
    The command does not do anything, except making the module actually execute
    """

    return True
