from typing import Any, Dict, Literal, Set, TypeVar

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
    languageModel: str | None = None  # noqa: N815

    ALLOW_COMMANDS: str | bool | None = None
    ON_FAILURE_MESSAGE_OVERRIDE: str | None = None
    ON_FAILURE_DISPLAY_ERROR: str | bool | None = None

    # Message history
    CONTEXT_WINDOW_TOKEN_LIMIT: int | None = None
    CONTEXT_WINDOW_N_MIN_MESSAGES: int = 2
    CONTEXT_WINDOW_N_MAX_MESSAGES: int = 10

    # Function calling
    FUNCTION_CALL_MAX_WORKERS: int = 4
    FUNCTION_CALL_MAX_ITERATIONS: int = 5

    # Failure message
    ON_FAILURE: str = """😔 Sorry, I was unable to resolve your request.
            Please try rephrasing your question or asking another question.
            If this message persists, you may try starting a new conversation.
        """.strip()

    # LLM
    LLM_SEED: int | None = None
    LLM_TIMEOUT: int = 60000
    LLM_TEMPERATURE: float = 0.0
    LLM_DEFAULT_MODEL: str = "AZURE_GPT_4_TURBO_2024_0409"
    LLM_ALLOW_STREAMING: bool = True

    def model_dump(
        self,
        *,
        mode: str = "python",
        include: Set[int] | Set[str] | Dict[int, Any] | Dict[str, Any] | None = None,
        exclude: Set[int] | Set[str] | Dict[int, Any] | Dict[str, Any] | None = {
            "API_KEY",
            "ENDPOINT_SECRET",
        },
        context: Any | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal["none"] | Literal["warn"] | Literal["error"] = True,
        serialize_as_any: bool = False,
    ) -> dict[str, Any]:
        return super().model_dump(
            mode=mode,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )

    def model_dump_json(
        self,
        *,
        indent: int | None = None,
        include: Set[int] | Set[str] | Dict[int, Any] | Dict[str, Any] | None = None,
        exclude: Set[int] | Set[str] | Dict[int, Any] | Dict[str, Any] | None = {
            "API_KEY",
            "ENDPOINT_SECRET",
        },
        context: Any | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal["none"] | Literal["warn"] | Literal["error"] = True,
        serialize_as_any: bool = False,
    ) -> str:
        return super().model_dump_json(
            indent=indent,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )


ConfType = TypeVar("ConfType", bound=ModuleConfig)
