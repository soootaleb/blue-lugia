import datetime
from typing import Optional

from pydantic import Field, field_validator

from blue_lugia.app import App
from blue_lugia.config import ModuleConfig
from blue_lugia.enums import Role
from blue_lugia.orm.driver import CSVDriver, ExcelDriver
from blue_lugia.orm.model import Message as ORMMessage
from blue_lugia.orm.model import Model
from blue_lugia.orm.source import BLFileDataSource, BLMessageManagerDataSource, UniqueDataSource
from blue_lugia.state import StateManager


def module(state: StateManager[ModuleConfig]) -> None:
    # metrics_file = state.files.filter(key="dora.fields.xlsx").fetch().first()
    # people_file = state.files.filter(key="PEOPLE.csv").fetch().first()
    # bonds_file = state.files.filter(key="bonds.csv").fetch().first()

    # if not metrics_file or not people_file or not bonds_file:
    #     raise Exception("File not found")

    # class Metric(Model):
    #     class Meta:
    #         table = "v0"

    #     field: Optional[str | float] = Field(...)
    #     rag: Optional[str | float] = Field(...)
    #     type: Optional[str | float] = Field(...)
    #     prompt: Optional[str | float] = Field(...)
    #     chunks_mode: Optional[str | float] = Field(...)
    #     deps: Optional[str | float] = Field(...)

    # class Person(Model):
    #     FIRST_NAME: str = Field(...)
    #     LAST_NAME: str = Field(...)
    #     DIV_NAME: str = Field(...)

    # class Bond(Model):
    #     isin: str = Field(..., alias="ISIN")
    #     issuer: str = Field(..., alias="Issuer")
    #     instrument_name: str = Field(..., alias="Instrument Name")

    # class Memory(Model):
    #     message: str = Field(...)

    # Memory.objects.create(Memory(message="Hello, world"))
    # Memory.objects.create(Memory(message="Bye, world"))
    # Memory.objects.create(Memory(message="Just world"))

    # messages = Memory.objects.all()

    # Metrics = Metric.sourced(BLFileDataSource(metrics_file)).driven(ExcelDriver())  # noqa: N806, F841
    # People = Person.sourced(BLFileDataSource(people_file)).driven(CSVDriver())  # noqa: N806, F841
    # Bonds = Bond.sourced(BLFileDataSource(bonds_file)).driven(CSVDriver())  # noqa: N806, F841

    # Messages = ORMMessage.sourced(BLMessageManagerDataSource(state.messages))  # noqa: N806

    # messages = Messages.objects.all()  # noqa: F841

    # Messages.objects.create(ORMMessage(role="assistant", content="Hello, world", original_content="Hello"))

    class ChatMessage(Model):
        id: str = Field(...)
        role: Role = Field(...)
        content: Optional[str] = Field(default=None, alias="text")

        @field_validator("role", mode="before")
        @classmethod
        def validate_role(cls, v: str) -> Role:
            return Role(v.lower())

        class Config:
            table = "unique_sdk.Message.list"

    chat = ChatMessage.sourced(UniqueDataSource(state.event))

    messages = chat.objects.all()


app = App("Petal").threaded(False).of(module).listen()  # .webhook(chat_id="chat_jnxlggqgif6ckssek103khwq", assistant_id="assistant_y4j9d9h0yoa2f084qp9jknxi")
