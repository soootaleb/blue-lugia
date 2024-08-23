from typing import List

from blue_lugia.app import App
from blue_lugia.config import ModuleConfig
from blue_lugia.enums import Hook
from blue_lugia.middlewares import Middleware
from blue_lugia.state import StateManager


class MessageMiddleware(Middleware):
    @property
    def hooks(self) -> List[Hook]:
        event = self.event
        logger = self.logger

        return [Hook.MODULE_PRE_CALL, Hook.MODULE_POST_CALL]

    def _run_module_pre_call(self, *args, **kwargs) -> None:
        print(f"MessageMiddleware::{self.__class__.__name__}::ApplingOn::MODULE_PRE_CALL")
        print(args)
        print(kwargs)
        print(f"MessageMiddleware::{self.__class__.__name__}::AppledOn::MODULE_PRE_CALL")

    def _run_module_post_call(self, *args, **kwargs) -> None:
        print(f"MessageMiddleware::{self.__class__.__name__}::ApplingOn::MODULE_POST_CALL")
        print(args)
        print(kwargs)
        print(f"MessageMiddleware::{self.__class__.__name__}::AppledOn::MODULE_POST_CALL")

    def __call__(self, hook: Hook, *args, **kwargs) -> None:
        if hook == Hook.MODULE_PRE_CALL:
            self._run_module_pre_call(*args, **kwargs)
        elif hook == Hook.MODULE_POST_CALL:
            self._run_module_post_call(*args, **kwargs)
        else:
            self.logger.error(f"MessageMiddleware::{self.__class__.__name__}::InvalidHook::{hook.value}")


def module(state: StateManager[ModuleConfig]) -> None:
    return


app = App("Petal").apply([MessageMiddleware]).threaded(False).of(module).listen()
