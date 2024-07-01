import logging
from abc import ABC
from typing import Any, Generic, List, Tuple

import unique_sdk
from pydantic import BaseModel
from pydantic_core import ValidationError

from blue_lugia.config import ConfType
from blue_lugia.enums import Role
from blue_lugia.managers import (
    FileManager,
    LanguageModelManager,
    Manager,
    MessageManager,
    StorageManager,
)
from blue_lugia.models import ExternalModuleChosenEvent, File, FileList, Message, MessageList, ToolCalled, ToolNotCalled


class StateManager(ABC, Generic[ConfType]):
    _event: ExternalModuleChosenEvent
    _messages: MessageManager
    _llm: LanguageModelManager
    _files: FileManager
    _storage: StorageManager

    _extra: dict[str, Any]
    _tools: List[type[BaseModel]]
    _ctx: MessageList

    _logger: logging.Logger | None = None

    _managers = {
        "messages": MessageManager,
        "llm": LanguageModelManager,
        "files": FileManager,
        "storage": StorageManager,
    }

    _conf: ConfType

    def __init__(
        self,
        event: ExternalModuleChosenEvent,
        conf: ConfType,
        logger: logging.Logger | None = None,
        managers: dict[str, type[Manager]] | None = None,
    ) -> None:
        self._event: ExternalModuleChosenEvent = event

        self._conf = conf

        self._logger = logger or logging.getLogger(__name__.lower())

        self._managers = self._managers | (managers or {}) or {}

        self._messages = self._MessageManager(
            event=event,
            tokenizer=self.config.LLM_TOKENIZER,
            logger=self.logger.getChild(self._MessageManager.__name__),
        )

        self._llm = self._LanguageModelManager(
            event=event,
            model=self.cfg.languageModel,
            timeout=self.cfg.LLM_TIMEOUT,
            logger=self.logger.getChild(self._LanguageModelManager.__name__),
        )

        self._files = self._FileManager(
            event=event,
            tokenizer=self.cfg.LLM_TOKENIZER,
            logger=self.logger.getChild(self._FileManager.__name__),
        )

        self._storage = self._StorageManager(
            event=event,
            store=self.messages.first() or self.messages.create(Message.ASSISTANT("")),
            logger=self.logger.getChild(self._StorageManager.__name__),
        )

        self._tools = []

        # we filter empty messages notably the ASSISTANT empty message created by the API
        self._ctx = (
            self.messages.all().fork().filter(lambda x: bool(x.content) or bool(x.tool_calls)).expand(self._key if hasattr(self, "_key") else "state_manager_tool_calls")  # type: ignore
        )
        self._extra = {}

    @property
    def _FileManager(self) -> type[FileManager]:  # noqa: N802
        return self._managers.get("files", FileManager)

    @property
    def _MessageManager(self) -> type[MessageManager]:  # noqa: N802
        return self._managers.get("messages", MessageManager)

    @property
    def _LanguageModelManager(self) -> type[LanguageModelManager]:  # noqa: N802
        return self._managers.get("llm", LanguageModelManager)

    @property
    def _StorageManager(self) -> type[StorageManager]:  # noqa: N802
        return self._managers.get("storage", StorageManager)

    @property
    def event(self) -> ExternalModuleChosenEvent:
        return self._event

    @property
    def messages(self) -> MessageManager:
        return self._messages

    @property
    def files(self) -> FileManager:
        return self._files

    @property
    def llm(self) -> LanguageModelManager:
        return self._llm

    @property
    def ctx(self) -> MessageList:
        return self._ctx

    @property
    def tools(self) -> List[type[BaseModel]]:
        return self._tools

    @property
    def storage(self) -> StorageManager:
        return self._storage

    @property
    def conf(self) -> ConfType:
        return self._conf

    @property
    def config(self) -> ConfType:
        return self._conf

    @property
    def cfg(self) -> ConfType:
        return self._conf

    @property
    def logger(self) -> logging.Logger:
        return self._logger or logging.getLogger(__name__.lower())

    @property
    def last_ass_message(self) -> Message | None:
        return self.messages.filter(lambda x: x.role == Role.ASSISTANT).last()

    @property
    def last_usr_message(self) -> Message | None:
        return self.messages.filter(lambda x: x.role == Role.USER).last()

    def using(self, llm: LanguageModelManager) -> "StateManager[ConfType]":
        self.logger.debug(f"Using LLM {llm}")
        self._llm = llm
        return self

    def extra(self, extra: dict[str, Any]) -> "StateManager[ConfType]":
        self.logger.debug(f"Setting extras {(', '.join(extra.keys()))}")
        self._extra = extra
        return self

    def context(
        self,
        messages: (List[Message] | File | FileManager | FileList | Message | MessageList | MessageManager),
        append: bool = False,
        prepend: bool = False,
    ) -> "StateManager[ConfType]":
        if isinstance(messages, File):
            _ctx = MessageList(
                [messages.as_message()],
                self.messages.tokenizer,
                logger=self.logger.getChild(MessageList.__name__),
            )
        elif isinstance(messages, (FileList, FileManager)):
            _ctx = messages.as_messages()
        elif isinstance(messages, Message):
            _ctx = MessageList(
                [messages],
                self.messages.tokenizer,
                logger=self.logger.getChild(MessageList.__name__),
            )
        elif isinstance(messages, MessageList):
            _ctx = messages
        elif isinstance(messages, MessageManager):
            _ctx = messages.all()
        else:
            _ctx = MessageList(
                messages,
                self.messages.tokenizer,
                logger=self.logger.getChild(MessageList.__name__),
            )

        if append and prepend:
            self.logger.error("Cannot append and prepend to the context at the same time.")
            raise ValueError("Cannot append and prepend at the same time.")

        if append:
            self.logger.debug(f"Adding {len(_ctx)} messages to the context")
            self.ctx.extend(_ctx)
        elif prepend:
            sent_user_message = self.ctx.filter(lambda x: bool(x._remote)).filter(lambda x: bool(x._remote) and x._remote._id == self.event.payload.user_message.id).first()
            if sent_user_message:
                self.logger.debug(f"Inserting {len(_ctx)} messages to the context")
                sent_user_message_index = self.ctx.index(sent_user_message)
                self.ctx[sent_user_message_index:sent_user_message_index] = _ctx
            else:
                self.logger.debug(f"Adding {len(_ctx)} messages to the context")
                self.ctx.extend(_ctx)
        else:
            self.logger.debug(f"Setting {len(_ctx)} messages as the context")
            self._ctx = _ctx

        return self

    def register(self, tools: type[BaseModel] | List[type[BaseModel]]) -> "StateManager":
        tools_as_list = tools if isinstance(tools, List) else [tools]

        for tool in tools_as_list:
            if tool not in self._tools:
                self._tools.append(tool)
                self.logger.debug(f"Registering tool {tool.__name__}")
            else:
                self.logger.warning(f"Tool {tool.__name__} already registered.")

        return self

    def _call_tools(
        self, message: Message, extra: dict | None = None, out: Message | None = None, raise_on_missing_tool: bool = False
    ) -> Tuple[List[ToolCalled], List[ToolNotCalled]]:
        tools_called: List[ToolCalled] = []
        tools_not_called: List[ToolNotCalled] = []

        tools_routes = {tool.__name__: tool for tool in self.tools}

        tool_calls = message.tool_calls

        self.logger.debug(f"Calling tools {tool_calls}")

        if extra is None:
            extra = {}

        tool_call_index = 0

        for tc in tool_calls:
            self.logger.debug(f"{tool_call_index} - Calling tool {tc['function']['name']}")

            if tc["function"]["name"] not in tools_routes:
                self.logger.error(f"Tool {tc['function']['name']} not registered. Skipping.")
                if raise_on_missing_tool:
                    raise ValueError(f"Tool {tc['function']['name']} not registered.")
                else:
                    continue

            tool = tools_routes[tc["function"]["name"]]

            all_extras = {
                **self._extra,
                **extra,
                "tool_call_index": tool_call_index,
            }

            self.logger.debug(f"Extra contains {', '.join(all_extras.keys())}")

            try:
                tool_call = tool(**tc["function"]["arguments"])
            except ValidationError as e:
                self.logger.error(f"Tool {tc['function']['name']} failed to validate.")

                arguments = tc["function"]["arguments"]

                tool_validation_handler = getattr(tool, "on_validation_error", None)

                if tool_validation_handler:
                    self.logger.debug(f"Calling {tool.__name__}.on_validation_error")

                    all_extras["validation_error"] = e

                    handled = tool_validation_handler(tc["id"], arguments, self, all_extras, out)

                else:
                    self.logger.debug(f"No on_validation_error handler for {tool.__name__}.")
                    handled = None

                tools_not_called.append({"id": tc["id"], "tool": tool, "arguments": arguments, "handled": handled, "error": e})

            else:
                self.logger.debug(f"Tool {tc['function']['name']} is {tool_call}")

                pre = (
                    tool_call.pre_run_hook(  # type: ignore
                        tc["id"],
                        self,
                        all_extras,
                        out,
                    )
                    if hasattr(tool_call, "pre_run_hook")
                    else None
                )

                self.logger.debug(f"Pre run hook is {pre}")

                if isinstance(pre, bool) and not pre:
                    run = None
                    self.logger.debug("Pre run hook returned False, skipping run.")
                else:
                    run = (
                        tool_call.run(  # type: ignore
                            tc["id"],
                            self,
                            all_extras,
                            out,
                        )
                        if hasattr(tool_call, "run")
                        else None
                    )

                    self.logger.debug(f"Run is {run}")

                post = (
                    tool_call.post_run_hook(  # type: ignore
                        tc["id"],
                        self,
                        all_extras,
                        out,
                    )
                    if hasattr(tool_call, "post_run_hook")
                    else None
                )

                self.logger.debug(f"Post run hook is {post}")

                tools_called.append(
                    {
                        "id": tc["id"],
                        "tool": tool_call,
                        "call": {
                            "pre_run_hook": pre,
                            "run": run,
                            "post_run_hook": post,
                        },
                    }
                )

                tool_call_index += 1

        return tools_called, tools_not_called

    def _process_tools_called(self, message: Message, tools_called: List[ToolCalled], tools_not_called: List[ToolNotCalled]) -> bool:  # noqa: C901
        complete = True

        extension = MessageList(
            [],
            self.messages.tokenizer,
            logger=self.logger.getChild(MessageList.__name__),
        )

        for tc in tools_called:
            tool = tc["tool"]
            tool_call = tc["call"]
            tool_call_id = tc["id"]

            run = tool_call["run"]
            # pre_run = tool_call["pre_run_hook"]
            post_run = tool_call["post_run_hook"]

            if isinstance(run, bool) and not run:
                self.logger.debug(f"Tool run {tool.__class__.__name__} returned False. Stoping loop over tool calls.")
                complete = False

            if isinstance(post_run, bool) and not post_run:
                self.logger.debug(
                    f"""Tool post_run_hook {tool.__class__.__name__} returned False.
                    Stoping loop over tool calls."""
                )
                complete = False

            # We add exactly one tool message for each tool call, mandatory
            extension.append(
                Message.TOOL(
                    content=(run.content if isinstance(run, Message) else str(run)),
                    tool_call_id=tool_call_id,
                    logger=self.logger.getChild(Message.__name__),
                )
            )

            self.logger.debug(f"Tool run {tool_call_id} of {tool.__class__.__name__} appended to extension.")

            if run is None and complete:
                t_name = tool.__class__.__name__
                self.logger.warning(
                    f"""Tool {t_name} returned None.
                    \nIn the mean time, the completion loop is supposed to continue.
                    \nThat means that next iteration will try to LLM.complete()
                        with a ToolMessage(content=None).
                    \nIts highly advised to return False in {t_name}.run() or {t_name}.post_run_hook().
                    \nYou should also make sure {t_name} correctly
                        updated the frontend messages along wth the context."""
                )

        for tc in tools_not_called:
            tool = tc["tool"]  # not an instance of the tool
            handled = tc["handled"]
            tool_call_id = tc["id"]

            if isinstance(handled, bool) and not handled:
                self.logger.debug(f"Tool {tool.__name__} on_validation_error returned False. Stoping loop over tool calls.")
                complete = False

            # We add exactly one tool message for each tool call, mandatory
            extension.append(
                Message.TOOL(
                    content=(handled.content if isinstance(handled, Message) else str(handled)),
                    tool_call_id=tool_call_id,
                    logger=self.logger.getChild(Message.__name__),
                )
            )

            self.logger.debug(f"Tool handling {tool_call_id} of {tool.__name__} appended to extension.")

            if handled is None and complete:
                t_name = tool.__name__
                self.logger.warning(
                    f"""Tool {t_name} on_validation_error returned None.
                    \nIn the mean time, the completion loop is supposed to continue.
                    \nThat means that next iteration will try to LLM.complete()
                        with a ToolMessage(content=None).
                    \nIts highly advised to return False in {t_name}.on_validation_error().
                    \nYou should also make sure {t_name} correctly
                        updated the frontend messages along wth the context."""
                )

        debug_store = self.messages.filter(lambda x: x.role == Role.USER and bool(x._remote)).last()

        if debug_store:
            debug_store.update(
                debug_store.content,
                debug={
                    **debug_store.debug,
                    "_tool_calls": [
                        {
                            "role": message.role.value,
                            "content": message.content,
                            "tools_called": message.tool_calls,
                        }
                    ]
                    + [
                        {
                            "role": m.role.value,
                            "content": m.content,
                            "tool_call_id": m.tool_call_id,
                        }
                        for m in extension
                    ],
                },
            )

        else:
            self.logger.warning(
                """No user message found in context.
                \nCannot update debug information for tool calls.
                \nThis is a critical issue for debugging."""
            )

        self.ctx.extend(extension)

        self.logger.debug(f"Extension of {len(extension)} tool messages appended to context.")

        return complete and (bool(tools_called) or bool(tools_not_called))

    def call(
        self,
        message: Message,
        extra: dict | None = None,
        out: Message | None = None,
        raise_on_missing_tool: bool = False,
    ) -> Tuple[List[ToolCalled], List[ToolNotCalled], bool]:
        tools_called, tools_not_called = self._call_tools(message=message, extra=extra or {}, out=out, raise_on_missing_tool=raise_on_missing_tool)

        complete = self._process_tools_called(message=message, tools_called=tools_called, tools_not_called=tools_not_called)

        self.logger.debug(f"Finished running {len(tools_called)} tools.")

        return tools_called, tools_not_called, complete

    def complete(
        self,
        message: Message | None = None,
        out: Message | None = None,
        start_text: str = "",
        tool_choice: type[BaseModel] | None = None,
        search_context: List[unique_sdk.Integrated.SearchResult] = [],
    ) -> Message:
        if isinstance(message, str):
            message = Message.USER(message, logger=self.logger.getChild(Message.__name__))

        if message:
            self.logger.debug(f"Completing message {message.role if message else "None"}")

        if message and message not in self.ctx:
            ctx = self.ctx.append(message)
            self.logger.debug(f"Appending message {message.role if message else "None"} to context.")
        else:
            self.logger.debug(f"Message {message.role if message else "None"} already in context.")
            ctx = self.ctx

        self.logger.debug("Filtering context for empty assistant messages without content nor tools.")

        ctx = ctx.filter(lambda x: x.role != Role.ASSISTANT or bool(x.content) or bool(x.tool_calls))

        completion = self.llm.complete(
            messages=ctx,
            tools=self.tools,
            out=out,
            start_text=start_text,
            tool_choice=tool_choice,
            search_context=search_context,
        )

        self.logger.debug(f"Appending completion to context: {completion.role if completion else "None"}")

        self.ctx.append(completion)

        return completion

    def loop(
        self,
        message: Message | None = None,
        out: Message | None = None,
        start_text: str = "",
        tool_choice: type[BaseModel] | None = None,
        search_context: List[unique_sdk.Integrated.SearchResult] = [],
        raise_on_max_iterations: bool = False,
        raise_on_missing_tool: bool = False,
    ) -> List[Tuple[Message, List[ToolCalled], List[ToolNotCalled]]]:
        complete = True

        loop_iteration = 0

        completions: List[Tuple[Message, List[ToolCalled], List[ToolNotCalled]]] = []

        self.logger.debug(
            f"""Starting completion loop with message {message.role if message else "None"}.
            Max {self.config.FUNCTION_CALL_MAX_ITERATIONS} iterations."""
        )

        while complete and loop_iteration < self.config.FUNCTION_CALL_MAX_ITERATIONS:
            self.logger.debug(f"Completing iteration {loop_iteration}.")

            completion = self.complete(message, out=out, start_text=start_text, tool_choice=tool_choice, search_context=search_context)

            self.logger.debug(f"Calling tools for completion {completion.role}.")

            tools_called, tools_not_called, complete = self.call(
                message=completion,
                extra={
                    "tool_calls": completion.tool_calls,
                    "loop_iteration": loop_iteration,
                },
                out=out,
                raise_on_missing_tool=raise_on_missing_tool,
            )

            completions.append((completion, tools_called, tools_not_called))

            self.logger.debug(f"{len(tools_called)} Tools called for completion {completion.role}.")

            loop_iteration += 1

        if loop_iteration >= self.config.FUNCTION_CALL_MAX_ITERATIONS:
            self.logger.warning(f"Max iterations reached. Stopping loop. Raise on max iterations: {raise_on_max_iterations}")
            if raise_on_max_iterations:
                raise ValueError("Max iterations reached.")

        return completions

    def stream(self, message: Message | None = None, out: Message | None = None, start_text: str = "") -> Message:
        self.logger.debug(f"Starting stream with message {message.role if message else "None"}.")
        return self.complete(message, out=out or self.last_ass_message, start_text=start_text)

    def clear(self) -> int:
        self.logger.debug("Clearing all messages and context.")
        self.ctx.clear()
        return self.messages.delete()

    def pre_module_hook(self) -> None:
        pass

    def post_module_hook(self) -> None:
        pass
