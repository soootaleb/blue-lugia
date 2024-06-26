from typing import Any, Type

from pydantic import BaseModel

from blue_lugia.enums import ToolType


class Tool(BaseModel):
    class ToolFunction(BaseModel):
        class ToolFunctionCall(BaseModel):
            name: str
            arguments: dict[str, Any]

        name: str
        description: str
        parameters: Type[BaseModel]

    type: ToolType
    function: ToolFunction
