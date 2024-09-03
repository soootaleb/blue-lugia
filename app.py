import datetime
import time

from pydantic import BaseModel, Field

from blue_lugia.app import App
from blue_lugia.config import ModuleConfig
from blue_lugia.models import Message
from blue_lugia.state import StateManager


class DevTool(BaseModel):
    wait: int = Field(0, description="The time to wait before sending the message.")

    def pre_run_hook(self, call_id: str, state: StateManager, extra: dict, *args) -> None:
        state.last_ass_message.append(f"Call {call_id} in tool {id(self)} started at {datetime.datetime.now().strftime("%H:%M:%S.%f")}")

    def run(self, call_id: str, state: StateManager, extra: dict, *args) -> str:
        time.sleep(self.wait)

        message = f"Call {call_id} in tool {id(self)} finished at {datetime.datetime.now().strftime("%H:%M:%S.%f")} and waited {self.wait} seconds"

        state.last_ass_message.append(message)

        return message


def module(state: StateManager[ModuleConfig]) -> None:
    state.last_ass_message.update("")

    state.using(state.llm.using("AZURE_GPT_4o_MINI_2024_0718"))

    completion = (
        state.context(
            [
                Message.SYSTEM("Your role is to help the developer test the management of sources."),
                Message.SYSTEM("Generate two parallel tool calls in the same message, calling two times the DevToop with random waiting times between 1 and 5 seconds."),
            ],
            # prepend=True,
        )
        .register(DevTool)
        .complete()
    )

    state.last_ass_message.update(f"Got {len(completion.tool_calls)} tool calls")

    if len(completion.tool_calls) > 1:
        state.call(completion)

    state.last_ass_message.append("Finished")

    return


app = App("Petal").threaded(False).of(module).webhook(chat_id="chat_kfzs7m6lbbr570sfip91ns81", assistant_id="assistant_tgmzoa62bqjyz50pfi7u5aqu")
