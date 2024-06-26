import datetime

from blue_lugia.models.event import AssistantMessage, ExternalModuleChosenEvent, Payload, UserMessage


class MockEvent(ExternalModuleChosenEvent):
    @classmethod
    def create(cls) -> "MockEvent":
        return cls(
            id="evt_mock_id",
            version="1.0.0",
            event="unique.chat.external-module.chosen",
            created_at=datetime.datetime.now(),
            user_id="user_mock_id",
            company_id="company_mock_id",
            payload=Payload(
                name="mock_module",
                description="Mock module",
                configuration={"key": "value"},
                chat_id="chat_mock_id",
                assistant_id="assistant_mock_id",
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
