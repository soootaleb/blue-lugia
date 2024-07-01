import datetime
import logging
import re
from typing import Any, Callable, Iterable, List

import requests
import tiktoken
import unique_sdk

from blue_lugia.enums import Role
from blue_lugia.models import ExternalModuleChosenEvent
from blue_lugia.models.message import Message, MessageList
from blue_lugia.models.model import Model


class Chunk(Model):
    id: str
    order: int
    content: str
    start_page: int
    end_page: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    _file: "File"
    _tokenizer: tiktoken.Encoding | None

    def __init__(
        self,
        id: str,
        order: int,
        content: str,
        start_page: int,
        end_page: int,
        created_at: datetime.datetime,
        updated_at: datetime.datetime,
        tokenizer: tiktoken.Encoding | None,
        file: "File",
        **kwargs: logging.Logger,
    ) -> None:
        super().__init__(**kwargs)
        self.id = id
        self.order = order
        self.content = self._clean_content(content)
        self.start_page = start_page
        self.end_page = end_page
        self.created_at = created_at
        self.updated_at = updated_at
        self._tokenizer = tokenizer
        self._file = file

        self._file.chunks.append(self)

    @property
    def tokens(self) -> list[int]:
        if not self._tokenizer:
            raise ValueError("No tokenizer set for the chunk")
        return self._tokenizer.encode(self.content)

    @property
    def file(self) -> "File":
        return self._file

    @property
    def xml(self) -> str:
        return f"""<source
                    id='{self.id}'
                    order='{self.order}'
                    start_page='{self.start_page}'
                    end_page='{self.end_page}'>
                    {self.content}
                </source>"""

    def _clean_content(self, _content: str) -> str:
        _content = re.sub(r"<\|document\|>.*?<\|\/document\|>", "", _content, flags=re.DOTALL)

        _content = re.sub(r"<\|info\|>.*?<\|\/info\|>", "", _content, flags=re.DOTALL)

        return _content

    def using(self, model: str | tiktoken.Encoding | None) -> "Chunk":
        if isinstance(model, str):
            self._tokenizer = tiktoken.encoding_for_model(model)
        elif model is not None:
            self._tokenizer = model
        else:
            self.logger.warning("No tokenizer set for the chunk")

        return self

    def truncate(self, tokens_limit: int) -> "Chunk":
        if not self._tokenizer:
            raise ValueError("No tokenizer set for the chunk")

        tokens_limit = max(tokens_limit, 0)
        self.content = self._tokenizer.decode(self.tokens[:tokens_limit])

        if not self.content:
            self.file.chunks.remove(self)

        return self

    def __len__(self) -> int:
        return len(self.content)

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return self.id


class ChunkList(List[Chunk], Model):
    def __init__(self, iterable: Iterable[Chunk] = [], **kwargs: Any) -> None:
        list.__init__(self, iterable)
        Model.__init__(self, **kwargs)

    @property
    def tokens(self) -> list[int]:
        all_tokens = []
        for chunk in self:
            all_tokens += chunk.tokens
        return all_tokens

    @property
    def xml(self) -> str:
        xml = "<sources>"

        for i, chunk in enumerate(self):
            xml += f"""<source{i}
                            id='{chunk.id}'
                            order='{chunk.order}'
                            start_page='{chunk.start_page}'
                            end_page='{chunk.end_page}'>
                            {chunk.xml}
                        </source{i}>"""

        return xml + "</sources>"

    def first(self, lookup: Callable[[Chunk], bool] | None = None) -> Chunk | None:
        if lookup:
            return next(filter(lookup, self), None)
        else:
            return self[0] if self else None

    def last(self, lookup: Callable[[Chunk], bool] | None = None) -> Chunk | None:
        if lookup:
            return next(filter(lookup, reversed(self)), None)
        else:
            return self[-1] if self else None

    def sort(self, key: str | Callable[[Chunk], Any], reverse: bool = False, in_place: bool = False) -> "ChunkList":
        if isinstance(key, str):
            sort_key: Callable[[Chunk], Any] = lambda x: getattr(x, key)  # noqa: E731
        else:
            sort_key = key

        if in_place:
            super().sort(key=sort_key, reverse=reverse)
            return self
        else:
            return ChunkList(
                sorted(self, key=sort_key, reverse=reverse),
                logger=self.logger.getChild(ChunkList.__name__),
            )

    def filter(self, f: Callable[[Chunk], bool], in_place: bool = False) -> "ChunkList":
        if in_place:
            self[:] = [chunk for chunk in self if f(chunk)]
            return self
        else:
            return ChunkList([chunk for chunk in self if f(chunk)], logger=self.logger)

    def truncate(self, tokens_limit: int, in_place: bool = False, files_map: dict[str, "File"] | None = None) -> "ChunkList":
        remaining_tokens = tokens_limit

        if files_map is None:
            files_map = {}

        if in_place:
            for chunk in self:
                chunk.truncate(remaining_tokens)
                remaining_tokens -= len(chunk.tokens)
                if not chunk.content:
                    self.remove(chunk)
            return self
        else:
            chunks = ChunkList(logger=self.logger.getChild(ChunkList.__name__))

            for chunk in self:
                if remaining_tokens > 0:
                    if chunk.file.id not in files_map:
                        files_map[chunk.file.id] = File(
                            event=chunk.file._event,
                            id=chunk.file.id,
                            name=chunk.file.name,
                            chunks=ChunkList(logger=chunk.file.chunks.logger),
                            mime_type=chunk.file.mime_type,
                            tokenizer=chunk.file._tokenizer,
                            read_url=chunk.file.read_url,
                            write_url=chunk.file.write_url,
                            created_at=chunk.file.created_at,
                            updated_at=chunk.file.updated_at,
                            logger=chunk.file.logger,
                        )

                    chunks.append(
                        Chunk(
                            id=chunk.id,
                            order=chunk.order,
                            content=chunk.content,
                            start_page=chunk.start_page,
                            end_page=chunk.end_page,
                            created_at=chunk.created_at,
                            updated_at=chunk.updated_at,
                            tokenizer=chunk._tokenizer,
                            file=files_map[chunk.file.id],
                            logger=chunk.logger,
                        ).truncate(remaining_tokens)  # remaining tokens > 0
                    )

                    remaining_tokens -= len(chunk.tokens)

                else:
                    break

            return chunks

    def as_files(self) -> "FileList":
        files = FileList(logger=self.logger.getChild(FileList.__name__))

        for chunk in self:
            if chunk.file not in files:
                files.append(chunk.file)

        return files

    def as_context(self) -> List[unique_sdk.Integrated.SearchResult]:
        results = []

        for chunk in self:
            key = f"{chunk.file.key} : {','.join([str(page) for page in range(chunk.start_page, chunk.end_page + 1)])}"

            results.append(
                unique_sdk.Integrated.SearchResult(
                    id=chunk.file.id,
                    chunkId=chunk.id,
                    key=key,
                    title=chunk.file.name,
                    url=chunk.file.read_url or f"unique://content/{chunk.file.id}",
                )
            )

        return results


class File(Model):
    id: str
    key: str
    name: str
    chunks: ChunkList
    mime_type: str
    read_url: str
    write_url: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    _event: ExternalModuleChosenEvent
    _tokenizer: tiktoken.Encoding | None

    def __init__(
        self,
        event: ExternalModuleChosenEvent,
        id: str,
        name: str,
        mime_type: str,
        chunks: ChunkList | None = None,
        tokenizer: tiktoken.Encoding | None = None,
        read_url: str = "",
        write_url: str = "",
        created_at: datetime.datetime = datetime.datetime.now(),
        updated_at: datetime.datetime = datetime.datetime.now(),
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._event = event
        self.id = id
        self.key = name
        self.name = name
        self.mime_type = mime_type
        self.chunks = chunks or ChunkList(logger=self.logger.getChild(ChunkList.__name__))
        self.read_url = read_url
        self.write_url = write_url
        self.created_at = created_at
        self.updated_at = updated_at
        self._tokenizer = tokenizer

    @property
    def content(self) -> str:
        return "".join([chunk.content for chunk in self.chunks])

    @property
    def xml(self) -> str:
        xml = f"<document name='{self.name}' id='{self.id}'>"
        xml += self.chunks.xml
        xml += "</document>"
        return xml

    @property
    def tokens(self) -> list[int]:
        if not self._tokenizer:
            raise ValueError("No tokenizer set for the file")
        return self._tokenizer.encode(self.content)

    def __lt__(self, other: "File") -> bool:
        return self.created_at < other.created_at

    def __eq__(self, other: "File") -> bool:
        return self.id == other.id

    def using(self, model: str | tiktoken.Encoding) -> "File":
        if isinstance(model, str):
            self._tokenizer = tiktoken.encoding_for_model(model)
        else:
            self._tokenizer = model
        return self

    def truncate(self, tokens_limit: int, in_place: bool = False) -> "File":
        if in_place:
            self.chunks.truncate(tokens_limit, in_place=True)
            return self
        else:
            file = File(
                event=self._event,
                id=self.id,
                name=self.name,
                mime_type=self.mime_type,
                chunks=ChunkList(logger=self.chunks.logger),
                tokenizer=self._tokenizer,
                read_url=self.read_url,
                write_url=self.write_url,
                created_at=self.created_at,
                updated_at=self.updated_at,
                logger=self.logger,
            )

            self.chunks.truncate(tokens_limit, files_map={file.id: file})

            return file

    def write(self, content: str, scope: str) -> "File":
        existing = unique_sdk.Content.upsert(
            user_id=self._event.user_id,
            company_id=self._event.company_id,
            input={
                "key": self.name,
                "title": self.name,
                "mimeType": self.mime_type,
            },
            scopeId=scope,
        )  # type: ignore

        self.read_url = existing.readUrl
        self.write_url = existing.writeUrl

        requests.put(
            self.write_url,
            data=content,
            headers={
                "X-Ms-Blob-Content-Type": self.mime_type,
                "X-Ms-Blob-Type": "BlockBlob",
            },
        )

        unique_sdk.Content.upsert(
            user_id=self._event.user_id,
            company_id=self._event.company_id,
            input={
                "key": self.name,
                "title": self.name,
                "mimeType": self.mime_type,
                "byteSize": len(content),
            },
            scopeId=scope,
            readUrl=self.write_url,  # type: ignore
        )  # type: ignore

        self.chunks = ChunkList(
            [
                Chunk(
                    id=f"{self.id}_1",
                    order=0,
                    content=content,
                    start_page=0,
                    end_page=0,
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now(),
                    tokenizer=self._tokenizer,
                    logger=self.logger.getChild(Chunk.__name__),
                    file=self,
                )
            ],
            logger=self.logger.getChild(ChunkList.__name__),
        )

        return self

    def as_message(self, role: Role = Role.SYSTEM) -> Message:
        return Message(
            role=role,
            content=self.content,
            logger=self.logger.getChild(Message.__name__),
        )

    def as_context(self) -> List[unique_sdk.Integrated.SearchResult]:
        return self.chunks.as_context()

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name


class FileList(List[File], Model):
    _tokenizer: str | tiktoken.Encoding | None

    def __init__(
        self,
        iterable: Iterable[File] = [],
        tokenizer: str | tiktoken.Encoding | None = None,
        **kwargs,
    ) -> None:
        list.__init__(self, iterable)
        Model.__init__(self, **kwargs)
        self._tokenizer = tokenizer

    @property
    def tokenizer(self) -> tiktoken.Encoding:
        if not self._tokenizer:
            raise ValueError("No tokenizer set for the file list")

        if isinstance(self._tokenizer, str):
            return tiktoken.encoding_for_model(self._tokenizer)
        else:
            return self._tokenizer

    @property
    def tokens(self) -> list[int]:
        all_tokens = []
        for file in self:
            all_tokens += file.tokens
        return all_tokens

    @property
    def xml(self) -> str:
        xml = "<documents>"
        for i, file in enumerate(self):
            xml += f"""<document{i}
                            name='{file.name}'
                            id='{file.id}'>
                            {file.xml}
                        </document{i}>"""
        return xml + "</documents>"

    def using(self, tokenizer: str | tiktoken.Encoding) -> "FileList":
        self._tokenizer = tokenizer
        return self

    def order_by(self, key: str | Callable[[File], Any] | None = None, reverse: bool = False, in_place: bool = False) -> "FileList":
        return self.sort(key=key, reverse=reverse, in_place=in_place)

    def sort(self, key: str | Callable[[File], Any] | None, reverse: bool = False, in_place: bool = False) -> "FileList":
        if isinstance(key, str):
            sort_key: Callable[[File], Any] = lambda x: getattr(x, key)  # noqa: E731
        elif key is None:
            sort_key = lambda x: x  # noqa: E731
        else:
            sort_key = key

        if in_place:
            super().sort(key=sort_key, reverse=reverse)
            return self
        else:
            return FileList(
                sorted(self, key=sort_key, reverse=reverse),
                tokenizer=self._tokenizer,
                logger=self.logger.getChild(FileList.__name__),
            )

    def first(self, lookup: Callable[[File], bool] | None = None) -> File | None:
        if lookup:
            return next(filter(lookup, self), None)
        else:
            return self[0] if self else None

    def last(self, lookup: Callable[[File], bool] | None = None) -> File | None:
        if lookup:
            return next(filter(lookup, reversed(self)), None)
        else:
            return self[-1] if self else None

    def append(self, object: File) -> "FileList":
        super().append(object)
        return self

    def extend(self, iterable: Iterable[File]) -> "FileList":
        super().extend(iterable)
        return self

    def as_messages(self, role: Role = Role.SYSTEM, tokenizer: str | tiktoken.Encoding | None = None) -> MessageList:
        return MessageList(
            [file.as_message(role) for file in self],
            tokenizer=tokenizer or self._tokenizer,
            logger=self.logger.getChild(MessageList.__name__),
        )

    def truncate(self, tokens_limit: int, in_place: bool = False) -> "FileList":
        file_token_limit = tokens_limit // len(self)

        if in_place:
            for file in self:
                file.truncate(file_token_limit, in_place=True)
            return self
        else:
            return FileList([file.truncate(file_token_limit) for file in self], logger=self.logger.getChild(FileList.__name__))

    def as_context(self) -> List[unique_sdk.Integrated.SearchResult]:
        results = []

        for file in self:
            results.extend(file.as_context())

        return results
