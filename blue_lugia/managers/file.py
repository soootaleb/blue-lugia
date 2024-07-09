import datetime
from typing import Any, Callable, List

import tiktoken
import unique_sdk

from blue_lugia.enums import Op, Role, SearchType
from blue_lugia.errors import ChatFileManagerError
from blue_lugia.managers.manager import Manager
from blue_lugia.models import (
    Chunk,
    ChunkList,
    File,
    FileList,
    MessageList,
)


class FileManager(Manager):
    _all: FileList
    _retrieved: bool

    _chat_only: bool
    _search_type: SearchType
    _scopes: List[str]

    _filters: List[Any]
    _filters_operator: Op

    _order_by: str | Callable | None = None
    _order_reverse: bool = False

    _mapped_operators = {
        "eq": "equals",
    }

    _tokenizer: str | tiktoken.Encoding

    def __init__(
        self,
        tokenizer: str | tiktoken.Encoding,
        chat_only: bool = False,
        search_type: SearchType = SearchType.COMBINED,
        scopes: List[str] = [],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._retrieved = False
        self._chat_only = chat_only
        self._search_type = search_type
        self._scopes = scopes if scopes else []
        self._filters = []
        self._filters_operator = Op.OR
        self._tokenizer = tokenizer
        self._all = FileList([], tokenizer=self.tokenizer, logger=self.logger.getChild(FileList.__name__))

    @property
    def tokenizer(self) -> tiktoken.Encoding:
        if isinstance(self._tokenizer, str):
            self._tokenizer = tiktoken.encoding_for_model(self._tokenizer)

        return self._tokenizer

    @property
    def uploaded(self) -> "FileManager":
        return FileManager(
            event=self._event,
            tokenizer=self.tokenizer,
            chat_only=True,
            logger=self.logger.getChild(FileManager.__name__),
        )

    def fork(self) -> "FileManager":
        file_manager = FileManager(
            chat_only=self._chat_only,
            search_type=self._search_type,
            event=self._event,
            logger=self.logger.getChild(FileManager.__name__),
            tokenizer=self.tokenizer,
        )

        file_manager._filters = self._filters.copy()
        file_manager._filters_operator = self._filters_operator
        file_manager._order_by = self._order_by
        file_manager._order_reverse = self._order_reverse
        file_manager._all = FileList(self._all, tokenizer=self.tokenizer, logger=self.logger.getChild(FileList.__name__))
        file_manager._retrieved = self._retrieved

        return file_manager

    def _cast_search(self, chunks: list[Any]) -> ChunkList:
        files_map: dict[str, File] = {}
        all_chunks = []

        for chunk in chunks:
            file_id = chunk["id"]

            if file_id not in files_map:
                files_map[file_id] = File(
                    event=self._event,
                    id=file_id,
                    name=chunk["key"],
                    mime_type=(chunk.get("metadata", {}) or {}).get("mimeType", "text/plain"),
                    chunks=ChunkList(logger=self.logger.getChild(ChunkList.__name__)),
                    tokenizer=self.tokenizer,
                    created_at=datetime.datetime.fromisoformat(chunk["createdAt"]),
                    updated_at=datetime.datetime.fromisoformat(chunk["updatedAt"]),
                    logger=self.logger.getChild(File.__name__),
                )

            chunk_to_add = Chunk(
                id=chunk["chunkId"],
                order=chunk["order"],
                content=chunk["text"],
                start_page=chunk["startPage"],
                end_page=chunk["endPage"],
                created_at=datetime.datetime.fromisoformat(chunk["createdAt"]),
                updated_at=datetime.datetime.fromisoformat(chunk["updatedAt"]),
                tokenizer=self.tokenizer,
                logger=self.logger.getChild(Chunk.__name__),
                file=files_map[file_id],
            )

            all_chunks.append(chunk_to_add)

        return ChunkList(
            all_chunks,
            tokenizer=self.tokenizer,
            logger=self.logger.getChild(ChunkList.__name__),
        )

    def _cast_content(self, files: list[Any]) -> FileList:
        files_map: dict[str, File] = {}

        for found_file in files:
            file_id = found_file["id"]
            chunks = found_file["chunks"]

            if file_id not in files_map:
                write_url = found_file.get("writeUrl", "")

                files_map[file_id] = File(
                    event=self._event,
                    id=file_id,
                    name=found_file["key"],
                    mime_type=(found_file.get("metadata", {}) or {}).get("mimeType", "text/plain"),
                    chunks=ChunkList(logger=self.logger.getChild(ChunkList.__name__)),
                    tokenizer=self.tokenizer,
                    write_url=write_url,
                    created_at=datetime.datetime.fromisoformat(found_file["updatedAt"]),
                    updated_at=datetime.datetime.fromisoformat(found_file["updatedAt"]),
                    logger=self.logger.getChild(File.__name__),
                )

            for chunk in chunks:
                chunk_to_add = Chunk(
                    id=f"{file_id}_{chunk['order']}",
                    order=chunk["order"],
                    content=chunk["text"],
                    start_page=0,
                    end_page=0,
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now(),
                    tokenizer=self.tokenizer,
                    logger=self.logger.getChild(Chunk.__name__),
                    file=files_map[file_id],
                )

                files_map[file_id].chunks.append(chunk_to_add)

        return FileList(
            files_map.values(),
            tokenizer=self.tokenizer,
            logger=self.logger.getChild(FileList.__name__),
        )

    def using(self, search_type: SearchType) -> "FileManager":
        file_manager = self.fork()
        file_manager._search_type = search_type
        return file_manager

    def scoped(self, scopes: List[str] | str) -> "FileManager":
        file_manager = self.fork()

        if isinstance(scopes, str):
            scopes = [scopes]

        if file_manager._scopes:
            self.logger.warning("BL::Manager::Files::scoped::ScopesOverwritten")

        file_manager._scopes = scopes

        return file_manager

    def search(self, query: str = "", limit: int = 1000) -> ChunkList:
        page = 1
        found_count = limit
        found_all = []

        metadata_filters = None

        if self._filters:
            last_filter = self._filters[-1]
            metadata_filters = {
                "path": [last_filter[0]],
                "operator": (self._mapped_operators[last_filter[1]] if last_filter[1] in self._mapped_operators else last_filter[1]),
                "value": last_filter[2],
            }

        while found_count > 0 and len(found_all) < limit:
            found = unique_sdk.Search.create(
                user_id=self._event.user_id,
                company_id=self._event.company_id,
                chatId=self._event.payload.chat_id,
                chatOnly=self._chat_only,
                searchString=query,
                page=page,
                scopeIds=self._scopes or None,
                searchType=self._search_type.value,
                metaDataFilter=metadata_filters,  # type: ignore
                limit=limit,
            )

            found_count = len(found["data"])
            found_all.extend(found["data"])

            page += 1

        typed_search = self._cast_search(found_all)

        if self._order_by:
            return typed_search.sort(key=self._order_by, reverse=self._order_reverse)
        else:
            return typed_search

    def fetch(self) -> FileList:
        wheres = {}

        if self._scopes:
            self.logger.warning("BL::Manager::Files::fetch::ScopesIgnored::Content search API does not support scopes.")

        mapped_filters = list(
            map(
                lambda x: {
                    x[0]: {
                        (self._mapped_operators[x[1]] if x[1] in self._mapped_operators else x[1]): x[2],
                    }
                },
                self._filters,
            )
        )

        if mapped_filters:
            if self._filters_operator == Op.OR:
                wheres["OR"] = mapped_filters
            elif self._filters_operator == Op.AND:
                wheres["AND"] = mapped_filters
            else:
                raise ChatFileManagerError(f"BL::Manager::ChatFile::fetch::InvalidOperator::{self._filters_operator}")

        if self._chat_only:
            wheres = {
                "ownerId": {
                    "equals": self._event.payload.chat_id,
                },
            }

            if self._filters:
                self.logger.warning("BL::Manager::ChatFile::fetch::ChatOnly::FiltersIgnored")

        found = unique_sdk.Content.search(
            user_id=self._event.user_id,
            company_id=self._event.company_id,
            chatId=self._event.payload.chat_id,
            where=wheres or None,  # type: ignore
        )

        self._filters_operator = Op.OR
        self._filters = []

        typed_content = self._cast_content(found)

        if self._order_by:
            return typed_content.sort(key=self._order_by, reverse=self._order_reverse)
        else:
            return typed_content

    def filter(self, op: Op = Op.OR, **kwargs) -> "FileManager":
        file_manager = self.fork()

        file_manager._filters_operator = op

        for full_key, value in kwargs.items():
            if "__" in full_key:
                key, operation = full_key.split("__")
            else:
                key, operation = full_key, "eq"

            file_manager._filters.append([key, operation, value])

        return file_manager

    def order_by(self, key: str | Callable[[File], Any], reverse: bool = False) -> "FileManager":
        file_manager = self.fork()

        if file_manager._order_by:
            self.logger.warning("BL::Manager::ChatFile::order_by::Overwritten")

        if file_manager._order_reverse:
            self.logger.warning("BL::Manager::ChatFile::order_by::ReverseOverwritten")

        file_manager._order_by = key
        file_manager._order_reverse = reverse

        return file_manager

    def sort(self, key: str | Callable[[File], Any], reverse: bool = False) -> "FileManager":
        return self.order_by(key, reverse)

    # Executive methods should not fork the manager
    def all(self) -> FileList:
        if not self._retrieved:
            self._all = self.fetch()
            self._retrieved = True

        if self._order_by:
            self._all.sort(key=self._order_by, reverse=self._order_reverse)

        return self._all

    def first(self, lookup: Callable[[File], bool] | None = None) -> File | None:
        return self.all().first(lookup)

    def last(self, lookup: Callable[[File], bool] | None = None) -> File | None:
        return self.all().last(lookup)

    def get_by_id(self, file_id: str) -> File | None:
        try:
            return next(filter(lambda x: x.id == file_id, self.all()))  # type: ignore
        except StopIteration:
            return None

    def get_by_name(self, name: str) -> File | None:
        try:
            return next(filter(lambda x: x.name == name, self.all()))  # type: ignore
        except StopIteration:
            return None

    def count(self, where: Callable[[File], bool] | None = None) -> int:
        files = self.all()

        if where:
            return len(list(filter(where, files)))
        else:
            return len(files)

    def __len__(self) -> int:
        return self.count()

    def values(self, *args, **kwargs) -> List:
        mapped = []

        flat = kwargs.get("flat", False)

        for f in self.all():
            mapped.append({arg: getattr(f, arg) for arg in args})

        if flat and len(args) == 1:
            return [item[args[0]] for item in mapped]
        elif flat and len(args) == 0:
            return [item for item in mapped]
        elif flat and len(args) > 1:
            raise ChatFileManagerError("BL::Manager::ChatFile::values::InvalidArgs::flat=True requires at most one argument.")
        else:
            return mapped

    def create(self, name: str, mime: str = "text/plain", scope: str | None = None) -> File:
        existing = unique_sdk.Content.upsert(
            user_id=self._event.user_id,
            company_id=self._event.company_id,
            input={
                "key": name,
                "title": name,
                "mimeType": mime,
            },
            scopeId=self._scopes[0] if self._scopes else scope,
        )  # type: ignore

        unique_sdk.Content.upsert(
            user_id=self._event.user_id,
            company_id=self._event.company_id,
            input={
                "key": name,
                "title": name,
                "mimeType": mime,
                "byteSize": 0,
            },
            scopeId=self._scopes[0] if self._scopes else scope,
            fileUrl=existing.writeUrl,
        )  # type: ignore

        return File(
            event=self._event,
            id=existing["id"],
            name=name,
            mime_type=mime,
            chunks=ChunkList(logger=self.logger.getChild(ChunkList.__name__)),
            tokenizer=self.tokenizer,
            write_url=existing.writeUrl,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            logger=self.logger.getChild(File.__name__),
        )

    def as_messages(self, role: Role = Role.SYSTEM) -> MessageList:
        return self.all().as_messages(role, self.tokenizer)

    def as_context(self) -> List[unique_sdk.Integrated.SearchResult]:
        return self.all().as_context()
