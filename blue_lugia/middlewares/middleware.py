import logging
from typing import Any, List

from blue_lugia.enums import Hook
from blue_lugia.models import ExternalModuleChosenEvent


class Middleware:
    _event: ExternalModuleChosenEvent
    _logger: logging.Logger

    _hooks: List[Hook]

    def __init__(self, event: ExternalModuleChosenEvent, logger: logging.Logger | None = None, hooks: List[Hook] | None = None, **kwargs) -> None:
        self._event = event
        self._logger = logger or kwargs.get("logger", logging.getLogger(__name__))
        self._hooks = hooks or kwargs.get("hooks", [])

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def event(self) -> ExternalModuleChosenEvent:
        return self._event

    @property
    def hooks(self) -> List[Hook]:
        return self._hooks

    def listen(self, hook: Hook) -> "Middleware":
        self._hooks.append(hook)
        return self

    def ingest(self, hook: Hook, *args, **kwargs) -> None:
        if hook in self._hooks:
            self.logger.debug(f"BL::Middleware::{self.__class__.__name__}::ApplingOn::{hook.value}")
            self(hook, *args, **kwargs)
            self.logger.debug(f"BL::Middleware::{self.__class__.__name__}::AppledOn::{hook.value}")

    def __call__(self, hook: Hook, *args, **kwargs) -> Any:
        pass
