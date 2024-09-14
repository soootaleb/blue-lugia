from datetime import datetime
from blue_lugia.app import App
from blue_lugia.models import ExternalModuleChosenEvent, Message

OPENAI_API_KEY = "***"

state = App("Petal").threaded(False).create_state(ExternalModuleChosenEvent(**{
    "id": "event_001",
    "version": "1.0",
    "event": "ModuleChosen",
    "created_at": datetime.now(),
    "user_id": "user_123",
    "company_id": "company_456",
    "payload": {
        "name": "ReportAssistant",
        "description": "Generates reports based on user input.",
        "configuration": {
            "language": "English",
            "report_type": "Summary"
        },
        "chat_id": "chat_001",
        "assistant_id": "assistant_001",
        "user_message": {
            "id": "user_msg_001",
            "text": "Can you assist me with the report?",
            "created_at": datetime.now()
        },
        "assistant_message": {
            "id": "assistant_msg_001",
            "created_at": datetime.now()
        }
    }
}))

state._llm = state.llm.oai(OPENAI_API_KEY).using("gpt-4o")

@state.simple(model="gpt-4o")
def hello(name: str):
  """Say hello to the user name and commment on the completion"""

  completion = state.llm.complete([Message.SYSTEM("Anser the user"), Message.USER("What's your name?")])

  return f"My name is {name}. Your completion was {completion.content}. Repeat it."

message = hello("Sam Altman")

print(message.content)