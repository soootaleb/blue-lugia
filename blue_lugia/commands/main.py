import importlib

from blue_lugia.config import ConfType
from blue_lugia.state import StateManager


def command(state: StateManager[ConfType], command: list[str]) -> bool:
    command_result = False

    try:
        module = importlib.import_module(f"blue_lugia.commands.{command[0]}")

        if len(command) == 1:
            function = getattr(module, command[0])
            command_result = function(state)
        else:
            if hasattr(module, command[1]):
                function = getattr(module, command[1])
                command_result = function(state, command[2:])
            elif hasattr(module, command[0]):
                function = getattr(module, command[0])
                command_result = function(state, command[1:])

    except ModuleNotFoundError as e:
        state.last_ass_message.update(f"Command not found: {command[0]}")

        raise e

    except AttributeError as e:
        state.last_ass_message.update(f"Function not found: {command[1]}")

        raise e

    return command_result
