import logging
from typing import Any


class Model:
    _logger: logging.Logger | None

    def __init__(
        self, logger: logging.Logger | None = None, *args: list[Any], **kwargs: logging.Logger
    ) -> None:
        self._logger = logger or kwargs.get("logger", logging.getLogger(__name__))

    @property
    def logger(self) -> logging.Logger | Any:
        return self._logger or logging.getLogger(__name__)
