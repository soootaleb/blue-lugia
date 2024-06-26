import datetime
from typing import Any

from pydantic import BaseModel


class UserMessage(BaseModel):
    id: str
    text: str
    created_at: datetime.datetime


class AssistantMessage(BaseModel):
    id: str
    created_at: datetime.datetime


class Payload(BaseModel):
    name: str
    description: str
    configuration: dict[str, Any]
    chat_id: str
    assistant_id: str
    user_message: UserMessage
    assistant_message: AssistantMessage


class ExternalModuleChosenEvent(BaseModel):
    id: str
    version: str
    event: str
    created_at: datetime.datetime
    user_id: str
    company_id: str
    payload: Payload
