import importlib
import inspect
import pkgutil

from blue_lugia.config import ModuleConfig
from blue_lugia.state import StateManager

IGNORED_MODULES = [
    "blue_lugia.commands.main",
]


def _ignore_module(module_name: str) -> bool:
    """
    Determine if the specified module should be ignored.

    Args:
        module_name (str): The name of the module to check.

    Returns:
        bool: True if the module should be ignored, False otherwise.
    """
    return module_name.startswith("_") or module_name in IGNORED_MODULES


def _ignore_function(function_name: str) -> bool:
    """
    Determine if the specified function should be ignored.

    Args:
        function_name (str): The name of the function to check.

    Returns:
        bool: True if the function should be ignored, False otherwise.
    """
    return function_name.startswith("_")


def _generate_docs(package: str) -> str:
    """
    Generate a markdown documentation string for all modules and their functions in the specified package.

    Args:
        package (str): The package name to document.

    Returns:
        str: The generated markdown documentation string.
    """
    docs = [
        "# Available commands\n"
        "Commands are special messages that start with an exclamation point (!)\n\n"
        "The general syntax is `!module function arg1 arg2`.\n\n"
        "Do not prefix the module name with `blue_lugia.commands`.\n\n"
        "If you don't provide the function, it will call the default function.\n\n"
        "For example if you want to clear the chat, you would type `!clear clear` or equivalend `!clear`.\n\n"
    ]

    # Import the base package
    base_package = importlib.import_module(package)

    # Iterate over all modules in the package
    for _, module_name, _ in pkgutil.walk_packages(base_package.__path__, base_package.__name__ + "."):
        if _ignore_module(module_name):
            continue

        module = importlib.import_module(module_name)

        docs.append(f"## Module `{module_name}`\n")
        module_doc = inspect.getdoc(module)
        if module_doc:
            docs.append(f"{module_doc}\n")

        functions = inspect.getmembers(module, inspect.isfunction)
        for function_name, function in functions:
            if _ignore_function(function_name) or function.__module__ != module_name:
                continue

            docs.append(f"### Function `{function_name}`\n")
            function_doc = inspect.getdoc(function)
            if function_doc:
                docs.append(f"{function_doc}\n")
            else:
                docs.append("No documentation available.\n")
            docs.append("\n")

    return "\n".join(docs)


def help(state: StateManager[ModuleConfig], *args: list[str]) -> None:
    """
    Generate and display documentation for all modules and functions in the `blue_lugia.commands` package.
    """

    state.last_ass_message.update(_generate_docs("blue_lugia.commands"))
