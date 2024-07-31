from typing import TypeVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class ModuleConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # required
    API_KEY: str = ""
    APP_ID: str = ""
    API_BASE: str = ""
    ENDPOINT_SECRET: str = ""

    # optional
    PREVENT_ASYNC_EXEC: str = ""

    # dev purpose
    COMPANY_ID: str = ""
    SCOPE_ID: str = ""
    USER_ID: str = ""

    # Top-level LLM for the assistant
    # NOTE: We use camelCase here to align with the other
    # language model configurations, but we use snake_case
    # elsewhere in the codebase b/c it's more Pythonic.
    languageModel: str | None = None

    ALLOW_COMMANDS: str | bool | None = None
    ON_FAILURE_MESSAGE_OVERRIDE: str | None = None
    ON_FAILURE_DISPLAY_ERROR: str | bool | None = None

    # Message history
    CONTEXT_WINDOW_TOKEN_LIMIT: int | None = None
    CONTEXT_WINDOW_N_MIN_MESSAGES: int = 2
    CONTEXT_WINDOW_N_MAX_MESSAGES: int = 10

    # Function calling
    FUNCTION_CALL_MAX_ITERATIONS: int = 5

    # Failure message
    ON_FAILURE: str = """Sorry, I was unable to resolve your request.
            Please try rephrasing your question or asking another question.
            If this message persists, you may try starting a new conversation.
        """.strip()

    # LLM
    LLM_TIMEOUT: int = 60000
    LLM_DEFAULT_MODEL: str = "AZURE_GPT_4_TURBO_2024_0409"


ConfType = TypeVar("ConfType", bound=ModuleConfig)
