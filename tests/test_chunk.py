import datetime
import unittest

from blue_lugia.enums import Truncate, TruncateLevel
from blue_lugia.models import Chunk
from blue_lugia.models.file import ChunkList, File
from tests.mocks.event import MockEvent
from tests.mocks.tokenizer import Tokenizer


class TestChunk(unittest.TestCase):
    def setUp(self) -> None:
        self.event = MockEvent.create()

    def test_clean_content(self) -> None:
        content = """<|document|>doc.txt<|/document|><|info|>info<|/info|>Content"""

        chunks = ChunkList()

        file = File(
            event=self.event,
            id="file_id",
            name="file_name",
            mime_type="text/plain",
            chunks=chunks,
            tokenizer=Tokenizer(),
        )

        chunk = Chunk(
            id="chunk_id",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunks.append(chunk)

        self.assertEqual(chunk.content, "Content")

    def test_clean_content_with_no_content(self) -> None:
        content = """<|document|>doc.txt<|/document|><|info|>info<|/info|>"""

        chunks = ChunkList()

        file = File(
            event=self.event,
            id="file_id",
            name="file_name",
            mime_type="text/plain",
            chunks=chunks,
            tokenizer=Tokenizer(),
        )

        chunk = Chunk(
            id="chunk_id",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunks.append(chunk)

        self.assertEqual(chunk.content, "")

    def test_truncate_default(self) -> None:
        content = "Content"

        chunks = ChunkList()

        file = File(
            event=self.event,
            id="file_id",
            name="file_name",
            mime_type="text/plain",
            chunks=chunks,
            tokenizer=Tokenizer(),
        )

        chunk = Chunk(
            id="chunk_id",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunks.append(chunk)

        self.assertEqual(chunk.content, "Content")
        self.assertEqual(chunk.truncate(3).content, "Con")

    def test_truncate_end(self) -> None:
        content = "Content"

        file = File(
            event=self.event,
            id="file_id",
            name="file_name",
            mime_type="text/plain",
            chunks=ChunkList(),
            tokenizer=Tokenizer(),
        )

        chunk = Chunk(
            id="chunk_id",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        self.assertEqual(chunk.content, "Content")

        chunk = Chunk(
            id="chunk_id",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        self.assertEqual(chunk.truncate(3, Truncate.KEEP_END).content, "ent")

        chunk = Chunk(
            id="chunk_id",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        self.assertEqual(chunk.truncate(tokens_limit=3, strategy=Truncate.KEEP_END, level=TruncateLevel.CHUNK).content, "")

    def test_truncate_outer(self) -> None:
        content = "Content"

        file = File(
            event=self.event,
            id="file_id",
            name="file_name",
            mime_type="text/plain",
            chunks=ChunkList(),
            tokenizer=Tokenizer(),
        )

        chunk = Chunk(
            id="chunk_id",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        self.assertEqual(chunk.content, "Content")

        chunk = Chunk(
            id="chunk_id",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        self.assertEqual(chunk.truncate(3, Truncate.KEEP_OUTER).content, "Cot")

        chunk = Chunk(
            id="chunk_id",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        self.assertEqual(chunk.truncate(tokens_limit=3, strategy=Truncate.KEEP_OUTER, level=TruncateLevel.CHUNK).content, "")

    def test_truncate_inner(self) -> None:
        content = "Content"

        chunks = ChunkList()

        file = File(
            event=self.event,
            id="file_id",
            name="file_name",
            mime_type="text/plain",
            chunks=chunks,
            tokenizer=Tokenizer(),
        )

        chunk = Chunk(
            id="chunk_id",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        self.assertEqual(chunk.content, "Content")

        chunk = Chunk(
            id="chunk_id",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        self.assertEqual(chunk.truncate(tokens_limit=3, strategy=Truncate.KEEP_INNER).content, "nte")

        chunk = Chunk(
            id="chunk_id",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        self.assertEqual(chunk.truncate(tokens_limit=3, strategy=Truncate.KEEP_INNER, level=TruncateLevel.CHUNK).content, "")


if __name__ == "__main__":
    unittest.main()
