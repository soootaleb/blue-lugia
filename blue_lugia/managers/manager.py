import logging

from blue_lugia.models import ExternalModuleChosenEvent


class Manager:
    _event: ExternalModuleChosenEvent
    _logger: logging.Logger

    def __init__(self, event: ExternalModuleChosenEvent, logger: logging.Logger | None = None, **kwargs) -> None:
        self._event = event
        self._logger = logger or kwargs.get("logger", logging.getLogger(__name__))

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def event(self) -> ExternalModuleChosenEvent:
        return self._event
