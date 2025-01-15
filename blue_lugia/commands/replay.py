from blue_lugia.config import ModuleConfig
from blue_lugia.enums import Role
from blue_lugia.state import StateManager


def replay(state: StateManager[ModuleConfig]) -> bool:
    """
    Unstable.
    This command removes the last user message "/replay" and the associated empty assistant message.
    It'll execute the module after the command has done such cleanup.
    Use this command to replay your previous interactions.
    """

    if state.last_ass_message:
        state.last_ass_message.delete()

    if state.last_usr_message:
        previous_user_message = state.messages.last(lambda x: x.role == Role.USER and state.last_usr_message is not None and x.id != state.last_usr_message.id)
        if previous_user_message:
            state.last_usr_message.update(content=previous_user_message.content, debug=previous_user_message.debug, references=previous_user_message.sources)
        else:
            state.last_ass_message.update("I'm sorry, I don't have any previous message to replay.")

    return True
