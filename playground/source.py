import io
import json
import sqlite3
from typing import Any

import numpy as np


class DataSource:
    _metadata: dict[str, Any]

    def __init__(self, metadata: dict | None = None, **kwargs) -> None:
        self._metadata = metadata or {}
        self.metadata.update(kwargs)

    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata

    def open(self) -> bool:
        return True

    def read(self, size: int | None = None) -> bytes:
        return b""

    def write(self, data: bytes | bytearray | np.ndarray | memoryview) -> int:
        return 0

    def close(self) -> bool:
        return True


class InMemoryDataSource(DataSource):
    _source: io.BytesIO

    @property
    def source(self) -> io.BytesIO:
        return self._source

    def open(self) -> None:
        self._source = io.BytesIO()

    def read(self, size: int | None = None) -> bytes:
        self.source.seek(0)
        return self.source.read(size)

    def write(self, data: bytes | bytearray | np.ndarray | memoryview) -> int:
        return self.source.write(data)

    def close(self) -> None:
        return self.source.close()


class JSONFileDataSource(InMemoryDataSource):
    _data: dict

    def open(self) -> bool:
        try:
            with open(self.metadata.get("file_path", "")) as file:
                self._data = json.load(file)
            return True
        except FileNotFoundError as e:
            print(f"An error occurred: {e}")
            return False

    def read(self, key: str | None = None) -> dict | str | None:
        return self._data.get(key) if key else self._data

    def write(self, data: Any) -> int:
        self._data.update(data)
        with open(self.metadata.get("file_path", ""), "w") as file:
            json.dump(self._data, file)
        return len(data)

    def close(self) -> bool:
        return True


class SQLDataSource(DataSource):
    _connection: sqlite3.Connection
    _cursor: sqlite3.Cursor

    def open(self) -> bool:
        try:
            self.connection = sqlite3.connect(self.metadata["db_path"])
            self.cursor = self.connection.cursor()
            return True
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return False

    def read(self, query: str, params: tuple | None = None) -> list:
        try:
            self.cursor.execute(query, params or ())
            return self.cursor.fetchall()  # Retrieves all rows as a list of tuples
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return []

    def write(self, query: str, params: tuple | None = None) -> int:
        try:
            self.cursor.execute(query, params or ())
            self.connection.commit()
            return self.cursor.rowcount  # Number of rows affected
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return 0

    def close(self) -> bool:
        if self.connection:
            self.connection.close()
            return True
        return False
