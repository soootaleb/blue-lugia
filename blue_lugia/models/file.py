import datetime
import logging
import random
import re
import string
from io import BytesIO
from typing import Any, Callable, Iterable, List, Optional
from xml.sax.saxutils import escape

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
    metadata: dict[str, Any]
    url: Optional[str]

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
        metadata: dict[str, Any] | None = None,
        url: Optional[str] = None,
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
        self.metadata = metadata or {}
        self.url = url
        self._tokenizer = tokenizer
        self._file = file

        self._file.chunks.append(self)

    @property
    def tokens(self) -> list[int]:
        """The tokens of the chunk's content. Uses the tokenizer set for the chunk."""
        if not self._tokenizer:
            raise ValueError("No tokenizer set for the chunk")
        return self._tokenizer.encode(self.content)

    @property
    def file(self) -> "File":
        return self._file

    def xml(self, i: int = 0, extra_attrs: dict[str, Any] | Callable[["Chunk"], dict[str, Any]] | None = None) -> str:
        """
        An XML representation of the chunk.
        Mainly used for RAG, you can pass it as a system message's content.

        Structure is :

        <source
            id='{self.id}'
            order='{self.order}'
            start_page='{self.start_page}'
            end_page='{self.end_page}'
            label='{key}'
            url='{self.url or f"unique://content/{self.file.id}"}'
            {extra_attrs}>
            {self.content}
        </source>
        """

        if callable(extra_attrs):
            extra_attrs_str = " ".join([f'{k}="{v}"' for k, v in extra_attrs(self).items()])
        elif isinstance(extra_attrs, dict):
            extra_attrs_str = " ".join([f'{k}="{v}"' for k, v in extra_attrs.items()])
        else:
            extra_attrs_str = ""

        pages = []
        for page in range(self.start_page, self.end_page + 1):
            if self.start_page > -1:
                pages.append(str(page))

        key = self.file.key

        if pages:
            key += f" : {','.join(pages)}"

        return f"""<source{i}
                    id="{escape(self.id)}"
                    order="{self.order}"
                    start_page="{self.start_page}"
                    label="{escape(key)}"
                    url="{escape(self.url or f"unique://content/{self.file.id}")}"
                    end_page="{self.end_page}" {extra_attrs_str}>
                    {escape(self.content)}
                </source{i}>"""

    def _clean_content(self, _content: str) -> str:
        _content = re.sub(r"<\|document\|>.*?<\|\/document\|>", "", _content, flags=re.DOTALL)

        _content = re.sub(r"<\|info\|>.*?<\|\/info\|>", "", _content, flags=re.DOTALL)

        return _content

    def using(self, model: str | tiktoken.Encoding | None) -> "Chunk":
        """Define the tokenizer to use for the chunk."""

        if isinstance(model, str):
            self._tokenizer = tiktoken.encoding_for_model(model)
        elif model is not None:
            self._tokenizer = model
        else:
            self.logger.warning("No tokenizer set for the chunk")

        return self

    def truncate(self, tokens_limit: int) -> "Chunk":
        """Truncates the content of the chunks to the given number of tokens. Also affects the content of the file."""

        if not self._tokenizer:
            raise ValueError("No tokenizer set for the chunk")

        tokens_limit = max(tokens_limit, 0)
        self.content = self._tokenizer.decode(self.tokens[:tokens_limit])

        if not self.content:
            self.file.chunks.remove(self)

        return self

    def as_context(self) -> unique_sdk.Integrated.SearchResult:
        pages = []
        for page in range(self.start_page, self.end_page + 1):
            if self.start_page > -1:
                pages.append(str(page))

        key = self.file.key

        if pages:
            key += f" : {','.join(pages)}"

        # Setting a static title breaks sources indexes and the link because Unique groups by title
        return unique_sdk.Integrated.SearchResult(
            id=self.file.id,
            chunkId=self.id,
            key=key,
            url=self.url or f"unique://content/{self.file.id}",
        )

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
        """
        The tokens of all the chunks in the list.
        """

        all_tokens = []
        for chunk in self:
            all_tokens += chunk.tokens
        return all_tokens

    def xml(
        self,
        offset: int = 0,
        chunk_extra_attrs: dict[str, Any] | Callable[["Chunk"], dict[str, Any]] | None = None,
    ) -> str:
        """
        An XML representation of the chunk list.
        Mainly used for RAG, you can pass it as a system message's content.

        Structure is :

        <source{index} id='{chunk.id}' order='{chunk.order}' start_page='{chunk.start_page}' end_page='{chunk.end_page}' {extra_attrs}>
            {chunk.content}
        </source{index}>
        """

        xml = ""

        for index, chunk in enumerate(self):
            chunk = self[index]
            i = index + offset

            xml += chunk.xml(i=i, extra_attrs=chunk_extra_attrs)

        return xml

    def first(self, lookup: Callable[[Chunk], bool] | None = None) -> Chunk | None:
        """
        Returns the first chunk in the list that matches the lookup function.
        If no lookup function is provided, returns the first chunk in the list.
        """

        if lookup:
            return next(filter(lookup, self), None)
        else:
            return self[0] if self else None

    def last(self, lookup: Callable[[Chunk], bool] | None = None) -> Chunk | None:
        """
        Returns the last chunk in the list that matches the lookup function.
        If no lookup function is provided, returns the last chunk in the list.
        """

        if lookup:
            return next(filter(lookup, reversed(self)), None)
        else:
            return self[-1] if self else None

    def sort(self, key: str | Callable[[Chunk], Any], reverse: bool = False, in_place: bool = False) -> "ChunkList":
        """
        Returns a new sorted ChunkList.
        You can specify in_place, defaults to creating a new list.
        """

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
        """
        Returns a new filtered ChunkList.
        You can specify in_place, defaults to creating a new list.
        """

        if in_place:
            self[:] = [chunk for chunk in self if f(chunk)]
            return self
        else:
            return ChunkList([chunk for chunk in self if f(chunk)], logger=self.logger)

    def truncate(self, tokens_limit: int, in_place: bool = False, files_map: dict[str, "File"] | None = None) -> "ChunkList":
        """
        Truncates the content of a ChunkList to a specified limit of tokens.

        Args:
            tokens_limit (int): The maximum number of tokens to retain in the ChunkList.
            in_place (bool): If True, truncation is applied directly to this ChunkList, modifying it.
                            If False, a new truncated ChunkList is created and returned.
            files_map (dict[str, "File"] | None): A mapping from file identifiers to File objects,
                                                which may be provided to manage the references to
                                                unique files across truncated chunks. If None, an empty
                                                dictionary is initialized.

        Returns:
            ChunkList: The truncated ChunkList. If 'in_place' is True, this is the same modified ChunkList,
                    otherwise, it is a new ChunkList instance containing the truncated chunks.

        This method adjusts the content of chunks in the ChunkList based on the 'tokens_limit' by
        iterating through each chunk and reducing its size as necessary until the limit is reached.
        If 'in_place' is False, it constructs a new ChunkList and selectively copies and truncates
        chunks to this new list, respecting the token limit and using the 'files_map' to manage
        file references if provided.
        """

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
                            metadata=chunk.metadata,
                            url=chunk.url,
                            logger=chunk.logger,
                        ).truncate(remaining_tokens)  # remaining tokens > 0
                    )

                    remaining_tokens -= len(chunk.tokens)

                else:
                    break

            return chunks

    def as_files(self) -> "FileList":
        """
        Converts the collection of chunks into a FileList containing unique files.

        Returns:
            FileList: A list containing unique File objects referenced by the chunks in this collection.
                    Each file is added to the list only once, regardless of how many chunks refer to it.

        This method iterates over each chunk in the collection, checking if its associated file is already
        included in the resultant FileList. If not, the file is appended to the list. This ensures that each
        file is represented only once in the returned FileList, even if multiple chunks refer to the same file.
        """
        files = FileList(logger=self.logger.getChild(FileList.__name__))

        for chunk in self:
            if chunk.file not in files:
                files.append(chunk.file)

        return files

    def as_context(self) -> List[unique_sdk.Integrated.SearchResult]:
        """
        Converts the collection of chunks into a list of search results based on their content and metadata.
        The result is designed to be used as a search_context when using LLM.complete()
        Returns:
            List[unique_sdk.Integrated.SearchResult]: A list of SearchResult objects that represent each chunk.
                                                    Each result contains the chunk's file ID, chunk ID,
                                                    a key representing the file and page range, and a URL to access the chunk.
        This method constructs a SearchResult for each chunk by forming a key from the file key and the range
        of pages the chunk spans. This key is used along with other chunk information to populate the SearchResult.
        The method ensures that each chunk's context is uniquely represented and accessible through a formatted URL.
        """

        return [chunk.as_context() for chunk in self]


class File(Model):
    """
    A representation of a file in a digital system, managing content and metadata associated with
    a specific file entity.

    Attributes:
        id (str): The unique identifier for the file.
        key (str): A key associated with the file, typically used for indexing.
        name (str): The name of the file.
        chunks (ChunkList): A list of content chunks that compose the entire file.
        mime_type (str): The MIME type of the file.
        write_url (str): A URL for writing data directly to the file storage.
        created_at (datetime.datetime): The creation timestamp of the file.
        updated_at (datetime.datetime): The last updated timestamp of the file.

    Methods:
        __init__: Initializes a new instance of the File class with specified attributes.
        content: Returns the combined content of all chunks in the file as a string.
        data: Retrieves the file content from a specified URL and returns it as a BytesIO stream.
        xml: Generates an XML string representation of the file and its chunks.
        tokens: Encodes the file's content into tokens using a tokenizer.
        using: Assigns a tokenizer model to the file.
        truncate: Truncates the file's content to a specified token limit.
        write: Writes new content to the file and updates its chunks.
        as_message: Constructs a system message containing the file's content.
        as_context: Converts the file into search results based on its chunks.
        __str__: Returns the name of the file as its string representation.
        __repr__: Returns the name of the file as its official string representation.
    """

    id: str
    key: str
    name: str
    chunks: ChunkList
    mime_type: str
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
        self.write_url = write_url
        self.created_at = created_at
        self.updated_at = updated_at
        self._tokenizer = tokenizer

    @property
    def content(self) -> str:
        """
        Returns the combined content of all chunks in the file as a string.

        Returns:
            str: A single string consisting of concatenated contents of all chunks.
        """
        return "".join([chunk.content for chunk in self.chunks])

    @property
    def data(self) -> BytesIO:
        """
        Retrieves the file content from a specified URL and returns it as a BytesIO stream.

        Returns:
            BytesIO: A stream of file content obtained from a remote URL.
        """
        response = requests.get(
            f"{unique_sdk.api_base}/content/{self.id}/file?chatId={self._event.payload.chat_id}",
            headers={
                "x-api-version": unique_sdk.api_version,
                "x-user-id": self._event.user_id,
                "x-app-id": unique_sdk.app_id,
                "x-company-id": self._event.company_id,
                "Authorization": f"Bearer {unique_sdk.api_key}",
            },
        )

        return BytesIO(response.content)

    @property
    def tokens(self) -> list[int]:
        """
        Encodes the file's content into tokens using a tokenizer.

        Returns:
            list[int]: A list of token ids representing the file content.

        Raises:
            ValueError: If no tokenizer is set for the file.
        """
        if not self._tokenizer:
            raise ValueError("No tokenizer set for the file")
        return self._tokenizer.encode(self.content)

    def xml(
        self,
        chunks_offset: int = 0,
        chunk_extra_attrs: dict[str, Any] | Callable[["Chunk"], dict[str, Any]] | None = None,
    ) -> str:
        """
        Generates an XML string representation of the file and its chunks.

        Args:
            chunks_offset (int): The starting offset for chunk enumeration in the XML, default is 0.

        Returns:
            str: An XML representation of the file and its content chunks.
        """

        return self.chunks.xml(offset=chunks_offset, chunk_extra_attrs=chunk_extra_attrs)

    @classmethod
    def create(cls, event: ExternalModuleChosenEvent, name: str, content: str, **kwargs: Any) -> "File":
        random_string = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))

        file = cls(
            event=event,
            id=kwargs.get("id", f"cont_{random_string}"),
            name=name,
            mime_type=kwargs.get("mime_type", "text/plain"),
            chunks=ChunkList(logger=logging.getLogger(ChunkList.__name__)),
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        )

        Chunk(
            id=kwargs.get("id", f"chunk_{random_string}"),
            order=kwargs.get("order", 0),
            content=content,
            start_page=kwargs.get("start_page", -1),
            end_page=kwargs.get("end_page", -1),
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            file=file,
            metadata=kwargs.get("metadata", {}),
            url=kwargs.get("url", None),
            tokenizer=file._tokenizer,
        )

        return file

    def __lt__(self, other: "File") -> bool:
        """
        Less than comparison based on the creation date of the files.

        Args:
            other (File): Another file to compare against.

        Returns:
            bool: True if this file was created earlier than the other file, False otherwise.
        """
        return self.created_at < other.created_at

    def __eq__(self, other: "File") -> bool:
        """
        Equality comparison based on the file's unique identifier.

        Args:
            other (File): Another file to compare against.

        Returns:
            bool: True if both files have the same id, False otherwise.
        """
        return self.id == other.id

    def using(self, model: str | tiktoken.Encoding) -> "File":
        """
        Assigns a tokenizer model to the file.

        Args:
            model (str | tiktoken.Encoding): A string representing the model name or an instance of tiktoken.Encoding to be used for tokenization.

        Returns:
            File: The current instance of File, with the tokenizer set or updated.
        """
        if isinstance(model, str):
            self._tokenizer = tiktoken.encoding_for_model(model)
        else:
            self._tokenizer = model
        return self

    def truncate(self, tokens_limit: int, in_place: bool = False) -> "File":
        """
        Truncates the file's content to a specified token limit.

        Args:
            tokens_limit (int): The maximum number of tokens to retain.
            in_place (bool): If True, truncation is applied directly to this file's chunks, modifying it.
                             If False, a new truncated File instance is created and returned.

        Returns:
            File: The truncated file. If 'in_place' is True, this is the same modified File instance,
                  otherwise, it is a new File instance containing the truncated chunks.
        """
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
                write_url=self.write_url,
                created_at=self.created_at,
                updated_at=self.updated_at,
                logger=self.logger,
            )

            self.chunks.truncate(tokens_limit, files_map={file.id: file})

            return file

    def write(self, content: str, scope: str) -> "File":
        """
        Writes new content to the file and updates its chunks.

        Args:
            content (str): The new content to write to the file.
            scope (str): The scope identifier under which the content update is logged or managed.

        Returns:
            File: The current instance of File, with updated content and metadata.
        """
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
            fileUrl=self.write_url,
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
                    metadata={},
                    url=None,
                    tokenizer=self._tokenizer,
                    logger=self.logger.getChild(Chunk.__name__),
                    file=self,
                )
            ],
            logger=self.logger.getChild(ChunkList.__name__),
        )

        return self

    def as_message(self, role: Role = Role.SYSTEM) -> Message:
        """
        Constructs a system message containing the file's content.

        Args:
            role (Role): The role of the message within the system, typically indicates the message's origin or purpose.

        Returns:
            Message: A message object containing the content of the file.
        """
        return Message(
            role=role,
            content=self.content,
            logger=self.logger.getChild(Message.__name__),
        )

    def as_context(self) -> List[unique_sdk.Integrated.SearchResult]:
        """
        Converts the file into search results based on its chunks.
        Designed to be passed as a search_context in LLM.complete()
        Returns:
            List[unique_sdk.Integrated.SearchResult]: A list of search results, each representing a chunk of the file.
        """
        return self.chunks.as_context()

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name


class FileList(List[File], Model):
    """
    A list structure that holds a collection of File objects, extending both Python's list and a custom Model base class.

    Attributes:
        _tokenizer (str | tiktoken.Encoding | None): The tokenizer to use for encoding the content of files in the list.

    Methods:
        __init__: Initializes a new instance of the FileList class with an optional list of File objects and a tokenizer.
        tokenizer: Retrieves the current tokenizer set for the file list.
        tokens: Aggregates and returns a list of all tokens from the files in the list.
        xml: Generates an XML representation of the files in the list.
        using: Assigns a tokenizer to the file list.
        order_by: Sorts the files in the list based on a specified key or function, optionally in place.
        sort: Sorts the files in the list based on a specified key or function, optionally in place.
        first: Returns the first file in the list that matches a specified lookup function, or the first file if no function is provided.
        last: Returns the last file in the list that matches a specified lookup function, or the last file if no function is provided.
        append: Appends a File object to the list.
        extend: Extends the list by appending elements from another iterable of File objects.
        as_messages: Converts the list of files into a list of messages.
        as_context: Converts the list of files into a list of search results based on their content and metadata.
        truncate: Truncates the content of all files in the list to a specified token limit, optionally in place.
    """

    _tokenizer: str | tiktoken.Encoding | None

    def __init__(
        self,
        iterable: Iterable[File] = [],
        tokenizer: str | tiktoken.Encoding | None = None,
        **kwargs,
    ) -> None:
        """
        Initializes a new instance of the FileList class with an optional list of File objects and a tokenizer.

        Args:
            iterable (Iterable[File]): An optional iterable of File objects to initialize the list, default is an empty list.
            tokenizer (str | tiktoken.Encoding | None): An optional tokenizer for encoding the content of the files in the list, default is None.
            **kwargs: Additional keyword arguments inherited from the base class.
        """
        list.__init__(self, iterable)
        Model.__init__(self, **kwargs)
        self._tokenizer = tokenizer

    @property
    def tokenizer(self) -> tiktoken.Encoding:
        """
        Retrieves the current tokenizer set for the file list. If the tokenizer is specified as a string, it is converted to a tiktoken.Encoding object.

        Returns:
            tiktoken.Encoding: The tokenizer used for encoding the content of the files in the list.

        Raises:
            ValueError: If no tokenizer is set for the file list.
        """
        if not self._tokenizer:
            raise ValueError("No tokenizer set for the file list")

        if isinstance(self._tokenizer, str):
            return tiktoken.encoding_for_model(self._tokenizer)
        else:
            return self._tokenizer

    @property
    def tokens(self) -> list[int]:
        """
        Aggregates and returns a list of all tokens from the files in the list, encoded using the set tokenizer.

        Returns:
            list[int]: A list of token ids representing the aggregated content of all files in the list.
        """
        all_tokens = []
        for file in self:
            all_tokens += file.tokens
        return all_tokens

    @property
    def chunks(self) -> ChunkList:
        """
        Aggregates and returns a list of all chunks from the files in the list.

        Returns:
            ChunkList: A list of all chunks from the files in the list.
        """
        all_chunks = ChunkList(logger=self.logger.getChild(ChunkList.__name__))

        for file in self:
            all_chunks.extend(file.chunks)

        return all_chunks

    def xml(
        self,
        offset: int = 0,
        chunk_extra_attrs: dict[str, Any] | Callable[["Chunk"], dict[str, Any]] | None = None,
    ) -> str:
        """
        Generates an XML representation of the files in the list. Each file is represented as a separate document within the XML structure.

        Args:
            offset (int): The starting index from which to include files in the XML representation, default is 0.

        Returns:
            str: An XML string representing the files in the list from the specified offset onwards.
        """
        xml = ""
        chunks_offset = 0

        for i in range(offset, len(self)):
            file = self[i]

            if i:
                xml += "\n"

            xml += file.xml(chunks_offset=chunks_offset, chunk_extra_attrs=chunk_extra_attrs)

            chunks_offset += len(file.chunks)

        return xml

    def using(self, tokenizer: str | tiktoken.Encoding) -> "FileList":
        """
        Assigns a tokenizer to the file list. If a string is provided, it is converted to a tiktoken.Encoding object.

        Args:
            tokenizer (str | tiktoken.Encoding): A string representing the model name or an instance of tiktoken.Encoding to be used for tokenization.

        Returns:
            FileList: The current instance of FileList, with the tokenizer set or updated.
        """
        self._tokenizer = tokenizer
        return self

    def order_by(self, key: str | Callable[[File], Any] | None = None, reverse: bool = False, in_place: bool = False) -> "FileList":
        """
        Sorts the files in the list based on a specified key or function. The sorting can be done in place.

        Args:
            key (str | Callable[[File], Any] | None): A key or function used for sorting the files.
            If a string is provided, it refers to an attribute of the File objects. If None, files are sorted by their natural order.
            reverse (bool): If True, the files are sorted in descending order. If False, in ascending order.
            in_place (bool): If True, the sorting is performed on the current FileList instance. If False, a new sorted FileList instance is returned.

        Returns:
            FileList: The sorted list of files. If 'in_place' is True, this is the same modified FileList instance,
                      otherwise, it is a new FileList instance containing the sorted files.
        """
        return self.sort(key=key, reverse=reverse, in_place=in_place)

    def sort(self, key: str | Callable[[File], Any] | None, reverse: bool = False, in_place: bool = False) -> "FileList":
        """
        Sorts the files in the list based on a specified key or function. The sorting can be done in place.

        Args:
            key (str | Callable[[File], Any] | None): A key or function used for sorting the files.
            If a string is provided, it refers to an attribute of the File objects. If None, files are sorted by their natural order.
            reverse (bool): If True, the files are sorted in descending order. If False, in ascending order.
            in_place (bool): If True, the sorting is performed on the current FileList instance. If False, a new sorted FileList instance is returned.

        Returns:
            FileList: The sorted list of files. If 'in_place' is True, this is the same modified FileList instance,
                      otherwise, it is a new FileList instance containing the sorted files.
        """
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
        """
        Returns the first file in the list that matches a specified lookup function. If no function is provided, returns the first file.

        Args:
            lookup (Callable[[File], bool] | None): An optional lookup function that specifies criteria to find the file.

        Returns:
            File | None: The first file that matches the criteria specified by the lookup function. If no function is provided, the first file in the list.
            If no file matches or the list is empty, None is returned.
        """
        if lookup:
            return next(filter(lookup, self), None)
        else:
            return self[0] if self else None

    def last(self, lookup: Callable[[File], bool] | None = None) -> File | None:
        """
        Returns the last file in the list that matches a specified lookup function. If no function is provided, returns the last file.

        Args:
            lookup (Callable[[File], bool] | None): An optional lookup function that specifies criteria to find the file.

        Returns:
            File | None: The last file that matches the criteria specified by the lookup function. If no function is provided, the last file in the list.
            If no file matches or the list is empty, None is returned.
        """
        if lookup:
            return next(filter(lookup, reversed(self)), None)
        else:
            return self[-1] if self else None

    def append(self, object: File) -> "FileList":
        """
        Appends a File object to the list.

        Args:
            object (File): The File object to append to the list.

        Returns:
            FileList: The current instance of FileList, with the File object appended.
        """
        super().append(object)
        return self

    def extend(self, iterable: Iterable[File]) -> "FileList":
        """
        Extends the list by appending elements from another iterable of File objects.

        Args:
            iterable (Iterable[File]): An iterable of File objects to append to the list.

        Returns:
            FileList: The current instance of FileList, extended by the elements from the provided iterable.
        """
        super().extend(iterable)
        return self

    def as_messages(self, role: Role = Role.SYSTEM, tokenizer: str | tiktoken.Encoding | None = None) -> MessageList:
        """
        Converts the list of files into a list of messages, each representing the content of a file.

        Args:
            role (Role): The role of the messages within the system, typically indicates the message's origin or purpose.
            tokenizer (str | tiktoken.Encoding | None): An optional tokenizer for encoding the content of the files into messages, default is the tokenizer set for the file list.

        Returns:
            MessageList: A list of messages, each containing the content of a file.
        """
        return MessageList(
            [file.as_message(role) for file in self],
            tokenizer=tokenizer or self._tokenizer,
            logger=self.logger.getChild(MessageList.__name__),
        )

    def truncate(self, tokens_limit: int, in_place: bool = False) -> "FileList":
        """
        Truncates the content of all files in the list to a specified token limit, optionally in place.

        Args:
            tokens_limit (int): The maximum number of tokens to retain across all files.
            in_place (bool): If True, truncation is applied directly to each file in the list, modifying them.
                             If False, a new truncated FileList instance is created with each file truncated.

        Returns:
            FileList: The truncated list of files. If 'in_place' is True, this is the same modified FileList instance,
                      otherwise, it is a new FileList instance containing the truncated files.
        """
        file_token_limit = tokens_limit // len(self)

        if in_place:
            for file in self:
                file.truncate(file_token_limit, in_place=True)
            return self
        else:
            return FileList([file.truncate(file_token_limit) for file in self], logger=self.logger.getChild(FileList.__name__))

    def as_context(self) -> List[unique_sdk.Integrated.SearchResult]:
        """
        Converts the list of files into a list of search results based on their content and metadata.
        Returns:
            List[unique_sdk.Integrated.SearchResult]: A list of search results, each representing a file in the list.
        """
        results = []

        for file in self:
            results.extend(file.as_context())

        return results
