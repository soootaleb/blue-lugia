import io
import pickle
import sqlite3
from typing import Any

import numpy as np

from blue_lugia.managers.file import FileManager
from blue_lugia.models.file import ChunkList, File
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

    def write(self, data: bytes | bytearray | np.ndarray | memoryview, params: tuple | None = None) -> int:
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

    def write(self, data: bytes | bytearray | np.ndarray | memoryview, params: tuple | None = None, at: int = 0, append: bool = True) -> int:
        self.source.seek(at, io.SEEK_END if append else io.SEEK_SET)
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

    def write(self, data: bytes | bytearray | np.ndarray | memoryview, params: tuple | None = None, at: int = 0, append: bool = True) -> int:
        self.file.seek(at, io.SEEK_END if append else io.SEEK_SET)
        self.source.seek(at, io.SEEK_END if append else io.SEEK_SET)
        self.source.write(data)
        return self.file.write(data)

    def close(self) -> bool:
        if self.file and self.source and super().close():
            self.file.close()
        return super().close()


class BLFileDataSource(InMemoryDataSource):
    _file: File

    def __init__(self, file: File, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._file = file

    @property
    def file(self) -> File:
        return self._file

    def open(self) -> bool:
        opened = super().open()
        if opened:
            self._source = self.file.data
        return opened

    def read(self, query: Q) -> bytes:
        self.source.seek(0)
        return self.source.read()

    def write(self, data: bytes | bytearray | np.ndarray | memoryview, params: tuple | None = None, at: int = 0, append: bool = True) -> int:
        self.source.seek(at, io.SEEK_END if append else io.SEEK_SET)
        self.source.write(data)
        if isinstance(data, (memoryview, np.ndarray)):
            data = data.tobytes()
        self.file.write(data.decode("utf-8"))
        return len(data)

    def close(self) -> bool:
        return super().close()


class BLFileManagerDataSource(InMemoryDataSource):
    _chunks: ChunkList
    _manager: FileManager

    def __init__(self, manager: FileManager, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._manager = manager

    @property
    def manager(self) -> FileManager:
        return self._manager

    @property
    def chunks(self) -> ChunkList:
        return self._chunks

    def open(self) -> bool:
        return super().open()

    def read(self, query: Q) -> bytes:
        self._chunks = self.manager.search(query=query._from or "", limit=query._limit or 1000)

        sort_key = query._order_by[0] if query._order_by else None

        if sort_key:
            if sort_key.startswith("-"):
                sort_key = sort_key[1:]
                self._chunks = self.chunks.sort(key=sort_key, reverse=True)
            else:
                self._chunks = self.chunks.sort(key=sort_key)

        chunks_dicts = [c.as_dict() for c in self.chunks]

        if query._offset:
            chunks_dicts = chunks_dicts[query._offset :]

        if query._limit:
            chunks_dicts = chunks_dicts[: query._limit]

        return pickle.dumps(chunks_dicts)

    def write(self, data: bytes | bytearray | np.ndarray | memoryview, params: tuple | None = None, at: int = 0, append: bool = True) -> int:
        raise NotImplementedError("BL::BLFileManagerDataSource::write:Can't create Chunk")

    def close(self) -> bool:
        return super().close()


class SQLiteDataSource(DataSource):
    _connection: sqlite3.Connection
    _cursor: sqlite3.Cursor

    def open(self) -> bool:
        try:
            self.connection = sqlite3.connect(self.metadata["db_path"])
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()
            return True
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return False

    def read(self, query: Q) -> list:
        try:
            sql, params = query.sql()
            self.cursor.execute(sql, params or [])
            return self.cursor.fetchall()  # Retrieves all rows as a list of tuples
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return []

    def write(self, data: bytes, params: tuple | None = None) -> int:
        try:
            self.cursor.execute(data.decode("utf-8"), params or ())
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
