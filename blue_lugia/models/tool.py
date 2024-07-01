from typing import Any, Optional, TypedDict

from pydantic import BaseModel, ValidationError


class ToolExecution(TypedDict):
    pre_run_hook: Optional[Any]
    run: Optional[Any]
    post_run_hook: Optional[Any]


class ToolCalled(TypedDict):
    id: str
    tool: BaseModel
    call: ToolExecution


class ToolNotCalled(TypedDict):
    id: str
    tool: type[BaseModel]
    arguments: dict
    handled: Optional[Any]
    error: ValidationError
