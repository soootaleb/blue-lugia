import datetime
import unittest

from blue_lugia.enums import Op
from blue_lugia.managers.llm import LanguageModelManager
from blue_lugia.managers.message import MessageManager
from blue_lugia.models.message import Message, MessageList
from blue_lugia.models.query import Q
from blue_lugia.state import StateManager
from tests.mocks.app import MockApp
from tests.mocks.event import MockEvent


class StateManagerTest(unittest.TestCase):
    def _get_state(self, messages: list) -> StateManager:
        class MockMessageManager(MessageManager):
            def all(self, force_refresh: bool = False) -> MessageList:
                return MessageList(messages, tokenizer=self.tokenizer, logger=self.logger)

        class MockLanguageModelManager(LanguageModelManager):
            def complete(self, *args, **kwargs) -> Message:
                return Message.ASSISTANT("DEFAULT_MOCK_ANSWER")

        return MockApp("Tester").using(MockLanguageModelManager).using(MockMessageManager).create_state(MockEvent.create())


class TestManagerArgsParsing(StateManagerTest):
    def test_without_anything(self) -> None:
        state = self._get_state([])
        q = state.files._op_args_kwargs_to_q(Op.OR)
        self.assertEqual(len(q.conditions), 0)
        self.assertTrue(q.evaluate({}))
        self.assertTrue(q.evaluate({"x": 1}))

    def test_single_condition(self) -> None:
        state = self._get_state([])
        q = state.files._op_args_kwargs_to_q(Op.OR, id=1)
        self.assertEqual(len(q.conditions), 1)
        self.assertFalse(q.evaluate({"x": 1}))
        self.assertTrue(q.evaluate({"x": 1, "id": 1}))

    def test_multiple_conditions_or(self) -> None:
        state = self._get_state([])
        q = state.files._op_args_kwargs_to_q(Op.OR, id=1, name="test")
        self.assertEqual(q.connector, Op.OR)
        self.assertEqual(len(q.conditions), 2)
        self.assertFalse(q.evaluate({"id": 2, "name": "fail"}))
        self.assertTrue(q.evaluate({"id": 1, "name": "fail"}))

    def test_multiple_conditions_and(self) -> None:
        state = self._get_state([])
        q = state.files._op_args_kwargs_to_q(Op.AND, id=1, name="test")
        self.assertEqual(q.connector, Op.AND)
        self.assertEqual(len(q.conditions), 2)
        self.assertFalse(q.evaluate({"id": 1, "name": "fail"}))
        self.assertTrue(q.evaluate({"id": 1, "name": "test"}))

    def test_q_to_metadata_empty(self) -> None:
        state = self._get_state([])
        q = state.files._op_args_kwargs_to_q(Q(id=1))
        self.assertEqual(q.connector, Op.AND)
        self.assertEqual(len(q.conditions), 1)
        self.assertFalse(q.evaluate({"x": 1}))
        self.assertTrue(q.evaluate({"x": 1, "id": 1}))

    def test_q_to_metadata_simple_equals(self) -> None:
        state = self._get_state([])
        q = state.files._op_args_kwargs_to_q(Q(Q(Q(id=1))))
        self.assertEqual(q.connector, Op.AND)
        self.assertEqual(len(q.conditions), 1)
        self.assertFalse(q.evaluate({"x": 1}))
        self.assertTrue(q.evaluate({"x": 1, "id": 1}))

    def test_q_to_metadata_complex(self) -> None:
        state = self._get_state([])
        q = state.files._op_args_kwargs_to_q(Q(id=1), Q(name="test"))
        self.assertEqual(q.connector, Op.AND)
        self.assertEqual(len(q.conditions), 2)
        self.assertFalse(q.evaluate({"x": 1, "name": "fail"}))
        self.assertFalse(q.evaluate({"id": 1, "name": "fail"}))
        self.assertTrue(q.evaluate({"id": 1, "name": "test"}))

    def test_q_to_metadata_complex_or(self) -> None:
        state = self._get_state([])
        q = state.files._op_args_kwargs_to_q(Op.OR, Q(id=1), Q(name="test"))
        self.assertEqual(q.connector, Op.OR)
        self.assertEqual(len(q.conditions), 2)
        self.assertFalse(q.evaluate({"id": 2, "name": "fail"}))
        self.assertTrue(q.evaluate({"id": 1, "name": "fail"}))
        self.assertTrue(q.evaluate({"id": 2, "name": "test"}))
        self.assertFalse(q.evaluate({"id": 2, "x": "test"}))
        self.assertTrue(q.evaluate({"id": 1, "name": "test"}))

    def test_q_to_metadata_complex_and(self) -> None:
        state = self._get_state([])
        q = state.files._op_args_kwargs_to_q(Op.AND, Q(id=1), Q(name="test"), file="test.txt", path="test")
        self.assertEqual(q.connector, Op.AND)
        self.assertEqual(len(q.conditions), 4)
        self.assertFalse(q.evaluate({"id": 2, "name": "test", "file": "test.txt", "path": "test"}))
        self.assertFalse(q.evaluate({"id": 2, "name": "test", "file": "test.txt"}))
        self.assertFalse(q.evaluate({"id": 2, "name": "test"}))
        self.assertTrue(q.evaluate({"id": 1, "name": "test", "file": "test.txt", "path": "test"}))

    def test_q_to_metadata_complex_and_or(self) -> None:
        state = self._get_state([])
        q = state.files._op_args_kwargs_to_q(Q(id=1) | Q(name="test"), file="test.txt", path="test")
        self.assertEqual(q.connector, Op.AND)
        self.assertEqual(len(q.conditions), 3)
        self.assertEqual(q.conditions[0].connector, Op.OR)
        self.assertEqual(len(q.conditions[0].conditions), 2)
        self.assertTrue(q.evaluate({"id": 1, "name": "fail", "file": "test.txt", "path": "test"}))
        self.assertTrue(q.evaluate({"id": 2, "name": "test", "file": "test.txt", "path": "test"}))
        self.assertTrue(q.evaluate({"id": 1, "name": "test", "file": "test.txt", "path": "test"}))
        self.assertFalse(q.evaluate({"id": 1, "name": "test", "file": "test.txt"}))
        self.assertFalse(q.evaluate({"id": 1, "name": "test"}))


class TestManagerFilterAPI(StateManagerTest):
    def test_filter_empty(self) -> None:
        state = self._get_state([])
        manager = state.files.filter()
        self.assertEqual(manager._filters_operator, Op.OR)
        self.assertEqual(manager._filters, [])
        self.assertIsNotNone(manager._query)

    def test_filter_single(self) -> None:
        state = self._get_state([])
        manager = state.files.filter(id=1)
        self.assertEqual(manager._filters_operator, Op.OR)
        self.assertEqual(manager._filters, [["id", "eq", 1]])
        self.assertIsNotNone(manager._query)

    def test_filter_multiple_and(self) -> None:
        state = self._get_state([])
        manager = state.files.filter(id=1, name="test")
        self.assertEqual(manager._filters_operator, Op.OR)
        self.assertEqual(manager._filters, [["id", "eq", 1], ["name", "eq", "test"]])
        self.assertIsNotNone(manager._query)

    def test_filter_multiple_and_op(self) -> None:
        state = self._get_state([])
        manager = state.files.filter(Op.AND, id=1, name="test")
        self.assertEqual(manager._filters_operator, Op.AND)
        self.assertEqual(manager._filters, [["id", "eq", 1], ["name", "eq", "test"]])
        self.assertIsNotNone(manager._query)

    def test_filter_multiple_and_q(self) -> None:
        state = self._get_state([])
        manager = state.files.filter(Q(id=1))
        self.assertEqual(manager._filters_operator, Op.OR)
        self.assertEqual(manager._filters, [])
        self.assertIsNotNone(manager._query)

        if manager._query is not None:
            query = manager._query
            self.assertFalse(query.negated)
            self.assertEqual(query.connector, Op.AND)
            self.assertTrue(query.evaluate({"id": 1}))

    def test_filter_multiple_and_multiple_q(self) -> None:
        state = self._get_state([])
        manager = state.files.filter(Q(id=1), Q(name="test"))
        self.assertEqual(manager._filters_operator, Op.OR)
        self.assertEqual(manager._filters, [])
        self.assertIsNotNone(manager._query)

        if manager._query is not None:
            query = manager._query
            self.assertFalse(query.negated)
            self.assertEqual(query.connector, Op.AND)
            self.assertEqual(len(query._conditions), 2)
            self.assertTrue(query.evaluate({"id": 1, "name": "test"}))
            self.assertFalse(query.evaluate({"id": 1, "name": "fail"}))

    def test_filter_multiple_and_multiple_q_op(self) -> None:
        state = self._get_state([])
        manager = state.files.filter(Op.OR, Q(id=1), Q(name="test"))
        self.assertEqual(manager._filters_operator, Op.OR)
        self.assertEqual(manager._filters, [])
        self.assertIsNotNone(manager._query)

        if manager._query is not None:
            query = manager._query
            self.assertFalse(query.negated)
            self.assertEqual(query.connector, Op.OR)
            self.assertEqual(len(query._conditions), 2)
            self.assertTrue(query.evaluate({"id": 1, "name": "test"}))
            self.assertTrue(query.evaluate({"id": 1, "name": "fail"}))
            self.assertFalse(query.evaluate({"id": 2, "name": "fail"}))

    def test_filter_multiple_and_multiple_q_op_kwargs(self) -> None:
        state = self._get_state([])
        manager = state.files.filter(Op.AND, Q(id=1), Q(name="test"), file="test.txt", path="test")
        self.assertEqual(manager._filters_operator, Op.AND)
        self.assertEqual(manager._filters, [["file", "eq", "test.txt"], ["path", "eq", "test"]])
        self.assertIsNotNone(manager._query)

        if manager._query is not None:
            query = manager._query
            self.assertFalse(query.negated)
            self.assertEqual(query.connector, Op.AND)
            self.assertEqual(len(query._conditions), 4)
            self.assertTrue(query.evaluate({"id": 1, "name": "test", "file": "test.txt", "path": "test"}))
            self.assertFalse(query.evaluate({"id": 1, "name": "test", "file": "test.txt"}))
            self.assertFalse(query.evaluate({"id": 1, "name": "test"}))

    def test_filter_multiple_and_multiple_q_op_kwargs_q(self) -> None:
        state = self._get_state([])
        manager = state.files.filter(Q(id=1) | Q(name="test"), file="test.txt", path="test")
        self.assertEqual(manager._filters_operator, Op.OR)
        self.assertEqual(manager._filters, [["file", "eq", "test.txt"], ["path", "eq", "test"]])
        self.assertIsNotNone(manager._query)

        if manager._query is not None:
            query = manager._query
            self.assertFalse(query.negated)
            self.assertEqual(query.connector, Op.AND)
            self.assertEqual(len(query._conditions), 3)
            self.assertEqual(query._conditions[0].connector, Op.OR)
            self.assertEqual(len(query._conditions[0]._conditions), 2)
            self.assertTrue(query.evaluate({"id": 1, "name": "fail", "file": "test.txt", "path": "test"}))
            self.assertTrue(query.evaluate({"id": 2, "name": "test", "file": "test.txt", "path": "test"}))
            self.assertTrue(query.evaluate({"id": 1, "name": "test", "file": "test.txt", "path": "test"}))
            self.assertFalse(query.evaluate({"id": 1, "name": "test", "file": "test.txt"}))
            self.assertFalse(query.evaluate({"id": 1, "name": "test"}))


class TestFilterOperations(StateManagerTest):
    def test_filter_empty(self) -> None:
        state = self._get_state([])
        manager = state.files.filter()
        self.assertEqual(manager._filters_operator, Op.OR)
        self.assertEqual(manager._filters, [])
        self.assertIsNotNone(manager._query)

    def test_filter_single(self) -> None:
        state = self._get_state([])
        manager = state.files.filter(id=1)
        self.assertEqual(manager._filters_operator, Op.OR)
        self.assertEqual(manager._filters, [["id", "eq", 1]])
        self.assertIsNotNone(manager._query)

    def test_filter_multiple_and(self) -> None:
        state = self._get_state([])
        manager = state.files.filter(Op.AND, id=1, name="test")
        self.assertEqual(manager._filters_operator, Op.AND)
        self.assertEqual(manager._filters, [["id", "eq", 1], ["name", "eq", "test"]])
        self.assertIsNotNone(manager._query)


class TestQToMetadataOperations(StateManagerTest):
    def test_q_to_metadata_empta(self) -> None:
        state = self._get_state([])
        metadata = state.files._q_to_metadata(Q())
        self.assertEqual(metadata, None)

    def test_q_to_metadata_simple_equals(self) -> None:
        state = self._get_state([])
        metadata = state.files._q_to_metadata(Q(id=1))
        self.assertEqual(
            metadata,
            {
                "path": ["id"],
                "operator": "equals",
                "value": 1,
            },
        )

    def test_q_to_metadata_simple_eq(self) -> None:
        state = self._get_state([])
        metadata = state.files._q_to_metadata(Q(id__eq=1))
        self.assertEqual(
            metadata,
            {
                "path": ["id"],
                "operator": "equals",
                "value": 1,
            },
        )

    def test_q_to_metadata_simple_not(self) -> None:
        state = self._get_state([])
        # Test with negation
        metadata = state.files._q_to_metadata(~Q(id__eq=1))
        self.assertEqual(metadata, {"path": ["id"], "operator": "notEquals", "value": 1})

    def test_q_to_metadata_simple_not_and(self) -> None:
        state = self._get_state([])
        # Test with AND operation
        metadata = state.files._q_to_metadata(Q(id__eq=1) & Q(type__eq="document"))
        self.assertEqual(metadata, {"and": [{"path": ["id"], "operator": "equals", "value": 1}, {"path": ["type"], "operator": "equals", "value": "document"}]})

    def test_q_to_metadata_simple_or(self) -> None:
        state = self._get_state([])
        # Test with OR operation
        metadata = state.files._q_to_metadata(Q(id__eq=1) | Q(type__eq="document"))
        self.assertEqual(metadata, {"or": [{"path": ["id"], "operator": "equals", "value": 1}, {"path": ["type"], "operator": "equals", "value": "document"}]})

    def test_q_to_metadata_simple_and_or(self) -> None:
        state = self._get_state([])
        # Test nested Q objects with mixed AND and OR operations
        metadata = state.files._q_to_metadata((Q(id__eq=1) & Q(status__eq="active")) | Q(type__eq="image"))
        self.assertEqual(
            metadata,
            {
                "or": [
                    {"and": [{"path": ["id"], "operator": "equals", "value": 1}, {"path": ["status"], "operator": "equals", "value": "active"}]},
                    {"path": ["type"], "operator": "equals", "value": "image"},
                ]
            },
        )

    def test_q_to_metadata_complex(self) -> None:
        state = self._get_state([])
        metadata = state.files._q_to_metadata((Q(id=1) | Q(id=2)) & Q(name__contains="NeoXam", update_date__start__gt="2021-01-01"))
        self.assertEqual(
            metadata,
            {
                "and": [
                    {"or": [{"path": ["id"], "operator": "equals", "value": 1}, {"path": ["id"], "operator": "equals", "value": 2}]},
                    {"path": ["name"], "operator": "contains", "value": "NeoXam"},
                    {"path": ["update_date", "start"], "operator": "greaterThan", "value": "2021-01-01"},
                ]
            },
        )

    def test_q_to_metadata_nested(self) -> None:
        state = self._get_state([])
        metadata = state.files._q_to_metadata(Q(my_array__nested=Q(id=1) & ~Q(name="file.txt")))
        self.assertEqual(
            metadata,
            {
                "path": ["my_array", "*"],
                "operator": "nested",
                "value": {
                    "and": [{"path": ["id"], "operator": "equals", "value": 1}, {"path": ["name"], "operator": "notEquals", "value": "file.txt"}],
                },
            },
        )

    def test_q_to_metadata_nested_or(self) -> None:
        state = self._get_state([])
        metadata = state.files._q_to_metadata(
            Q(url__contains=".com/SitePages", FirstPublishedDate__gt="2024-07-15T00:00:00.00Z", FirstPublishedDate__lt="2024-07-19T00:00:00.00Z")
            & ~Q(url__contains="fr/")
            & ~Q(url__contains="Templates/")
        )
        self.assertEqual(
            metadata,
            {
                "and": [
                    {
                        "path": ["url"],
                        "operator": "contains",
                        "value": ".com/SitePages",
                    },
                    {
                        "path": ["FirstPublishedDate"],
                        "operator": "greaterThan",
                        "value": "2024-07-15T00:00:00.00Z",
                    },
                    {
                        "path": ["FirstPublishedDate"],
                        "operator": "lessThan",
                        "value": "2024-07-19T00:00:00.00Z",
                    },
                    {
                        "path": ["url"],
                        "operator": "notContains",
                        "value": "fr/",
                    },
                    {
                        "path": ["url"],
                        "operator": "notContains",
                        "value": "Templates/",
                    },
                ]
            },
        )

    def test_q_to_metadata_in(self) -> None:
        state = self._get_state([])
        metadata = state.files._q_to_metadata(Q(id__in=[1, 2, 3]))
        self.assertEqual(
            metadata,
            {
                "path": ["id"],
                "operator": "in",
                "value": [1, 2, 3],
            },
        )

    def test_q_to_metadata_nested_or_icontains(self) -> None:
        state = self._get_state([])
        metadata = state.files._q_to_metadata(Q(key__icontains=".pdf") & Q(key__icontains="NeoXam") | ~Q(key__icontains=".pdf") & ~Q(key__icontains=".xlsx"))
        self.assertEqual(
            metadata,
            {
                "or": [
                    {
                        "and": [
                            {"path": ["key"], "operator": "contains", "value": ".pdf"},
                            {"path": ["key"], "operator": "contains", "value": "NeoXam"},
                        ]
                    },
                    {
                        "and": [
                            {"path": ["key"], "operator": "notContains", "value": ".pdf"},
                            {"path": ["key"], "operator": "notContains", "value": ".xlsx"},
                        ]
                    },
                ]
            },
        )

    def test_old_vs_new_api_equivalent_none(self) -> None:
        state = self._get_state([])

        filtered_state = state.files.fork().filter(op=Op.AND, **{})

        old_api_metadata = filtered_state._filters_to_metadata()

        filtered_state = state.files.fork().filter(Q())

        new_api_metadata = state.files._q_to_metadata(filtered_state._query or Q())

        self.assertEqual(old_api_metadata, new_api_metadata)

    def test_old_vs_new_api_equivalent_complex(self) -> None:
        state = self._get_state([])

        filtered_state = state.files.fork().filter(
            op=Op.AND,
            **{
                "url__contains": ".com/SitePages",
                "url__notContains__in": ["fr/", "Templates/"],
                "FirstPublishedDate__contains": "2",
            },
        )

        old_api_metadata = filtered_state._filters_to_metadata()

        filtered_state = state.files.fork().filter(
            Q(url__contains=".com/SitePages") & ~Q(url__contains="fr/") & ~Q(url__contains="Templates/") & Q(FirstPublishedDate__contains="2")
        )

        new_api_metadata = state.files._q_to_metadata(filtered_state._query or Q())

        self.assertEqual(old_api_metadata, new_api_metadata)

    def test_old_vs_new_api_equivalent_dynamic(self) -> None:
        state = self._get_state([])

        start_date = (datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=-16)).isoformat(timespec="milliseconds") + "Z"
        end_date = (datetime.datetime.now().replace(hour=23, minute=59, second=59, microsecond=999) + datetime.timedelta(days=0)).isoformat(timespec="milliseconds") + "Z"

        filtered_state = state.files.fork().filter(
            op=Op.AND,
            **{
                "url__contains": ".com/SitePages",
                "url__notContains__in": ["fr/", "Templates/"],
                "FirstPublishedDate__greaterThan": start_date,
                "FirstPublishedDate__lessThan": end_date,
            },
        )

        old_api_metadata = filtered_state._filters_to_metadata()

        filtered_state = state.files.fork().filter(
            Q(url__contains=".com/SitePages") & ~Q(url__contains="fr/") & ~Q(url__contains="Templates/") & Q(FirstPublishedDate__gt=start_date) & Q(FirstPublishedDate__lt=end_date)
        )

        new_api_metadata = state.files._q_to_metadata(filtered_state._query or Q())

        self.assertEqual(old_api_metadata, new_api_metadata)


class TestQToContentFilters(StateManagerTest):
    def test_q_to_content_filters_empty(self) -> None:
        state = self._get_state([])
        wheres = state.files._q_to_content_filters(Q())
        self.assertEqual(wheres, {})

    def test_q_to_content_filters_simple_equals(self) -> None:
        state = self._get_state([])
        wheres = state.files._q_to_content_filters(~Q(id=1))
        self.assertEqual(wheres, {"NOT": {"AND": [{"id": {"equals": 1}}]}})

    def test_q_to_content_filters_simple_or_not(self) -> None:
        state = self._get_state([])
        wheres = state.files._q_to_content_filters(Q(x=1) | ~Q(id=1))
        self.assertEqual(wheres, {"OR": [{"x": {"equals": 1}}, {"NOT": {"AND": [{"id": {"equals": 1}}]}}]})

    def test_q_to_content_filters_complex_and_not(self) -> None:
        state = self._get_state([])
        query = Q(
            Q(url__startswith="https://pictet.sharepoint.com/SitePages/", url__endswith=".aspx"),
            ~Q(Q(url__icontains="/fr/") | Q(url__icontains="/Templates/")),
        )
        wheres = state.files._q_to_content_filters(query)
        self.assertEqual(
            wheres,
            {
                "AND": [
                    {"url": {"startsWith": "https://pictet.sharepoint.com/SitePages/"}},
                    {"url": {"endsWith": ".aspx"}},
                    {
                        "NOT": {
                            "OR": [
                                {"url": {"contains": "/fr/", "mode": "insensitive"}},
                                {"url": {"contains": "/Templates/", "mode": "insensitive"}},
                            ]
                        }
                    },
                ]
            },
        )

    def test_q_to_content_filters_complex_and_or_not(self) -> None:
        state = self._get_state([])
        query = Q(key__contains=".pdf") & Q(key__contains="NeoXam") | ~Q(key__contains=".pdf")
        wheres = state.files._q_to_content_filters(query)
        self.assertEqual(
            wheres,
            {
                "OR": [
                    {
                        "AND": [
                            {"key": {"contains": ".pdf"}},
                            {"key": {"contains": "NeoXam"}},
                        ]
                    },
                    {"NOT": {"AND": [{"key": {"contains": ".pdf"}}]}},
                ]
            },
        )

    def test_q_to_content_filters_complex_and_or_not_icontains(self) -> None:
        state = self._get_state([])
        query = Q(key__icontains=".pdf") & Q(key__icontains="NeoXam") | ~Q(key__icontains=".pdf") & ~Q(key__icontains=".xlsx")
        wheres = state.files._q_to_content_filters(query)
        self.assertEqual(
            wheres,
            {
                "OR": [
                    {
                        "AND": [
                            {"key": {"contains": ".pdf", "mode": "insensitive"}},
                            {"key": {"contains": "NeoXam", "mode": "insensitive"}},
                        ]
                    },
                    {
                        "AND": [
                            {"NOT": {"AND": [{"key": {"contains": ".pdf", "mode": "insensitive"}}]}},
                            {"NOT": {"AND": [{"key": {"contains": ".xlsx", "mode": "insensitive"}}]}},
                        ]
                    },
                ]
            },
        )

    def test_old_api_equivalent_none(self) -> None:
        state = self._get_state([])

        filtered_state = state.files.filter(op=Op.AND, **{})

        old_api_filters = filtered_state._filters_to_content_filters()
        new_api_filters = filtered_state._q_to_content_filters(filtered_state._query or Q())

        self.assertEqual(old_api_filters, new_api_filters)

    def test_old_api_equivalent_simple(self) -> None:
        state = self._get_state([])

        filtered_state = state.files.filter(key="file.txt")

        old_api_filters = filtered_state._filters_to_content_filters()
        new_api_filters = filtered_state._q_to_content_filters(filtered_state._query or Q())

        self.assertEqual(old_api_filters, new_api_filters)

    def test_new_api_equivalent_none(self) -> None:
        state = self._get_state([])

        filtered_state = state.files.filter(Q())

        old_api_filters = state.files.fork().filter(Op.AND, **{})._filters_to_content_filters()
        new_api_filters = state.files._q_to_content_filters(filtered_state._query or Q())

        self.assertEqual(old_api_filters, new_api_filters)

    def test_new_api_equivalent_simple(self) -> None:
        state = self._get_state([])

        filtered_state = state.files.filter(Q(key="file.txt"))

        old_api_filters = state.files.fork().filter(Op.AND, key="file.txt")._filters_to_content_filters()
        new_api_filters = state.files._q_to_content_filters(filtered_state._query or Q())

        self.assertEqual(old_api_filters, new_api_filters)


if __name__ == "__main__":
    unittest.main()
