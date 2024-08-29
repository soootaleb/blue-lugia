import io
import sqlite3
from typing import Any

import numpy as np

from blue_lugia.models.query import Q


class DataSource:
    _metadata: dict[str, Any]
    _opened: bool = False

    def __init__(self, metadata: dict | None = None, **kwargs) -> None:
        self._metadata = metadata or {}
        self.metadata.update(kwargs)

    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata

    def open(self) -> bool:
        if not self._opened:
            self._opened = True
        return self._opened

    def read(self, query: Q) -> bytes:
        return b""

    def write(self, data: bytes | bytearray | np.ndarray | memoryview) -> int:
        return 0

    def close(self) -> bool:
        if self._opened:
            self._opened = False
        return True


class InMemoryDataSource(DataSource):
    _source: io.BytesIO

    @property
    def source(self) -> io.BytesIO:
        return self._source

    def open(self) -> bool:
        if opened := super().open():
            self._source = io.BytesIO()
        return opened

    def read(self, query: Q) -> bytes:
        self.source.seek(0)
        return self.source.read()

    def write(self, data: bytes | bytearray | np.ndarray | memoryview) -> int:
        return self.source.write(data)

    def close(self) -> bool:
        if closed := super().close():
            self.source.close()
        return closed


class FileDataSource(InMemoryDataSource):
    _file: io.FileIO

    def __init__(self, file_path: str, metadata: dict | None = None, **kwargs) -> None:
        super().__init__(metadata=metadata, file_path=file_path, **kwargs)

    @property
    def file(self) -> io.FileIO:
        return self._file

    def open(self) -> bool:
        try:
            opened = super().open()
            if opened:
                self._file = io.FileIO(self.metadata.get("file_path", ""), mode="r+")
                self._source = io.BytesIO(self.file.read())
            return opened
        except FileNotFoundError as e:
            print(f"An error occurred: {e}")
            return False

    def read(self, query: Q) -> bytes:
        self.file.seek(0)
        self.source.seek(0)
        return self.file.read()

    def write(self, data: bytes | bytearray | np.ndarray | memoryview) -> int:
        self.source.write(data)
        return self.file.write(data)

    def close(self) -> bool:
        if self.file and self.source and super().close():
            self.file.close()
        return super().close()


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

    def read(self, query: Q, params: tuple | None = None) -> list:
        try:
            sql, params = query.sql()
            self.cursor.execute(sql, params or ())
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
