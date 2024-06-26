from abc import ABC, abstractmethod

from blue_lugia.app import App


class AppFactory(ABC):
    @abstractmethod
    def create(self, name: str) -> App: ...
