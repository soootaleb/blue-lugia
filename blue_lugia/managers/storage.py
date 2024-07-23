from typing import Any

from blue_lugia.managers.manager import Manager
from blue_lugia.models import Message


class StorageManager(Manager):
    _store: Message

    def __init__(self, store: Message, **kwargs) -> None:
        super().__init__(**kwargs)
        self._store = store

    @property
    def data(self) -> dict:
        return self._store.debug.get("_store", {})

    def __getitem__(self, key: str) -> dict:
        return self.get(key)

    def __setitem__(self, key: str, value: dict) -> None:
        self.set(key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: dict | str | int | bool | list) -> dict:
        self._store.update(
            content=self._store.content,
            debug={**self._store.debug, "_store": {**self.data, key: value}},
        )
        return self.data
