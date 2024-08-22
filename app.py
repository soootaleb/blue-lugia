from typing import Optional

from pydantic import BaseModel, Field

from blue_lugia.app import App
from blue_lugia.config import ModuleConfig
from blue_lugia.enums import Role
from blue_lugia.managers.file import FileManager
from blue_lugia.models import Message
from blue_lugia.models.file import ChunkList, FileList
from blue_lugia.models.message import MessageList
from blue_lugia.models.query import Q
from blue_lugia.state import StateManager


# Create a custom error and handle it. Need to call App.handle() to handle the error
class CommandError(Exception):
    def handle(self, state: StateManager) -> None:
        state.last_ass_message.append(f"Woopsies, here is a command error: {self}")


# Inherit the base config to add your fields. The fields will be set with the corresponding ENVARS or module configuration set in the UI
class CustomConfig(ModuleConfig):
    TEST_MESSAGE: str = "CustomConfig"
    IN_MESSAGE: str = "InMessage"


# A tool is a Base Model
# The class name is used as the tool name
# The class description is used as the tool description
# Fields descriptions and types (potentially optional) are used as the tool arguments.
class SumTool(BaseModel):
    """Add two numbers"""

    class Config:
        bl_fc_strict = True
        bl_schema_strict = True

    x: int = Field(..., description="first value")
    y: int = Field(..., description="second value")

    # The run method is executed by state.call(completion). The tool call formulated by the LLM results in an instance of the tool, so you can access arguments with self.x
    # What's returned by this method is considered the "tool response", so the state.call() will append a message { role: TOOL, content: run() } to the context
    def run(self, call_id: str, state: StateManager, *args, **kwargs) -> int:
        # state.last_ass_message.update(f"The sum of {self.x} and {self.y} is {self.x + self.y}")
        return self.x + self.y

    # pre_run_hook and post_run_hook and run must accept a number of arguments, add *args and **kwargs if you don't know them all
    # returning False will prevent state.loop() to complete the context after all tools have been called.
    def post_run_hook(self, call_id: str, state: StateManager, *args, **kwargs) -> Optional[bool]:
        pass
        # return False

    # It happens that the LLM returns a tool call that does not match the signature (e.g with a missing required argument)
    # This method is executed if the tool was designated but could not be instanciated / executed
    @classmethod
    def on_validation_error(cls, call_id: str, arguments: dict, state: StateManager, extra: dict | None = None, out: Message | None = None) -> bool:
        validation_error = (extra or {}).get("validation_error")
        state.last_ass_message.append(f"Tool {cls.__name__} not called because of validation error {validation_error}")
        return False


def debug(state: StateManager[CustomConfig], args: list[str] = []) -> None:
    search_query = (  # noqa: F841
        Q(url__contains=".com/SitePages", FirstPublishedDate__gt="2024-07-15T00:00:00.00Z", FirstPublishedDate__lt="2024-07-19T00:00:00.00Z")
        & ~Q(url__contains="fr/")
        & ~Q(url__contains="Templates/")
    )

    fetch_query = Q(key__icontains=".pdf") & Q(key__icontains="NeoXam") | ~Q(key__icontains=".pdf") & ~Q(key__icontains=".xlsx")

    files_names = state.files.filter(fetch_query).values("name", flat=True)

    state.last_ass_message.update(f"Found files {', '.join(files_names)}")


# The module is a function accepting a state manager
def module(state: StateManager[ModuleConfig]) -> None:
    # ============= LOGGING =======================

    # log messages with the state logger
    state.logger.debug(f"Just entered the module of app {state.app.name}")

    # create child loggers for better readability
    logger = state.logger.getChild("ChildLogger")

    # state exposes the configuration, based on default values set by ModuleConfig, overriden by envars, overriden by assistant config from the UI
    logger.debug(f"languageModel is {state.conf.languageModel}")

    # ===================== MODELS ========================

    # You generally manipulate models Message, File
    message: Message = Message(Role.USER, "Hello") or Message.USER("Hello")

    # Models have methods to handle them
    message.append("World")

    # And properties you can find using autocompletion
    state.logger.debug(message.content)

    # Models also have their associated lists
    history = MessageList([Message.SYSTEM("You are a helpful assistant"), Message.USER("Who are you ?")])

    # With their methods
    user_messages: MessageList = history.filter(lambda x: x.role == Role.USER)  # noqa: F841
    first_message: Message | None = history.first()  # noqa: F841
    first_system_message: Message | None = history.first(lambda x: x.role == Role.SYSTEM)  # noqa: F841
    truncated_messages: MessageList = history.truncate(1000)  # noqa: F841

    # And their properties
    messages_tokens = history.tokens  # noqa: F841

    # ===================== MANAGERS ========================

    # Managers are used to interact with the API
    files = state.files
    messages = state.messages
    llm = state.llm

    # They expose methods to retrieve, create, update, delete the models
    messages_in_chat: MessageList = messages.all()  # noqa: F841

    # The managers return models or list of models
    user_messages_in_chat: MessageList = messages.filter(lambda x: x.role == Role.USER).all()  # noqa: F841
    last_user_message: Message | None = messages.last(lambda x: x.role == Role.USER)  # equivalent to state.last_usr_message  # noqa: F841
    last_assistant_message: Message | None = messages.last(lambda x: x.role == Role.ASSISTANT)  # equivalent to state.last_ass_message  # noqa: F841

    # Note that managers have "configuration methods" and "execution methods"
    # For example, Manager.filter() does not execute a query, but instead returns a new manager with filters ready to be applied
    files: FileManager = files.filter(key__contains=".xlsx")

    # You can check the Q model / documentation for more complex queries
    files.filter(
        Q(url__contains=".com/SitePages", FirstPublishedDate__gt="2024-07-15T00:00:00.00Z", FirstPublishedDate__lt="2024-07-19T00:00:00.00Z")
        & ~Q(url__contains="fr/")
        & ~Q(url__contains="Templates/")
    )

    # The files manager encapsulates both Search & Content APIs
    # Search returns a ChunkList while Content returns a FileList
    searching_chunks: ChunkList = files.search("What's directive 51 ?")  # noqa: F841
    retrieving_files: FileList = files.fetch()  # noqa: F841

    # Objects returned by a manager are generally compatible with methods of other managers
    completion: Message = llm.complete([Message.USER("Tell me a joke")])
    state.last_ass_message.update(completion.content)

    # LLM Manager streams to frontend if you provide a message to stream to
    llm.complete([Message.USER("Tell me a story between the moon, the earth and the sun")], out=state.last_ass_message)

    # ====================== COMBINING ============================

    # Let's try to do some RAG

    # Retrieve some chunks
    chunks: ChunkList = state.files.search("What's directive 51 ?")

    # Prepare some prompting
    context: MessageList = MessageList(
        [
            Message.SYSTEM("Your role is to summarize the informatin asked by the user using bullet points."),
            Message.SYSTEM("You MUST cite your sources using [source0], [source1], [source2], etc"),
        ]
    )

    # You can manipulate the retrieved chunks before exposing it to the context
    chunks: ChunkList = chunks.sort(lambda chunk: chunk.order)

    # Format the sources to be exposed to the LLM
    formated_sources: str = chunks.xml()

    context.append(Message.SYSTEM(f"The available sources are: {formated_sources}"))

    # Format the retrieved data as a search context for the frontend to create the links
    search_context = chunks.as_context()

    # Use the LLM to answer directly to the frontend
    completion = llm.complete(context, out=state.last_ass_message, search_context=search_context)

    # Completion is already in frontend, but you could analyse it
    state.logger.debug(f"LLM responded with {completion.content}")

    # ============================ STATE ==============================

    # TODO

    state.files.uploaded.search().as_files().first()
    state.complete(out=state.last_ass_message)


# Use method chaining to define the app name, the commands, error handlers, custom config, and the module to run
app = App("Petal").configured(CustomConfig).handle(CommandError).threaded(False).of(module)

# You can arbitrarily execute your module by mocking an event
# Keep in mind that the app._conf which is a ModuleConfig, will be set with your environment variables.
# Your .env should be set according to the APIs your want to use (local, next, neo, etc)
# app.webhook(chat_id="chat_kfzs7m6lbbr570sfip91ns81", assistant_id="assistant_y4j9d9h0yoa2f084qp9jknxi")
