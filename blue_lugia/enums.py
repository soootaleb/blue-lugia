from enum import Enum


class Role(Enum):
    USER = "user"
    TOOL = "tool"
    SYSTEM = "system"
    ASSISTANT = "assistant"


class Model(Enum):
    # AZURE_GPT_4_TURBO = "AZURE_GPT_4_TURBO_2024_0409"
    AZURE_GPT_35_TURBO_16K = "AZURE_GPT_35_TURBO_16K"
    AZURE_GPT_35_TURBO = "AZURE_GPT_35_TURBO_0613"
    AZURE_GPT_4_TURBO = "AZURE_GPT_4_TURBO_1106"
    AZURE_GPT_4_8K = "AZURE_GPT_4_0613"
    OPENAI_GPT_4_TURBO = "gpt-4-turbo-2024-04-09"
    OPENAI_GPT_4_O = "gpt-4o"


class SearchType(Enum):
    VECTOR = "VECTOR"
    COMBINED = "COMBINED"


class Op(Enum):
    OR = "OR"
    AND = "AND"
    NOT = "NOT"


class Truncate(Enum):
    """
    Truncate type

    - KEEP_START: Keep the n tokens from the start
    - KEEP_END: Keep the n tokens from the end
    - KEEP_INNER: Keep the n tokens in the middle of the list
    - KEEP_OUTER: Keep the outer n tokens of the list
    """

    KEEP_START = "KEEP_START"
    KEEP_END = "KEEP_END"
    KEEP_INNER = "KEEP_INNER"
    KEEP_OUTER = "KEEP_OUTER"
