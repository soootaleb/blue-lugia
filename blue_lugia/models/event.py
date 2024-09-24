import datetime
from typing import Any, Optional

from pydantic import BaseModel


class UserMessage(BaseModel):
    id: str
    text: str
    created_at: datetime.datetime


class AssistantMessage(BaseModel):
    id: str
    created_at: datetime.datetime


class ToolParameters(BaseModel):
    language: str


class UserMetadata(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: str


class Payload(BaseModel):
    name: str
    description: str
    configuration: dict[str, Any]
    chat_id: Optional[str]
    assistant_id: str
    user_message: UserMessage
    assistant_message: AssistantMessage
    tool_parameters: ToolParameters
    user_metadata: UserMetadata


class ExternalModuleChosenEvent(BaseModel):
    id: str
    version: str
    event: str
    created_at: datetime.datetime
    user_id: str
    company_id: str
    payload: Payload
