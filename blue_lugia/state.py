import logging
from abc import ABC
from typing import Any, Callable, Generic, List, Tuple

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
from blue_lugia.models.store import Store


class StateManager(ABC, Generic[ConfType]):
    """
    Manages the state of the system, coordinating interactions between different managers like message handling, file management, and language modeling.

    Attributes:
        _event (ExternalModuleChosenEvent): The external event that triggers state management.
        _messages (MessageManager): Manager responsible for message operations.
        _llm (LanguageModelManager): Manages interactions with language models.
        _files (FileManager): Handles file-based operations.
        _storage (StorageManager): Manages data persistence and retrieval.
        _extra (dict[str, Any]): Extra parameters that might be needed during processing.
        _tools (List[type[BaseModel]]): Registered tools for processing.
        _ctx (MessageList): The current context of messages being processed.
        _logger (logging.Logger | None): Logger for logging activities, optional.
        _managers (dict[str, type[Manager]]): Dictionary mapping manager types to their instances.
        _conf (ConfType): Configuration object specific to the manager implementations.
        _commands (dict[str, Callable]): Commands available within the state.
        _app (Any): Application context or reference.

    Methods:
        __init__: Initializes a new instance of StateManager.
        event: Returns the event that initiated the state management.
        messages: Accesses the message manager.
        files: Accesses the file manager.
        llm: Accesses the language model manager.
        ctx: Accesses the current message context.
        tools: Lists all registered tools.
        storage: Accesses the storage manager.
        conf, config, cfg: Returns the configuration object.
        logger: Accesses the logger.
        app: Returns the application context.
        last_ass_message: Retrieves the last assistant message.
        last_usr_message: Retrieves the last user message.
        using: Configures the state manager to use a specified language model manager.
        extra: Sets extra parameters for use in processing.
        context: Sets or modifies the context in which messages are processed.
        register: Registers new tools for use in processing.
        _call_tools: Internal method to facilitate tool calls.
        _process_tools_called: Processes the results from tool calls.
        call: Facilitates calling tools with a given message.
        complete: Completes the processing of a message or context.
        loop: Executes a processing loop, handling message and tool interactions iteratively.
        stream: Streams processing for continuous interaction.
        clear: Clears all messages and resets context.
        pre_module_hook: Hook that runs before module operations.
        post_module_hook: Hook that runs after module operations.
    """

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

    _commands: dict[str, Callable]
    _app: Any

    _data: Store

    def __init__(
        self,
        event: ExternalModuleChosenEvent,
        conf: ConfType,
        logger: logging.Logger | None = None,
        managers: dict[str, type[Manager]] | None = None,
        app: Any | None = None,
    ) -> None:
        self._event: ExternalModuleChosenEvent = event

        self._conf = conf

        self._logger = logger or logging.getLogger(__name__.lower())

        self._managers = self._managers | (managers or {}) or {}

        self._llm = self._LanguageModelManager(
            event=event,
            model=self.cfg.languageModel or self.cfg.LLM_DEFAULT_MODEL,
            timeout=self.cfg.LLM_TIMEOUT,
            context_max_tokens=self.cfg.CONTEXT_WINDOW_TOKEN_LIMIT,
            seed=self.cfg.LLM_SEED,
            logger=self.logger.getChild(self._LanguageModelManager.__name__),
        )

        self._messages = self._MessageManager(
            event=event,
            tokenizer=self._llm.tokenizer,
            logger=self.logger.getChild(self._MessageManager.__name__),
        )

        self._files = self._FileManager(
            event=event,
            tokenizer=self._llm.tokenizer,
            logger=self.logger.getChild(self._FileManager.__name__),
        )

        self._storage = self._StorageManager(
            event=event,
            store=self.messages.first() or self.messages.create(Message.ASSISTANT("")),
            logger=self.logger.getChild(self._StorageManager.__name__),
        )

        self._tools = []

        # we filter empty messages notably the ASSISTANT empty message created by the API
        self._ctx = self.messages.all().fork().filter(lambda x: bool(x.content) or bool(x.tool_calls)).expand()

        self._app = app
        self._extra = {}
        self._data = Store()

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
    def data(self) -> Store:
        return self._data

    @property
    def app(self) -> Any:
        return self._app

    @property
    def last_ass_message(self) -> Message | None:
        return self.messages.filter(lambda x: x.role == Role.ASSISTANT).last()

    @property
    def last_usr_message(self) -> Message | None:
        return self.messages.filter(lambda x: x.role == Role.USER).last()

    def using(self, llm: LanguageModelManager) -> "StateManager[ConfType]":
        """
        Configures the StateManager to use a specific Language Model Manager.

        Args:
            llm (LanguageModelManager): The language model manager to be used by the StateManager.

        Returns:
            StateManager[ConfType]: The current instance of StateManager with the updated language model manager.

        Usage:
            This method allows for dynamic switching or updating of the language model manager within the StateManager,
            facilitating flexibility in response to changes or different processing needs.
        """
        self.logger.debug(f"BL::StateManager::using::Using LLM {llm}")
        self._llm = llm
        return self

    def extra(self, extra: dict[str, Any]) -> "StateManager[ConfType]":
        """
        Sets additional parameters that can be used during the processing of messages and tools.

        Args:
            extra (dict[str, Any]): A dictionary of extra parameters to set.

        Returns:
            StateManager[ConfType]: The current instance of StateManager with updated extra parameters.

        Usage:
            This method provides a way to pass arbitrary extra data that can influence the behavior of the StateManager during message and tool processing.
        """
        self.logger.debug(f"BL::StateManager::extra::Setting extras {(', '.join(extra.keys()))}")
        self._extra = extra
        return self

    def context(
        self,
        messages: (List[Message] | File | FileManager | FileList | Message | MessageList | MessageManager),
        append: bool = False,
        prepend: bool = False,
    ) -> "StateManager[ConfType]":
        """
        Sets or modifies the current context for processing messages.

        Args:
            messages (Union[List[Message], File, FileManager, FileList, Message, MessageList, MessageManager]): The new context or additional messages to set or add.
            append (bool): If True, adds the provided messages to the end of the current context.
            prepend (bool): If True, adds the provided messages to the beginning of the current context.

        Returns:
            StateManager[ConfType]: The current instance of StateManager with the modified context.

        Raises:
            ValueError: If both append and prepend are True, which is logically conflicting.

        Usage:
            This method manages the message context which is crucial for maintaining the state across interactions within the system.
            It allows for dynamically changing the context in which subsequent operations are evaluated.
        """
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
            self.logger.error("BL::StateManager::context::Cannot append and prepend to the context at the same time.")
            raise ValueError("Cannot append and prepend at the same time.")

        if append:
            self.logger.debug(f"BL::StateManager::context::Adding {len(_ctx)} messages to the context")
            self.ctx.extend(_ctx)
        elif prepend:
            self.ctx[0:0] = _ctx
        else:
            self.logger.debug(f"BL::StateManager::context::Setting {len(_ctx)} messages as the context")
            self._ctx = _ctx

        return self

    def set_context(
        self,
        messages: (List[Message] | File | FileManager | FileList | Message | MessageList | MessageManager),
        append: bool = False,
        prepend: bool = False,
    ) -> "StateManager[ConfType]":
        """
        Sets or modifies the current context for processing messages.

        Args:
            messages (Union[List[Message], File, FileManager, FileList, Message, MessageList, MessageManager]): The new context or additional messages to set or add.
            append (bool): If True, adds the provided messages to the end of the current context.
            prepend (bool): If True, adds the provided messages to the beginning of the current context.

        Returns:
            StateManager[ConfType]: The current instance of StateManager with the modified context.

        Raises:
            ValueError: If both append and prepend are True, which is logically conflicting.

        Usage:
            This method manages the message context which is crucial for maintaining the state across interactions within the system.
            It allows for dynamically changing the context in which subsequent operations are evaluated.
        """
        return self.context(messages=messages, append=append, prepend=prepend)

    def register(self, tools: type[BaseModel] | List[type[BaseModel]]) -> "StateManager":
        """
        Registers one or more new tools to be used in processing.

        Args:
            tools (Union[type[BaseModel], List[type[BaseModel]]]): The tool or list of tools to register.

        Returns:
            StateManager: The current instance of StateManager with the new tools registered.

        Usage:
            This method is used to add new tools to the StateManager's toolkit, expanding its capabilities for handling various tasks related to message and data processing.
        """
        tools_as_list = tools if isinstance(tools, List) else [tools]

        for tool in tools_as_list:
            if tool not in self._tools:
                self._tools.append(tool)
                self.logger.debug(f"BL::StateManager::register::Registering tool {tool.__name__}")
            else:
                self.logger.warning(f"BL::StateManager::register::Tool {tool.__name__} already registered.")

        return self

    def _call_tools(
        self, message: Message, extra: dict | None = None, out: Message | None = None, raise_on_missing_tool: bool = False
    ) -> Tuple[List[ToolCalled], List[ToolNotCalled]]:
        tools_called: List[ToolCalled] = []
        tools_not_called: List[ToolNotCalled] = []

        tools_routes = {tool.__name__: tool for tool in self.tools}

        tool_calls = message.tool_calls

        self.logger.debug(f"BL::StateManager::_call_tools::Calling tools {tool_calls}")

        if extra is None:
            extra = {}

        tool_call_index = 0

        for tc in tool_calls:
            self.logger.debug(f"BL::StateManager::_call_tools::{tool_call_index} - Calling tool {tc['function']['name']}")

            if tc["function"]["name"] not in tools_routes:
                self.logger.error(f"BL::StateManager::_call_tools::Tool {tc['function']['name']} not registered. Skipping.")
                if raise_on_missing_tool:
                    raise ValueError(f"BL::StateManager::_call_tools::Tool {tc['function']['name']} not registered.")
                else:
                    continue

            tool = tools_routes[tc["function"]["name"]]

            all_extras = {
                **self._extra,
                **extra,
                "tool_call_index": tool_call_index,
            }

            self.logger.debug(f"BL::StateManager::_call_tools::Extra contains {', '.join(all_extras.keys())}")

            try:
                tool_call = tool(**tc["function"]["arguments"])
            except ValidationError as e:
                self.logger.error(f"Tool {tc['function']['name']} failed to validate.")

                arguments = tc["function"]["arguments"]

                tool_validation_handler = getattr(tool, "on_validation_error", None)

                if tool_validation_handler:
                    self.logger.debug(f"BL::StateManager::_call_tools::Calling {tool.__name__}.on_validation_error")

                    all_extras["validation_error"] = e

                    handled = tool_validation_handler(tc["id"], arguments, self, all_extras, out)

                else:
                    self.logger.debug(f"BL::StateManager::_call_tools::No on_validation_error handler for {tool.__name__}.")
                    handled = None

                tools_not_called.append({"id": tc["id"], "tool": tool, "arguments": arguments, "handled": handled, "error": e})

            else:
                self.logger.debug(f"BL::StateManager::_call_tools::Tool {tc['function']['name']} is {tool_call}")

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

                self.logger.debug(f"BL::StateManager::_call_tools::Pre run hook is {pre}")

                if isinstance(pre, bool) and not pre:
                    run = None
                    self.logger.debug("BL::StateManager::_call_tools::Pre run hook returned False, skipping run.")
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

                    self.logger.debug(f"BL::StateManager::_call_tools::Run is {str(run)[:100]}")

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

                self.logger.debug(f"BL::StateManager::_call_tools::Post run hook is {str(post)[:100]}")

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
            post_run = tool_call["post_run_hook"]

            if isinstance(post_run, bool) and not post_run:
                self.logger.debug(f"""BL::StateManager::_process_tools_called::Tool post_run_hook {tool.__class__.__name__} returned False. Stoping loop over tool calls.""")
                complete = False

            # We add exactly one tool message for each tool call, mandatory
            extension.append(
                Message.TOOL(
                    content=(run.original_content if isinstance(run, Message) else str(run)),
                    tool_call_id=tool_call_id,
                    citations=run.citations if isinstance(run, Message) else None,
                    sources=run.sources if isinstance(run, Message) else None,
                    logger=self.logger.getChild(Message.__name__),
                )
            )

            self.logger.debug(f"BL::StateManager::_process_tools_called::Tool run {tool_call_id} of {tool.__class__.__name__} appended to extension.")

            if run is None and complete:
                t_name = tool.__class__.__name__
                self.logger.warning(
                    f"""BL::StateManager::_process_tools_called::Tool {t_name} returned None.
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
                self.logger.debug(f"BL::StateManager::_process_tools_called::Tool {tool.__name__} on_validation_error returned False. Stoping loop over tool calls.")
                complete = False

            # We add exactly one tool message for each tool call, mandatory
            extension.append(
                Message.TOOL(
                    content=(handled.content if isinstance(handled, Message) else str(handled)),
                    tool_call_id=tool_call_id,
                    citations=handled.citations if isinstance(handled, Message) else None,
                    sources=handled.sources if isinstance(handled, Message) else None,
                    logger=self.logger.getChild(Message.__name__),
                )
            )

            self.logger.debug(f"BL::StateManager::_process_tools_called::Tool handling {tool_call_id} of {tool.__name__} appended to extension.")

            if handled is None and complete:
                t_name = tool.__name__
                self.logger.warning(
                    f"""BL::StateManager::_process_tools_called::Tool {t_name} on_validation_error returned None.
                    \nIn the mean time, the completion loop is supposed to continue.
                    \nThat means that next iteration will try to LLM.complete()
                        with a ToolMessage(content=None).
                    \nIts highly advised to return False in {t_name}.on_validation_error().
                    \nYou should also make sure {t_name} correctly
                        updated the frontend messages along wth the context."""
                )

        debug_store = self.messages.filter(lambda x: x.role == Role.USER and bool(x._remote)).last()

        if debug_store and message.tool_calls:
            debug_store.update(
                debug_store.content,
                debug={
                    **debug_store.debug,
                    "_tool_calls": debug_store.debug.get("_tool_calls", [])
                    + [
                        {
                            "role": message.role.value,
                            "content": message.content,
                            "original_content": message.original_content,
                            "tools_called": message.tool_calls,
                            "citations": message.citations,
                            "sources": message.sources,
                        }
                    ]
                    + [
                        {
                            "role": m.role.value,
                            "content": m.content,
                            "original_content": message.original_content,
                            "tool_call_id": m.tool_call_id,
                            "citations": m.citations,
                            "sources": m.sources,
                        }
                        for m in extension
                    ],
                },
            )

        elif message.tool_calls:
            self.logger.warning("""BL::StateManager::_process_tools_called::No user message found in context. Cannot update debug information for tool calls.""")

        self.ctx.extend(extension)

        self.logger.debug(f"BL::StateManager::_process_tools_called::Extension of {len(extension)} tool messages appended to context.")

        return complete and (bool(tools_called) or bool(tools_not_called))

    def call(
        self,
        message: Message,
        extra: dict | None = None,
        out: Message | None = None,
        raise_on_missing_tool: bool = False,
    ) -> Tuple[List[ToolCalled], List[ToolNotCalled], bool]:
        """
        Facilitates calling registered tools with a given message.

        Args:
            message (Message): The message to process with tools.
            extra (dict, optional): Additional parameters to pass to tools during processing.
            out (Message, optional): An output message that may be modified by tools.
            raise_on_missing_tool (bool): If True, raises an exception when a required tool is missing.

        Returns:
            Tuple[List[ToolCalled], List[ToolNotCalled], bool]: A tuple containing lists of tools that were called and not called,
            and a boolean indicating if the process should continue.

        Usage:
            This method is central for tool execution, handling the orchestration of tool calls in response to message events, applying additional parameters,
            and managing the continuation of processing based on tool outputs.
        """
        tools_called, tools_not_called = self._call_tools(message=message, extra=extra or {}, out=out, raise_on_missing_tool=raise_on_missing_tool)

        complete = self._process_tools_called(message=message, tools_called=tools_called, tools_not_called=tools_not_called)

        self.logger.debug(f"BL::StateManager::call::Finished running {len(tools_called)} tools.")

        return tools_called, tools_not_called, complete

    def complete(
        self,
        message: Message | None = None,
        out: Message | None = None,
        start_text: str = "",
        tool_choice: type[BaseModel] | None = None,
        schema: type[BaseModel] | None = None,
        search_context: List[unique_sdk.Integrated.SearchResult] | None = None,
        output_json: bool = False,
        completion_name: str = "",
    ) -> Message:
        """
        Completes the processing of a message or a sequence within the current context by optionally involving tool interactions and language model outputs.

        Args:
            message (Message | None): The message to be processed or None to use the existing context.
            out (Message | None): An optional message that may be updated with the completion results.
            start_text (str): Initial text to set the context or prompt for language model generation.
            tool_choice (type[BaseModel] | None): If specified, forces the use of a particular tool for this operation.
            output_json (bool): If True, returns the output in JSON format. Passed to LLM.complete()
            completion_name (str): The name of the completion for logging purposes.
            search_context (List[unique_sdk.Integrated.SearchResult] | None): The search context to use for the completion.

        Returns:
            Message: The message generated or modified as a result of the completion process.

        Usage:
            This method is critical for integrating various components of the system to generate a cohesive response or output based on the input message,
            context, and system capabilities.
        """
        if isinstance(message, str):
            message = Message.USER(message, logger=self.logger.getChild(Message.__name__))

        if message:
            self.logger.debug(f"BL::StateManager::complete::Completing message {message.role if message else "None"}")

        if message and message not in self.ctx:
            ctx = self.ctx.append(message)
            self.logger.debug(f"BL::StateManager::complete::Appending message {message.role if message else "None"} to context.")
        else:
            self.logger.debug(f"BL::StateManager::complete::Message {message.role if message else "None"} already in context.")
            ctx = self.ctx

        self.logger.debug("BL::StateManager::complete::Filtering context for empty assistant messages without content nor tools.")

        ctx = ctx.filter(lambda x: x.role != Role.ASSISTANT or bool(x.content) or bool(x.tool_calls))

        completion = self.llm.complete(
            messages=ctx,
            tools=self.tools,
            out=out,
            start_text=start_text,
            tool_choice=tool_choice,
            schema=schema,
            output_json=output_json,
            completion_name=completion_name,
            search_context=search_context,
        )

        self.logger.debug(f"BL::StateManager::complete::Appending completion to context: {completion.role if completion else "None"}")

        self.ctx.append(completion)

        return completion

    def loop(
        self,
        message: Message | None = None,
        out: Message | None = None,
        start_text: str = "",
        tool_choice: type[BaseModel] | None = None,
        schema: type[BaseModel] | None = None,
        raise_on_max_iterations: bool = False,
        raise_on_missing_tool: bool = False,
        output_json: bool = False,
        completion_name: str = "",
        search_context: List[unique_sdk.Integrated.SearchResult] | None = None,
    ) -> List[Tuple[Message, List[ToolCalled], List[ToolNotCalled]]]:
        """
        Executes a loop of message processing and tool interactions to handle complex scenarios that require iterative processing.

        Args:
            message (Message | None): The starting message for the loop or None to start with the current context.
            out (Message | None): An optional message to collect outputs.
            start_text (str): Initial text to prompt processing in each iteration.
            tool_choice (type[BaseModel] | None): Specifies a particular tool to use throughout the iterations.
            raise_on_max_iterations (bool): If True, raises an exception when the maximum number of iterations is reached.
            raise_on_missing_tool (bool): If True, raises an exception when a required tool is missing.
            output_json (bool): If True, returns the output in JSON format. Passed to LLM.complete()
            completion_name (str): The name of the completion for logging purposes.

        Returns:
            List[Tuple[Message, List[ToolCalled], List[ToolNotCalled]]]: A list of results from each iteration, including messages and tool interaction outcomes.

        Usage:
            This method is designed for scenarios where a single pass through the system's processing capabilities is insufficient, allowing for dynamic adjustments
            and re-evaluation of conditions in response to evolving contexts.
        """
        complete = True

        loop_iteration = 0

        completions: List[Tuple[Message, List[ToolCalled], List[ToolNotCalled]]] = []

        self.logger.debug(
            f"""BL::StateManager::loop::Starting completion loop with message {message.role if message else "None"}. Max {self.config.FUNCTION_CALL_MAX_ITERATIONS} iterations."""
        )

        while complete and loop_iteration < self.config.FUNCTION_CALL_MAX_ITERATIONS:
            self.logger.debug(f"Completing iteration {loop_iteration}.")

            completion = self.complete(
                message=message,
                out=out,
                start_text=start_text,
                tool_choice=tool_choice,
                schema=schema,
                output_json=output_json,
                completion_name=completion_name,
                search_context=search_context,
            )

            self.logger.debug(f"BL::StateManager::loop::Calling tools for completion {completion.role}.")

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

            self.logger.debug(f"BL::StateManager::loop::{len(tools_called)} Tools called for completion {completion.role}.")

            loop_iteration += 1

        if loop_iteration >= self.config.FUNCTION_CALL_MAX_ITERATIONS:
            self.logger.warning(f"BL::StateManager::loop::Max iterations reached. Stopping loop. Raise on max iterations: {raise_on_max_iterations}")
            if raise_on_max_iterations:
                raise ValueError("BL::StateManager::loop::Max iterations reached.")

        return completions

    def stream(
        self,
        message: Message | None = None,
        out: Message | None = None,
        start_text: str = "",
        output_json: bool = False,
        schema: type[BaseModel] | None = None,
        completion_name: str = "",
        search_context: List[unique_sdk.Integrated.SearchResult] | None = None,
    ) -> Message:
        """
        Streams processing of messages, potentially in a real-time environment, handling one message at a time.

        Args:
            message (Message | None): The message to start streaming processing for.
            out (Message | None): An output message that may be continuously updated.
            start_text (str): Initial text to prime the language model or processing logic.
            output_json (bool): If True, returns the output in JSON format. Passed to LLM.complete()
            completion_name (str): The name of the completion for logging purposes.

        Returns:
            Message: The updated message after processing the input or current context.

        Usage:
            Used in scenarios where messages need to be processed in a streaming or ongoing fashion, adapting to incoming data in real-time or near-real-time.
        """
        self.logger.debug(f"BL::StateManager::stream::Starting stream with message {message.role if message else "None"}.")
        return self.complete(
            message=message,
            out=out or self.last_ass_message,
            start_text=start_text,
            output_json=output_json,
            schema=schema,
            completion_name=completion_name,
            search_context=search_context,
        )

    def clear(self) -> int:
        """
        Clears all messages and resets the context to an initial state.

        Returns:
            int: The number of messages cleared from the context.

        Usage:
            This method provides a way to reset the system, clearing all stored messages and contexts, typically used in situations requiring a fresh start or
            in response to specific system states.
        """
        self.logger.debug("BL::StateManager::clear::Clearing all messages and context.")
        self.ctx.clear()
        return self.messages.delete()

    def pre_module_hook(self) -> None:
        """
        Executed before running the module
        """
        pass

    def post_module_hook(self) -> None:
        """
        Executed before running the module.
        Will run even if the module raises and error.
        """
        pass

    def reset(self) -> "StateManager":
        """
        Reset extra, tools and context.
        If you want to reset the managers, you should use the fork method.
        When using the state from within a tool, you should use the fork method to avoid side effects.
        """

        self.logger.info("BL::StateManager::reset::Resetting StateManager.")

        self._llm = self._LanguageModelManager(
            event=self.event,
            model=self.cfg.languageModel or self.cfg.LLM_DEFAULT_MODEL,
            timeout=self.cfg.LLM_TIMEOUT,
            seed=self.cfg.LLM_SEED,
            context_max_tokens=self.cfg.CONTEXT_WINDOW_TOKEN_LIMIT,
            logger=self.logger.getChild(self._LanguageModelManager.__name__),
        )

        self._messages = self._MessageManager(
            event=self.event,
            tokenizer=self._llm.tokenizer,
            logger=self.logger.getChild(self._MessageManager.__name__),
        )

        self._files = self._FileManager(
            event=self.event,
            tokenizer=self._llm.tokenizer,
            logger=self.logger.getChild(self._FileManager.__name__),
        )

        self._storage = self._StorageManager(
            event=self.event,
            store=self.messages.first() or self.messages.create(Message.ASSISTANT("")),
            logger=self.logger.getChild(self._StorageManager.__name__),
        )

        self._extra = {}
        self._data = Store()
        self._tools = []
        self._ctx = self.messages.all(force_refresh=True).fork().filter(lambda x: bool(x.content) or bool(x.tool_calls)).expand()
        return self

    def fork(self) -> "StateManager":
        """
        Fork the current state manager.
        Based on same event, it'll create a new instance of the state manager with the same configuration.
        Hence, managers will be reset, as well as the context and the tools.

        When using the state from within a tool, you should use this method to avoid side effects.
        If you just want to reset the context and the tools, you can use the reset method.
        """
        return self.__class__(event=self.event, conf=self.conf, logger=self.logger, managers=self._managers, app=self.app)
