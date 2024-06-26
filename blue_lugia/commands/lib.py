import os

from blue_lugia.config import ModuleConfig
from blue_lugia.models import Message
from blue_lugia.state import StateManager

"""
Execute arbitrary commands
"""


def lib(state: StateManager[ModuleConfig], args: list[str]) -> None:
    """
    Show how to use the blue lugia library
    """

    # current file location
    current_dir = os.path.dirname(os.path.realpath(__file__))
    parent_dir = os.path.dirname(current_dir)

    # list all files recursively of the blue lugia module
    files = [
        os.path.join(dp, f)
        for dp, dn, filenames in os.walk(parent_dir)
        for f in filenames
        if os.path.splitext(f)[1] == ".py"
    ]

    # concatenate all files content

    content = ""

    for file in files:
        with open(f"{file}") as f:
            content += f.read()

    state.context(
        [
            Message.SYSTEM("Your role is to help the user use the blue_lugia python library"),
            Message.SYSTEM("The code of the library is:"),
            Message.SYSTEM(content),
        ],
        append=True,
    ).complete(
        Message.USER(" ".join(args)),
        out=state.last_ass_message,
    )
