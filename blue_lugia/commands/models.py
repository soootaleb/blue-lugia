import json

from blue_lugia.config import ModuleConfig
from blue_lugia.state import StateManager

"""
Returns LLMs
"""


def models(state: StateManager[ModuleConfig], *args: list[str]) -> None:
    """
    Return models accepted by the LanguageModelManager
    """

    models = state.llm.models_names if len(args) and args[0] == "names" else state.llm.models

    state.last_ass_message.append(f"```json\n{json.dumps(models, indent=2, ensure_ascii=False)}")
