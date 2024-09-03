import datetime
import unittest

from blue_lugia.enums import Truncate
from blue_lugia.models import Chunk
from blue_lugia.models.file import ChunkList, File
from tests.mocks.event import MockEvent
from tests.mocks.tokenizer import Tokenizer


class TestChunkList(unittest.TestCase):
    def setUp(self) -> None:
        self.event = MockEvent.create()

    def test_first(self) -> None:
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

        chunk_1 = Chunk(
            id="chunk_id_1",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_2 = Chunk(
            id="chunk_id_2",
            order=1,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_3 = Chunk(
            id="chunk_id_3",
            order=2,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunks.append(chunk_1)
        chunks.append(chunk_2)
        chunks.append(chunk_3)

        self.assertEqual(chunks.first(), chunk_1)
        self.assertEqual(chunks.first(lambda c: c.order == 1), chunk_2)
        self.assertIsNone(chunks.first(lambda c: c.order == 69))

    def test_last(self) -> None:
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

        chunk_1 = Chunk(
            id="chunk_id_1",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_2 = Chunk(
            id="chunk_id_2",
            order=1,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_3 = Chunk(
            id="chunk_id_3",
            order=2,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunks.append(chunk_1)
        chunks.append(chunk_2)
        chunks.append(chunk_3)

        self.assertEqual(chunks.last(), chunk_3)
        self.assertEqual(chunks.last(lambda c: c.order == 1), chunk_2)
        self.assertIsNone(chunks.last(lambda c: c.order == 69))

    def test_sort(self) -> None:
        content = """<|document|>doc.txt<|/document|><|info|>info<|/info|>Content"""

        file = File(
            event=self.event,
            id="file_id",
            name="file_name",
            mime_type="text/plain",
            chunks=ChunkList(),
            tokenizer=Tokenizer(),
        )

        chunk_1 = Chunk(
            id="chunk_id_1",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_2 = Chunk(
            id="chunk_id_2",
            order=1,
            content=content,
            start_page=1,
            end_page=1,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_3 = Chunk(
            id="chunk_id_3",
            order=2,
            content=content,
            start_page=2,
            end_page=2,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        sorted_by_order = ChunkList(
            [
                chunk_1,
                chunk_3,
                chunk_2,
            ]
        ).sort("order")

        self.assertEqual(sorted_by_order[0], chunk_1)
        self.assertEqual(sorted_by_order[1], chunk_2)
        self.assertEqual(sorted_by_order[2], chunk_3)

        sorted_reverse_order = ChunkList(
            [
                chunk_1,
                chunk_3,
                chunk_2,
            ]
        ).sort("order", reverse=True)

        self.assertEqual(sorted_reverse_order[0], chunk_3)
        self.assertEqual(sorted_reverse_order[1], chunk_2)
        self.assertEqual(sorted_reverse_order[2], chunk_1)

        sorted_by_start_page = ChunkList(
            [
                chunk_1,
                chunk_3,
                chunk_2,
            ]
        ).sort(lambda c: c.start_page)

        self.assertEqual(sorted_by_start_page[0], chunk_1)
        self.assertEqual(sorted_by_start_page[1], chunk_2)
        self.assertEqual(sorted_by_start_page[2], chunk_3)

    def test_filter(self) -> None:
        content = """<|document|>doc.txt<|/document|><|info|>info<|/info|>Content"""

        file = File(
            event=self.event,
            id="file_id",
            name="file_name",
            mime_type="text/plain",
            chunks=ChunkList(),
            tokenizer=Tokenizer(),
        )

        chunk_1 = Chunk(
            id="chunk_id_1",
            order=0,
            content=content,
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_2 = Chunk(
            id="chunk_id_2",
            order=1,
            content=content,
            start_page=1,
            end_page=1,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_3 = Chunk(
            id="chunk_id_3",
            order=2,
            content=content,
            start_page=2,
            end_page=2,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        filtered = ChunkList(
            [
                chunk_1,
                chunk_2,
                chunk_3,
            ]
        ).filter(lambda c: c.start_page == 1)

        self.assertEqual(filtered[0], chunk_2)
        self.assertEqual(len(filtered), 1)

        # test filtering in_place

        chunks = ChunkList(
            [
                chunk_1,
                chunk_2,
                chunk_3,
            ]
        )

        chunks.filter(lambda c: c.start_page == 1, in_place=True)

        self.assertEqual(chunks[0], chunk_2)
        self.assertEqual(len(chunks), 1)

    def test_truncate_default(self) -> None:
        chunks = ChunkList()

        file = File(
            event=self.event,
            id="file_id",
            name="file_name",
            mime_type="text/plain",
            chunks=chunks,
            tokenizer=Tokenizer(),
        )

        chunk_1 = Chunk(
            id="chunk_id_1",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content x 1""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_2 = Chunk(
            id="chunk_id_2",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content xx 2""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_3 = Chunk(
            id="chunk_id_3",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content xxx 3""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunks.extend(
            [
                chunk_1,
                chunk_2,
                chunk_3,
            ],
        )

        chunk_1_tokens_count = len(chunk_1.tokens)
        chunk_2_tokens_count = len(chunk_2.tokens)
        chunk_3_tokens_count = len(chunk_3.tokens)

        total_tokens_count = chunk_1_tokens_count + chunk_2_tokens_count + chunk_3_tokens_count

        self.assertEqual(len(chunks.truncate(0).tokens), 0)
        self.assertEqual(len(chunks.truncate(total_tokens_count).tokens), total_tokens_count)
        self.assertEqual(len(chunks.truncate(chunk_1_tokens_count).tokens), chunk_1_tokens_count)
        self.assertEqual(chunks.truncate(chunk_1_tokens_count).tokens, chunk_1.tokens)
        self.assertEqual(
            len(chunks.truncate(chunk_1_tokens_count + chunk_2_tokens_count).tokens),
            chunk_1_tokens_count + chunk_2_tokens_count,
        )

    def test_truncate_end(self) -> None:
        chunks = ChunkList()

        file = File(
            event=self.event,
            id="file_id",
            name="file_name",
            mime_type="text/plain",
            chunks=chunks,
            tokenizer=Tokenizer(),
        )

        chunk_1 = Chunk(
            id="chunk_id_1",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content x 1""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_2 = Chunk(
            id="chunk_id_2",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content xx 2""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_3 = Chunk(
            id="chunk_id_3",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content xxx 3""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunks.extend(
            [
                chunk_1,
                chunk_2,
                chunk_3,
            ],
        )

        chunk_1_tokens_count = len(chunk_1.tokens)
        chunk_2_tokens_count = len(chunk_2.tokens)
        chunk_3_tokens_count = len(chunk_3.tokens)

        total_tokens_count = chunk_1_tokens_count + chunk_2_tokens_count + chunk_3_tokens_count

        self.assertEqual(len(chunks.truncate(0, strategy=Truncate.KEEP_END).tokens), 0)
        self.assertEqual(len(chunks.truncate(total_tokens_count, strategy=Truncate.KEEP_END).tokens), total_tokens_count)
        self.assertEqual(len(chunks.truncate(chunk_1_tokens_count, strategy=Truncate.KEEP_END).tokens), chunk_1_tokens_count)
        self.assertEqual(chunks.truncate(chunk_3_tokens_count, strategy=Truncate.KEEP_END).tokens, chunk_3.tokens)
        self.assertEqual(
            len(chunks.truncate(chunk_1_tokens_count + chunk_2_tokens_count, strategy=Truncate.KEEP_END).tokens),
            chunk_1_tokens_count + chunk_2_tokens_count,
        )

    def test_truncate_inner(self) -> None:
        chunks = ChunkList()

        file = File(
            event=self.event,
            id="file_id",
            name="file_name",
            mime_type="text/plain",
            chunks=chunks,
            tokenizer=Tokenizer(),
        )

        chunk_1 = Chunk(
            id="chunk_id_1",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content xxx 1""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_2 = Chunk(
            id="chunk_id_2",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content xx 2""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_3 = Chunk(
            id="chunk_id_3",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content xxx 3""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunks.extend(
            [
                chunk_1,
                chunk_2,
                chunk_3,
            ],
        )

        chunk_1_tokens_count = len(chunk_1.tokens)
        chunk_2_tokens_count = len(chunk_2.tokens)
        chunk_3_tokens_count = len(chunk_3.tokens)

        total_tokens_count = chunk_1_tokens_count + chunk_2_tokens_count + chunk_3_tokens_count

        self.assertEqual(len(chunks.truncate(0, strategy=Truncate.KEEP_INNER).tokens), 0)
        self.assertEqual(len(chunks.truncate(total_tokens_count, strategy=Truncate.KEEP_INNER).tokens), total_tokens_count)
        self.assertEqual(len(chunks.truncate(chunk_1_tokens_count, strategy=Truncate.KEEP_INNER).tokens), chunk_1_tokens_count)

        # This test passes only because the chunklist is symetric so removing sides results in keeping the exact middle chunk
        self.assertEqual(chunks.truncate(chunk_2_tokens_count, strategy=Truncate.KEEP_INNER).tokens, chunk_2.tokens)

        self.assertEqual(
            len(chunks.truncate(chunk_1_tokens_count + chunk_2_tokens_count, strategy=Truncate.KEEP_INNER).tokens),
            chunk_1_tokens_count + chunk_2_tokens_count,
        )

    def test_truncate_outer(self) -> None:
        chunks = ChunkList()

        file = File(
            event=self.event,
            id="file_id",
            name="file_name",
            mime_type="text/plain",
            chunks=chunks,
            tokenizer=Tokenizer(),
        )

        chunk_1 = Chunk(
            id="chunk_id_1",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content x 1""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_2 = Chunk(
            id="chunk_id_2",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content xx 2""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunk_3 = Chunk(
            id="chunk_id_3",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content xxx 3""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        chunks.extend(
            [
                chunk_1,
                chunk_2,
                chunk_3,
            ],
        )

        chunk_1_tokens_count = len(chunk_1.tokens)
        chunk_2_tokens_count = len(chunk_2.tokens)
        chunk_3_tokens_count = len(chunk_3.tokens)

        total_tokens_count = chunk_1_tokens_count + chunk_2_tokens_count + chunk_3_tokens_count

        self.assertEqual(len(chunks.truncate(0, strategy=Truncate.KEEP_OUTER).tokens), 0)
        self.assertEqual(len(chunks.truncate(total_tokens_count, strategy=Truncate.KEEP_OUTER).tokens), total_tokens_count)
        self.assertEqual(len(chunks.truncate(chunk_1_tokens_count, strategy=Truncate.KEEP_OUTER).tokens), chunk_1_tokens_count)

        # This test passes only because the chunklist is symetric so removing sides results in keeping the exact middle chunk
        self.assertEqual(chunks.truncate(chunk_1_tokens_count + chunk_3_tokens_count, strategy=Truncate.KEEP_OUTER).tokens, chunk_1.tokens + chunk_3.tokens)

        self.assertEqual(
            len(chunks.truncate(chunk_1_tokens_count + chunk_2_tokens_count, strategy=Truncate.KEEP_OUTER).tokens),
            chunk_1_tokens_count + chunk_2_tokens_count,
        )

    def test_as_file(self) -> None:
        file = File(
            event=self.event,
            id="file_id",
            name="file_name",
            mime_type="text/plain",
            chunks=ChunkList(),
            tokenizer=Tokenizer(),
        )

        Chunk(
            id="chunk_id",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content 1""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        Chunk(
            id="chunk_id",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content 2""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        Chunk(
            id="chunk_id",
            order=0,
            content="""<|document|>doc.txt<|/document|><|info|>info<|/info|>Content 3""",
            start_page=0,
            end_page=0,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            tokenizer=Tokenizer(),
            file=file,
        )

        files = file.chunks.as_files()

        self.assertEqual(len(files), 1)
        self.assertEqual(len(file.chunks), 3)
        self.assertEqual(len(files[0].chunks), 3)
        self.assertEqual(files[0].name, "file_name")


if __name__ == "__main__":
    unittest.main()
