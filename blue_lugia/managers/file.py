import datetime
from typing import Any, Callable

import tiktoken
import unique_sdk
from typing_extensions import deprecated

from blue_lugia.enums import Op, SearchType
from blue_lugia.errors import ChatFileManagerError
from blue_lugia.managers.manager import Manager
from blue_lugia.models import (
    Chunk,
    ChunkList,
    File,
    FileList,
    Q,
)


class FileManager(Manager):
    _all: FileList
    _retrieved: bool

    _chat_only: bool
    _search_type: SearchType
    _scopes: list[str]
    _ids: list[str]

    _filters: list[Any]
    _filters_operator: Op

    _query: Q | None = None

    _order_by: str | Callable | None = None
    _order_reverse: bool = False

    _mapped_operators = {
        "eq": "equals",
        "ne": "notEquals",
        "gt": "greaterThan",
        "gte": "greaterThanOrEqual",
        "lt": "lessThan",
        "lte": "lessThanOrEqual",
        "in": "in",
        "nin": "notIn",
        "contains": "contains",
        "icontains": "contains",
        "ncontains": "notContains",
        "nicontains": "notContains",
        "isnull": "isNull",
        "isnotnull": "isNotNull",
        "isempty": "isEmpty",
        "isnotempty": "isNotEmpty",
        "startswith": "startsWith",
        "endswith": "endsWith",
        "foreach": "foreach",
        "nested": "nested",
    }

    _negated_operators = {
        "equals": "notEquals",
        "notEquals": "equals",
        "greaterThan": "lowerThanOrEqual",
        "greaterThanOrEqual": "lowerThan",
        "lessThan": "greaterThanOrEqual",
        "lessThanOrEqual": "greaterThan",
        "in": "notIn",
        "notIn": "in",
        "contains": "notContains",
        "icontains": "notContains",
        "notContains": "contains",
        "isNull": "isNotNull",
        "isNotNull": "isNull",
        "isEmpty": "isNotEmpty",
        "isNotEmpty": "isEmpty",
        "startsWith": "startsWith",
        "endsWith": "endsWith",
        "nested": "nested",
    }

    _tokenizer: str | tiktoken.Encoding

    def __init__(
        self,
        tokenizer: str | tiktoken.Encoding,
        chat_only: bool = False,
        search_type: SearchType = SearchType.COMBINED,
        scopes: list[str] = [],
        ids: list[str] = [],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._retrieved = False
        self._chat_only = chat_only
        self._search_type = search_type
        self._scopes = scopes if scopes else []
        self._ids = ids if ids else []
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
        file_manager = self.__class__(
            chat_only=self._chat_only,
            search_type=self._search_type,
            scopes=self._scopes,
            ids=self._ids,
            event=self._event,
            logger=self.logger,
            tokenizer=self.tokenizer,
        )

        file_manager._filters = self._filters.copy()
        file_manager._filters_operator = self._filters_operator
        file_manager._query = self._query
        file_manager._order_by = self._order_by
        file_manager._order_reverse = self._order_reverse
        file_manager._all = FileList(self._all, tokenizer=self.tokenizer, logger=self.logger.getChild(FileList.__name__))
        file_manager._retrieved = self._retrieved

        return file_manager

    def _cast_search(self, chunks: list[unique_sdk.Search]) -> ChunkList:
        files_map: dict[str, File] = {}
        all_chunks = []

        for chunk in chunks:
            file_id = chunk["id"]

            if file_id not in files_map:
                files_map[file_id] = File(
                    event=self._event,
                    id=file_id,
                    name=chunk["title"] if "title" in chunk and chunk["title"] else chunk["key"],
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
                metadata=chunk.get("metadata", {}),
                url=chunk.get("url"),
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
                    name=found_file["title"] if "title" in found_file and found_file["title"] else found_file["key"],
                    mime_type=(found_file.get("metadata", {}) or {}).get("mimeType", "text/plain"),
                    chunks=ChunkList(logger=self.logger.getChild(ChunkList.__name__)),
                    tokenizer=self.tokenizer,
                    write_url=write_url,
                    created_at=datetime.datetime.fromisoformat(found_file["createdAt"]),
                    updated_at=datetime.datetime.fromisoformat(found_file["updatedAt"]),
                    logger=self.logger.getChild(File.__name__),
                )

            for chunk in chunks:
                Chunk(
                    id=chunk["id"],
                    order=chunk["order"],
                    content=chunk["text"],
                    start_page=chunk["startPage"],
                    end_page=chunk["endPage"],
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now(),
                    metadata=chunk.get("metadata", {}),
                    url=chunk.get("url"),
                    tokenizer=self.tokenizer,
                    logger=self.logger.getChild(Chunk.__name__),
                    file=files_map[file_id],
                )

        return FileList(
            files_map.values(),
            tokenizer=self.tokenizer,
            logger=self.logger.getChild(FileList.__name__),
        )

    def _kwargs_to_kov(self, full_key: str, value: Any) -> tuple[str | list, str, Any]:
        if "__" in full_key:
            splited = full_key.split("__")

            if len(splited) == 2:
                key, operation = splited[0], splited[1]

            elif len(splited) == 3:
                key, operation, potential_in = splited[0], splited[1], splited[2]

                if potential_in == "in":
                    operations = []

                    if isinstance(value, list):
                        for v in value:
                            operations.append([key, operation, v])
                    else:
                        raise ChatFileManagerError(f"BL::Manager::ChatFile::filter::InvalidValue::{value}")

                    key, operation = operations, "sub_filter"
                else:
                    raise ChatFileManagerError(f"BL::Manager::ChatFile::filter::InvalidKey::{full_key}")
            else:
                raise ChatFileManagerError(f"BL::Manager::ChatFile::filter::InvalidKey::{full_key}")
        else:
            key, operation = full_key, "eq"

        return key, operation, value

    def _op_args_kwargs_to_q(self, op: Op | Q, *args: Q, **kwargs) -> Q:
        query = Q()

        if isinstance(op, Op):
            query = Q(*args, **kwargs)
            if op == Op.NOT:
                query._negated = True
            else:
                query._connector = op
        else:
            query = Q(op, *args, **kwargs)

        return query

    def _process_metadata_condition(self, condition: tuple[str, str, Any] | Q, negated: bool = False) -> dict[str, Any] | None:
        if isinstance(condition, Q):
            return self._q_to_metadata(condition)
        else:
            # Process a single condition tuple (key, operation, value).
            key, operation, value = condition

            # Handle older API versions that used "in" as a suffix for list operations.
            if operation == "in" and isinstance(value, list):
                splited = key.split("__")
                previous_operation = splited[-1]

                if previous_operation in self._mapped_operators.values():
                    return self._q_to_metadata(Q(*[Q(**{key: v}) for v in value]))

            if operation == "nested" or operation == "foreach":
                key += "__*"
                operation = "nested"

                if isinstance(value, dict):
                    value = Q(**value)

            # Handle Django-like transition using double underscores to indicate JSON paths
            path = key.split("__")

            operation = self._mapped_operators.get(operation, operation)

            if negated:
                operation = self._negated_operators.get(operation, operation)

            if isinstance(value, (list, set, tuple)):
                value = list(value)  # Ensure the value is JSON serializable if it's a collection.

            if isinstance(value, Q):
                # Handle nested Q objects as sub-filters.
                value = self._q_to_metadata(value)

            return {"path": path, "operator": operation, "value": value}

    def _q_to_metadata(self, q: Q) -> dict[str, Any] | None:
        """
        Converts a Q object to a metadata dictionary suitable for API queries.
        This method processes conditions, handling nested queries, logical connectors, negation, and path translations.

        Args:
            q (Q): The Q object to convert.

        Returns:
            dict[str, Any] | None: A dictionary representing the metadata filter, or None if the Q object is empty.
        """
        if not q.conditions:
            return None  # Return None if there are no conditions to process.

        # Handle the logical connectors at the top-level query.
        if q.connector == Op.AND or q.connector == Op.OR:
            inner_result = [self._process_metadata_condition(c, q.negated) for c in q.conditions]
            result = {q.connector.value.lower(): inner_result} if len(inner_result) > 1 else inner_result[0]
        else:
            result = None

        return result

    def _process_content_condition(self, condition: tuple[str, str, Any] | Q) -> dict[str, Any]:
        if isinstance(condition, Q):
            # Recursive call to process nested Q objects
            return self._q_to_content_filters(condition) if len(condition.conditions) > 1 or condition.negated else self._process_content_condition(condition.conditions[0])
        else:
            # Process a single condition tuple (key, operation, value)
            key, operation, value = condition

            if isinstance(value, (list, set, tuple)):
                value = list(value)  # Ensure the value is JSON serializable if it's a collection.

            if isinstance(value, Q):
                # Handle nested Q objects as sub-filters.
                value = self._q_to_content_filters(value)

            if operation.startswith("i") and operation[1:] in self._mapped_operators:
                operator = self._mapped_operators.get(operation[1:], operation)
                where = {key: {operator: value, "mode": "insensitive"}}
            else:
                operator = self._mapped_operators.get(operation, operation)
                where = {key: {operator: value}}

            return where

    def _q_to_content_filters(self, q: Q) -> dict[str, Any]:
        """
        Converts a Q object to a dictionary format suitable for content filtering.
        This method handles nested conditions, logical connectors, and specific comparison operations like startsWith, endsWith, and contains.

        Args:
            q (Q): The Q object to convert.

        Returns:
            dict[str, Any]: A dictionary representing the content filter structure.
        """

        if not q.conditions:
            return {}

        inner_result = [self._process_content_condition(c) for c in q.conditions]
        conditions = {q.connector.value.upper(): inner_result}
        return {"NOT": conditions} if q.negated else conditions

    @deprecated("BL::API::Version::UseInstead::FileManager::_q_to_metadata")
    def _filters_to_metadata(self) -> dict[str, Any] | None:
        metadata_filters = None

        if len(self._filters) == 1:
            last_filter = self._filters[0]
            metadata_filters = {
                "path": [last_filter[0]],
                "operator": (self._mapped_operators[last_filter[1]] if last_filter[1] in self._mapped_operators else last_filter[1]),
                "value": last_filter[2],
            }
        elif len(self._filters) > 1:
            metadata_filters = {
                self._filters_operator.value.lower(): [
                    {
                        "path": [x[0]],
                        "operator": (self._mapped_operators[x[1]] if x[1] in self._mapped_operators else x[1]),
                        "value": x[2],
                    }
                    for x in self._filters
                ]
            }

        return metadata_filters

    @deprecated("BL::API::Version::UseInstead::FileManager::_q_to_content_filters")
    def _filters_to_content_filters(self) -> dict[str, Any]:
        wheres = {}

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

        return wheres

    def using(self, search_type: SearchType) -> "FileManager":
        file_manager = self.fork()
        file_manager._search_type = search_type
        return file_manager

    def scoped(self, scopes: list[str] | str) -> "FileManager":
        file_manager = self.fork()

        if isinstance(scopes, str):
            scopes = [scopes]

        if file_manager._scopes:
            self.logger.warning("BL::Manager::Files::scoped::ScopesOverwritten")

        file_manager._scopes = scopes

        return file_manager

    def contents(self, ids: list[str] | str) -> "FileManager":
        file_manager = self.fork()

        if isinstance(ids, str):
            ids = [ids]

        if file_manager._ids:
            self.logger.warning("BL::Manager::Files::ids::ContentIDsOverwritten")

        file_manager._ids = ids

        return file_manager

    def search(self, query: str = "", limit: int = 100, **kwargs) -> ChunkList:
        metadata_filters = self._q_to_metadata(self._query) if self._query else None

        extra_args = {}

        if self._chat_only:
            extra_args["chatOnly"] = True

        if self._scopes:
            extra_args["scopeIds"] = self._scopes

        if self._ids:
            extra_args["contentIds"] = self._ids

        if metadata_filters:
            extra_args["metaDataFilter"] = metadata_filters

        if self._event.payload.chat_id:
            extra_args["chatId"] = self._event.payload.chat_id

        if limit <= 1000:
            extra_args["limit"] = limit
        else:
            raise ChatFileManagerError(f"BL::Manager::ChatFile::search::LimitTooLarge::{limit}")

        extra_args = {**extra_args, **kwargs}

        found = unique_sdk.Search.create(
            user_id=self._event.user_id,
            company_id=self._event.company_id,
            searchString=query,
            searchType=self._search_type.value,
            **extra_args,
        )

        typed_search = self._cast_search(found)

        if self._order_by:
            return typed_search.sort(key=self._order_by, reverse=self._order_reverse)
        else:
            return typed_search

    def fetch(self) -> FileList:
        query = self._query or Q()

        if self._chat_only:
            query &= Q(ownerId=self._event.payload.chat_id)

        if self._scopes:
            query &= Q(ownerId__in=self._scopes)

        if self._ids:
            query &= Q(id__in=self._ids)

        wheres = self._q_to_content_filters(query)

        if self._chat_only and self._scopes:
            self.logger.warning("BL::Manager::Files::fetch::EmptyQuery::Using uploaded and scoped filters together will result in empty results")

        extra_args = {}

        if self._event.payload.chat_id:
            extra_args["chatId"] = self._event.payload.chat_id

        found = unique_sdk.Content.search(
            user_id=self._event.user_id,
            company_id=self._event.company_id,
            where=wheres or None,  # type: ignore
            **extra_args,
        )

        typed_content = self._cast_content(found)

        if self._order_by:
            return typed_content.sort(key=self._order_by, reverse=self._order_reverse)
        else:
            return typed_content

    def filter(self, op: Op | Q = Op.OR, *args, **kwargs) -> "FileManager":
        file_manager = self.fork()

        file_manager._filters_operator = op if isinstance(op, Op) else Op.OR

        file_manager._query = self._op_args_kwargs_to_q(op, *args, **kwargs)

        for full_key, value in kwargs.items():
            key, operation, value = self._kwargs_to_kov(full_key, value)

            if operation == "sub_filter":
                for sub_filter in key:
                    file_manager._filters.append(sub_filter)
            else:
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

    @deprecated("BL::API::Version::UseInstead::FileManager::contents")
    def get_by_id(self, file_id: str) -> File | None:
        try:
            return next(filter(lambda x: x.id == file_id, self.all()))  # type: ignore
        except StopIteration:
            return None

    @deprecated("BL::API::Version::UseInstead::FileManager::filter")
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

    def values(self, *args, **kwargs) -> list:
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

    def create(self, name: str, content: str | bytes | None, mime_type: str = "text/plain", scope: str | None = None, ingest: bool = True, **kwargs) -> File:
        file = File.create(event=self.event, name=name, content=content or "", mime_type=mime_type, **kwargs)

        if content:
            file.write(content=content, scope=scope, ingest=ingest)

        return file

    def as_context(self) -> list[unique_sdk.Integrated.SearchResult]:
        return self.all().as_context()
