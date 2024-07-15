import concurrent.futures
import datetime
import inspect
import json
import os
import traceback
from http import HTTPStatus
from logging.config import dictConfig
from typing import Any, Callable, Generic, List, Tuple, Type, cast
from urllib.parse import urlparse

import toml
import unique_sdk
from flask import Flask, Response, jsonify, request
from sseclient import SSEClient

from blue_lugia.commands import command
from blue_lugia.config import ConfType, ModuleConfig
from blue_lugia.enums import Role
from blue_lugia.managers import (
    FileManager,
    LanguageModelManager,
    Manager,
    MessageManager,
    StorageManager,
)
from blue_lugia.models import ExternalModuleChosenEvent
from blue_lugia.models.event import AssistantMessage, Payload, UserMessage
from blue_lugia.state import StateManager


class App(Flask, Generic[ConfType]):
    """
    App class extends the Flask framework to include additional functionality
    for handling external module events and managing state.

    Args:
        import_name (str): The name of the application package.
        static_url_path (str | None, optional): The URL path for the static files.
        static_folder (str | os.PathLike[str] | None, optional): The folder for the static files.
        static_host (str | None, optional): The host for the static files.
        host_matching (bool, optional): Enable or disable host matching.
        subdomain_matching (bool, optional): Enable or disable subdomain matching.
        template_folder (str | os.PathLike[str] | None, optional): The folder for the templates.
        instance_path (str | None, optional): The path for the instance folder.
        instance_relative_config (bool, optional): Enable or disable relative instance path.
        root_path (str | None, optional): The root path for the application.

    Methods:
        of(module: Callable[[ExternalModuleChosenEvent], bool]) -> "App":
            Sets the module to be processed and returns the App instance.
        configured(conf: Type[ConfType]) -> "App":
            Configures the module configuration and returns the App instance.
        managed(state_manager: Type[StateManager]) -> "App":
            Sets the state manager and returns the App instance.
        threaded(threaded: bool = True) -> "App":
            Enables or disables threaded execution and returns the App instance.
    """

    _module: Callable[[StateManager[ConfType]], bool | None] | None

    _assistant_id: str | None

    _threaded: bool = True
    _executor: concurrent.futures.ThreadPoolExecutor

    _conf: ConfType
    _state_manager: Type[StateManager[ConfType]] | None = None

    _error_handlers: List[Tuple[Type[Exception], Callable[[Exception, StateManager[ConfType]], None] | None]]

    _managers: dict[str, Type[Manager]]

    _commands: dict[str, Callable[[StateManager[ConfType], list[str]], bool | None]]

    def __init__(
        self,
        import_name: str,
        static_url_path: str | None = None,
        static_folder: str | os.PathLike[str] | None = "static",
        static_host: str | None = None,
        host_matching: bool = False,
        subdomain_matching: bool = False,
        template_folder: str | os.PathLike[str] | None = "templates",
        instance_path: str | None = None,
        instance_relative_config: bool = False,
        root_path: str | None = None,
    ) -> None:
        # load_dotenv()

        super().__init__(
            import_name,
            static_url_path,
            static_folder,
            static_host,
            host_matching,
            subdomain_matching,
            template_folder,
            instance_path,
            instance_relative_config,
            root_path,
        )

        self._module = None

        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=15)
        self._error_handlers = []
        self._managers = {}

        self._commands = {}

        self.configure_logging()

        self.configured(cast(Type[ConfType], ModuleConfig))

        self.route("/")(self._hello)
        self.route("/version")(self._version)
        self.route("/webhook", methods=["POST"])(self._webhook)  # type: ignore

    @property
    def sse_client(self) -> SSEClient:
        base_url = urlparse(self._conf.API_BASE)
        url = f"{base_url.scheme}://{base_url.netloc}/public/event-socket/events/stream?subscriptions=unique.chat.external-module.chosen"
        self.logger.debug(f"Connecting to {url}")
        return SSEClient(
            url=url,
            headers={
                "Authorization": f"Bearer {self._conf.API_KEY}",
                "x-app-id": self._conf.APP_ID,
                "x-company-id": self._conf.COMPANY_ID,
            },
        )

    @property
    def version(self) -> dict[str, Any]:
        version = {}

        if self._module:
            module: Callable = self._module
            module_file_path = inspect.getfile(module)
            parent = os.path.dirname(module_file_path)

            if not os.path.exists(os.path.join(parent, "pyproject.toml")):
                parent = os.path.dirname(parent)

            pyproject = os.path.join(parent, "pyproject.toml")

            try:
                with open(pyproject) as file:
                    version = toml.load(file)
            except FileNotFoundError:
                self.logger.debug(f"BL:App::version::Could not find pyproject.toml in {parent}")
                pass
        else:
            version["error"] = "Module not set"

        return version

    def configure_logging(self) -> None:
        dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "%(asctime)s - %(name)s - %(levelname)-8s - %(message)s",
                        "datefmt": "%Y-%m-%d %H:%M:%S",
                    }
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "level": "DEBUG",
                        "formatter": "default",
                    }
                },
                "root": {"level": "DEBUG", "handlers": ["console"]},
                "loggers": {
                    "unique": {
                        "level": "WARNING",
                    },
                    "urllib3": {
                        "level": "WARNING",
                    },
                    "httpcore": {
                        "level": "WARNING",
                    },
                    "openai": {
                        "level": "WARNING",
                    },
                    "https": {
                        "level": "WARNING",
                    },
                },
            }
        )

    def register(
        self,
        command: str,
        handler: Callable[[StateManager[ConfType], list[str]], bool | None],
    ) -> "App":
        """
        Registers a command with the handler and returns the App instance.

        Args:
            command (str): The command to register.
            handler (Callable[[StateManager[ConfType], list[str]], bool]): The handler for the command.

        Returns:
            App: The current instance of the App.
        """
        self._commands[command] = handler
        self.logger.info(f"Command {command} registered.")
        return self

    def of(self, module: Callable[[StateManager[ConfType]], bool | None]) -> "App":
        """
        Sets the module to be processed and returns the App instance.

        Args:
            module (Callable[[StateManager[ConfType]], bool]): The module to process events.

        Returns:
            App: The current instance of the App.
        """
        self._module = module
        self.logger.info(f"Module {module.__name__} set.")
        return self

    def configured(self, conf: Type[ConfType]) -> "App":
        """
        Configures the module configuration and returns the App instance.

        Args:
            conf (Type[ConfType]): The configuration class for the module.

        Returns:
            App: The current instance of the App.
        """
        self._conf = conf()

        unique_sdk.api_key = self._conf.API_KEY
        unique_sdk.app_id = self._conf.APP_ID
        unique_sdk.api_base = self._conf.API_BASE

        if not self._conf.API_KEY:
            self.logger.warning("BL::App::configured::API_KEY not set.")
        if not self._conf.APP_ID:
            self.logger.warning("BL::App::configured::APP_ID not set.")
        if not self._conf.API_BASE:
            self.logger.warning("BL::App::configured::API_BASE not set.")

        self.logger.info(f"Configuration {conf.__name__} set.")
        return self

    def managed(self, state_manager: Type[StateManager]) -> "App":
        """
        Sets the state manager and returns the App instance.

        Args:
            state_manager (Type[StateManager]): The state manager class.

        Returns:
            App: The current instance of the App.
        """
        self._state_manager = state_manager
        self.logger.info(f"State manager {state_manager.__name__} set.")
        return self

    def threaded(self, threaded: bool = True) -> "App":
        """
        Enables or disables threaded execution and returns the App instance.

        Args:
            threaded (bool, optional): Flag to enable or disable threaded execution. Defaults to True.

        Returns:
            App: The current instance of the App.
        """
        self._threaded = threaded
        self.logger.info(f"Threaded execution set to {threaded}.")
        return self

    def using(self, manager: Type[Manager]) -> "App":
        if not issubclass(manager, Manager):
            raise TypeError("Manager must be a subclass of Manager")
        elif issubclass(manager, MessageManager):
            self._managers["messages"] = manager
        elif issubclass(manager, LanguageModelManager):
            self._managers["llm"] = manager
        elif issubclass(manager, FileManager):
            self._managers["files"] = manager
        elif issubclass(manager, StorageManager):
            self._managers["storage"] = manager
        else:
            raise ValueError("Manager not recognized")

        self.logger.debug(f"Manager {manager.__name__} set.")

        return self

    def handle(
        self,
        exception: Type[Exception],
        handler: Callable[[Exception, StateManager[ConfType]], None] | None = None,
    ) -> "App":
        """
        Adds an error handler

        The error handle is a subclass of Exception and should implement the handle(self, state) method
        """
        self._error_handlers.append((exception, handler))
        self.logger.info(f"Error handler {exception.__name__} added.")
        return self

    def listen(self) -> None:
        for sse_event in self.sse_client:
            try:
                event_data = json.loads(sse_event.data or "{}")
                if "event" in event_data:
                    self._type_event_and_run_module(
                        {
                            "id": "evt_mock_event_1234",
                            "version": "1.0.0",
                            "createdAt": datetime.datetime.now().timestamp(),
                            **event_data,
                        }
                    )
            except Exception as e:
                self.logger.error(f"BL::State::listen::Error processing event: {e.__class__.__name__}", exc_info=False)

    def run(
            self,
            chat_id: str,
            assistant_id: str,
            conf: dict | None = None,
            description: str = "Mock event",
            event_id: str = "evt_xyz",
            version: str = "1.0.0",
            event_type: str ="unique.chat.external-module.chosen",
            user_message: str = "User message",
            user_id: str | None = None,
            user_message_id: str = "msg_xyz",
            assistant_message_id: str = "msg_123",
            company_id: str | None = None,
            event_created_at: Callable[[], datetime.datetime] = datetime.datetime.now,
            user_message_created_at: Callable[[], datetime.datetime] = datetime.datetime.now,
            assistant_message_created_at: Callable[[], datetime.datetime] = datetime.datetime.now,
        ) -> None:
        """
        Execute the webhook using the provided user id and chat id.

        You can define the event configuration. Specify a custom configuration to define default values.
        - envars starting with MOD_CONF_ will be set as the configuration. (MOD_CONF_X will be accessible with state.conf.X)
        - you can also pass a dictionary with the configuration, which will override the envars
        """

        config = {}

        # take all evars starting with MOD_CONF_ and add them to the configuration
        for key, value in os.environ.items():
            if key.startswith("MOD_CONF_"):
                config[key[9:]] = value

        config.update(conf or {})

        event = ExternalModuleChosenEvent(
            id=event_id,
            version=version,
            event=event_type,
            created_at=event_created_at(),
            user_id=user_id or self._conf.USER_ID,
            company_id=company_id or self._conf.COMPANY_ID,
            payload=Payload(
                name=self.name,
                description=description,
                configuration=config,
                chat_id=chat_id,
                assistant_id=assistant_id,
                user_message=UserMessage(
                    id=user_message_id,
                    text=user_message,
                    created_at=user_message_created_at(),
                ),
                assistant_message=AssistantMessage(
                    id=assistant_message_id,
                    created_at=assistant_message_created_at(),
                ),
            ),
        )

        return self._run_module(event)

    def _type_event(self, event: dict[str, Any]) -> ExternalModuleChosenEvent:
        target_timezone = datetime.timezone(datetime.timedelta(hours=2))

        return ExternalModuleChosenEvent(
            id=event["id"],
            version=event["version"],
            event=event["event"],
            created_at=datetime.datetime.fromtimestamp(event["createdAt"]),
            user_id=event["userId"],
            company_id=event["companyId"],
            payload=Payload(
                name=event["payload"]["name"],
                description=event["payload"]["description"],
                configuration=event["payload"]["configuration"],
                chat_id=event["payload"]["chatId"],
                assistant_id=event["payload"]["assistantId"],
                user_message=UserMessage(
                    id=event["payload"]["userMessage"]["id"],
                    text=event["payload"]["userMessage"]["text"],
                    created_at=datetime.datetime.fromisoformat(event["payload"]["userMessage"]["createdAt"]).astimezone(target_timezone),
                ),
                assistant_message=AssistantMessage(
                    id=event["payload"]["assistantMessage"]["id"],
                    created_at=datetime.datetime.fromisoformat(event["payload"]["assistantMessage"]["createdAt"]).astimezone(target_timezone),
                ),
            ),
        )

    def _run_module(self, event: ExternalModuleChosenEvent) -> None:  # noqa: C901
        if not self._state_manager:
            self._state_manager = StateManager[ConfType]

        if not self._conf:
            self._conf = cast(ConfType, ModuleConfig())

        self._conf = self._conf.model_copy(update=event.payload.configuration)

        state = self._state_manager(
            event=event,
            conf=self._conf,
            logger=self.logger.getChild(self._state_manager.__name__),
            managers=self._managers,
            app=self,
        )

        try:
            last_user_message = state.last_usr_message

            if last_user_message and last_user_message.content and last_user_message.is_command and state.conf.ALLOW_COMMANDS:
                user_input = last_user_message.content[1:].split()
                command_name = user_input[0]

                if command_name in self._commands:  # noqa: SIM108
                    exec_module = self._commands[command_name](state, user_input[1:])
                else:
                    exec_module = command(state, last_user_message.content[1:].split())
            else:
                exec_module = True

            if isinstance(exec_module, bool) and exec_module:
                try:
                    state.pre_module_hook()
                    if self._module:
                        self._module(state)
                    else:
                        raise ValueError("Module not set.")
                finally:
                    state.post_module_hook()

        except Exception as exception:
            handler = None

            for h in self._error_handlers:
                if isinstance(exception, h[0]):
                    handler = h
                    break

            try:
                if hasattr(exception, "handle"):
                    exception.handle(state)  # type: ignore
                elif handler and handler[1]:
                    handler[1](exception, state)
                else:
                    raise exception

            except Exception as e:
                self.logger.error(f"Error running error handler: {e}", exc_info=True)

                try:
                    self.root_exception_handler(exception, state)
                except Exception as exc:
                    self.logger.error(f"Error running root error handler: {exc}", exc_info=True)

        finally:
            if len(state.messages.all(force_refresh=True)):
                last_message = state.messages.last()

                if last_message and not last_message.content:
                    last_message.update("Oops.")

    def save_exception(self, e: Exception, state: StateManager[ConfType]) -> None:
        tb = traceback.extract_tb(e.__traceback__)

        last_trace = tb[-1]
        filename = last_trace.filename
        line = last_trace.lineno

        last_user_message = state.messages.filter(lambda x: x.role == Role.USER).last()

        if last_user_message:
            last_user_message.update(
                content=last_user_message.content,
                debug={
                    "_debug": {
                        "error": str(e),
                        "filename": filename,
                        "line": line,
                        "traceback": traceback.format_exc().splitlines(),
                    }
                },
            )

        else:
            self.logger.error("No user message found to attach exception to.")

    def root_exception_handler(self, e: Exception, state: StateManager[ConfType]) -> None:
        self.logger.error(f"Error running module: {e}", exc_info=True)

        self.save_exception(e, state)

        error_message = state.conf.ON_FAILURE

        if state.conf.ON_FAILURE_MESSAGE_OVERRIDE:
            error_message = state.conf.ON_FAILURE_MESSAGE_OVERRIDE

        if state.conf.ON_FAILURE_DISPLAY_ERROR:
            error_message += f"\n\n```{e}```"

        if state.last_ass_message:
            state.last_ass_message.update(error_message)
        else:
            self.logger.error("No last_ass_message found to set error message")

    def _type_event_and_run_module(self, event: dict) -> None:
        if event and event["event"] == "unique.chat.external-module.chosen":
            external_event = self._type_event(event)
            if external_event.payload.name.lower() == self.name.lower():
                if self._threaded:
                    self._executor.submit(self._run_module, external_event)
                else:
                    self._run_module(external_event)

    def _hello(self) -> Tuple[str, int]:
        return f"Hello from the {self.name} tool! 🚀", 200

    def _version(self) -> Tuple[dict, int]:
        return self.version, 200

    def _webhook(self) -> Tuple[str, int] | Tuple[Response, int] | None:
        event = None
        payload = request.data

        self.logger.info("Received webhook request.")

        try:
            event = json.loads(payload)
        except json.decoder.JSONDecodeError:
            return "Invalid payload", 400

        if self._conf and self._conf.ENDPOINT_SECRET:
            # Only verify the event if there is an endpoint secret defined
            # Otherwise use the basic event deserialized with json
            sig_header = request.headers.get("X-Unique-Signature", "XXXXXX")
            timestamp = request.headers.get("X-Unique-Created-At", "XXXXXX")

            self.logger.info(f"X-Unique-Signature: {'*' * 3 + sig_header[-3:]}")
            self.logger.info(f"UNIQUE_API_KEY: {'*' * 3 + self._conf.API_KEY[-3:]}")
            self.logger.info(f"UNIQUE_APP_ID: {'*' * 3 + self._conf.APP_ID[-3:]}")

            if not sig_header or not timestamp:
                self.logger.info("⚠️  Webhook signature or timestamp headers missing.")
                return jsonify(success=False), HTTPStatus.BAD_REQUEST

            try:
                event = unique_sdk.Webhook.construct_event(payload, sig_header, timestamp, self._conf.ENDPOINT_SECRET)
            except unique_sdk.SignatureVerificationError as e:
                self.logger.info("⚠️  Webhook signature verification failed. " + str(e))

                try:
                    unique_sdk.Message.modify(
                        user_id=event["userId"],
                        company_id=event["companyId"],
                        chatId=event["payload"]["chatId"],
                        id=event["payload"]["assistantId"],
                        text="Sorry, I am unavailable right now",
                        debugInfo={
                            "error": str(e),
                            "keys": {
                                "api_key": "*" * 3 + self._conf.API_KEY[-3:],
                                "app_id": "*" * 3 + self._conf.APP_ID[-3:],
                                "signature": "*" * 3 + sig_header[-3:],
                                "timestamp": timestamp,
                            },
                        },
                    )  # type: ignore

                except Exception as exc:
                    self.logger.error(f"I can't take it anymore: {exc}", exc_info=True)

                return jsonify(success=False), HTTPStatus.BAD_REQUEST

        self._type_event_and_run_module(event)

        return "OK", 200
