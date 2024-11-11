import datetime

from blue_lugia.models.event import AssistantMessage, ExternalModuleChosenEvent, Payload, ToolParameters, UserMessage, UserMetadata


class MockEvent(ExternalModuleChosenEvent):
    @classmethod
    def create(cls, company_id: str = "company_mock_id", user_id: str = "user_mock_id") -> "MockEvent":
        return cls(
            id="evt_mock_id",
            version="1.0.0",
            event="unique.chat.external-module.chosen",
            created_at=datetime.datetime.now(),
            user_id=user_id,
            company_id=company_id,
            payload=Payload(
                name="mock_module",
                description="Mock module",
                configuration={"key": "value"},
                chat_id="chat_mock_id",
                assistant_id="assistant_mock_id",
                user_metadata=UserMetadata(username="admin", first_name="admin", last_name="admin", email="admin@admin.com"),
                tool_parameters=ToolParameters(language="en"),
                user_message=UserMessage(
                    id="user_message_mock_id",
                    text="User message",
                    created_at=datetime.datetime.now(),
                ),
                assistant_message=AssistantMessage(
                    id="assistant_message_mock_id",
                    created_at=datetime.datetime.now(),
                ),
            ),
        )
