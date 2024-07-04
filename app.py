from blue_lugia.app import App
from blue_lugia.managers.llm import LanguageModelManager
from blue_lugia.models import Message
from blue_lugia.models.message import MessageList
from blue_lugia.processor import Processor
from blue_lugia.state import StateManager

# class MessageContentProcessor(Processor):
#     def process(self, message: Message) -> Message:
#         return message

#     def unprocess(self, message: Message) -> Message:
#         return message


# class PrependProcessor(MessageContentProcessor):
#     def process(self, message: Message) -> Message:
#         message.content = f"Prepended: {message.content}"
#         return message

#     def unprocess(self, message: Message) -> Message:
#         if message.content:
#             message.content = message.content.replace("Prepended: ", "")
#         return message


class ProcessedLLM(LanguageModelManager):
    def _reformat(self, messages: MessageList) -> MessageList:
        return super()._reformat(messages)

def module(state: StateManager) -> None:

    chunks = state.files.filter(key__contains="VMware").search()

    state.complete(out=state.last_ass_message)


app = App("Petal").using(ProcessedLLM).process(Processor).threaded(False).of(module).listen()
