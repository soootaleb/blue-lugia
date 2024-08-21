import unittest

from blue_lugia.enums import Op
from blue_lugia.models import Q


class TestQ(unittest.TestCase):
    def test_single_condition_match(self) -> None:
        q = Q(x=1)
        self.assertTrue(q.evaluate({"x": 1}))
        self.assertFalse(q.evaluate({"x": 2}))

    def test_single_condition_no_match(self) -> None:
        q = Q(x=1)
        self.assertFalse(q.evaluate({"x": 2}))

    def test_and_condition_both_match(self) -> None:
        q = Q(x=1) & Q(y=2)
        self.assertTrue(q.evaluate({"x": 1, "y": 2}))
        self.assertFalse(q.evaluate({"x": 1, "y": 3}))
        self.assertFalse(q.evaluate({"x": 2, "y": 2}))

    def test_and_condition_one_match(self) -> None:
        q = Q(x=1) & Q(y=2)
        self.assertFalse(q.evaluate({"x": 1, "y": 3}))
        self.assertFalse(q.evaluate({"x": 2, "y": 2}))

    def test_or_condition_one_match(self) -> None:
        q = Q(x=1) | Q(y=2)
        self.assertTrue(q.evaluate({"x": 1, "y": 3}))
        self.assertTrue(q.evaluate({"x": 2, "y": 2}))
        self.assertFalse(q.evaluate({"x": 3, "y": 3}))

    def test_or_condition_both_match(self) -> None:
        q = Q(x=1) | Q(y=2)
        self.assertTrue(q.evaluate({"x": 1, "y": 2}))

    def test_complex_and_or_combination(self) -> None:
        q = (Q(x=1) & Q(y=2)) | Q(z=3)
        self.assertTrue(q.evaluate({"x": 1, "y": 2}))
        self.assertTrue(q.evaluate({"z": 3}))
        self.assertFalse(q.evaluate({"x": 1, "y": 3}))
        self.assertFalse(q.evaluate({"x": 2, "y": 2}))
        self.assertTrue(q.evaluate({"x": 1, "y": 2, "z": 3}))

    def test_nested_conditions(self) -> None:
        q = Q(x=1) & (Q(y=2) | Q(z=3))
        self.assertTrue(q.evaluate({"x": 1, "y": 2}))
        self.assertTrue(q.evaluate({"x": 1, "z": 3}))
        self.assertFalse(q.evaluate({"x": 1, "y": 3}))
        self.assertFalse(q.evaluate({"x": 2, "y": 2}))
        self.assertTrue(q.evaluate({"x": 1, "y": 2, "z": 3}))

    def test_no_conditions(self) -> None:
        q = Q()
        self.assertTrue(q.evaluate({"x": 1}))  # Assumes no conditions always return True

    def test_unsupported_key(self) -> None:
        q = Q(a=1) | Q(b=2)
        self.assertFalse(q.evaluate({"x": 1, "y": 2}))  # No match because 'a' and 'b' are not in the dataset

    def test_empty_input(self) -> None:
        q = Q(x=1)
        self.assertFalse(q.evaluate({}))  # No match with empty dataset

    def test_empty_q(self) -> None:
        q = Q()
        self.assertTrue(q.evaluate({}))  # Assuming an empty Q should match any input, returns True
        q._connector = Op.OR
        self.assertTrue(q.evaluate({}))  # Assuming an empty Q should match any input, returns True

    def test_complex_combination_with_multiple_and_or(self) -> None:
        q = (Q(x=1) & Q(y=2)) | (Q(z=3) & Q(a=4))
        self.assertTrue(q.evaluate({"x": 1, "y": 2}))
        self.assertTrue(q.evaluate({"z": 3, "a": 4}))
        self.assertFalse(q.evaluate({"x": 1, "y": 3, "z": 3}))
        self.assertFalse(q.evaluate({"x": 2, "y": 2, "a": 4}))
        self.assertTrue(q.evaluate({"x": 1, "y": 2, "z": 3, "a": 4}))

    def test_not_single_condition(self) -> None:
        q = ~Q(x=1)
        self.assertTrue(q.evaluate({"x": 2}))
        self.assertFalse(q.evaluate({"x": 1}))

    def test_not_combined_with_and(self) -> None:
        q = ~Q(x=1) & Q(y=2)
        self.assertTrue(q.evaluate({"x": 2, "y": 2}))
        self.assertFalse(q.evaluate({"x": 1, "y": 2}))
        self.assertFalse(q.evaluate({"x": 2, "y": 3}))

    def test_not_combined_with_or(self) -> None:
        q = ~Q(x=1) | Q(y=2)
        self.assertTrue(q.evaluate({"x": 2, "y": 3}))
        self.assertTrue(q.evaluate({"x": 2, "y": 2}))
        self.assertFalse(q.evaluate({"x": 1, "y": 3}))

    def test_double_not(self) -> None:
        q = ~~Q(x=1)
        self.assertTrue(q.evaluate({"x": 1}))
        self.assertFalse(q.evaluate({"x": 2}))

    def test_not_nested_condition(self) -> None:
        q = ~(Q(x=1) & Q(y=2))
        self.assertTrue(q.evaluate({"x": 1, "y": 3}))  # Because Q(y=2) fails
        self.assertTrue(q.evaluate({"x": 2, "y": 2}))  # Because Q(x=1) fails
        self.assertTrue(q.evaluate({"x": 2, "y": 3}))  # Both conditions fail
        self.assertFalse(q.evaluate({"x": 1, "y": 2}))  # Both conditions succeed

    def test_not_with_or_and_and(self) -> None:
        q = ~(Q(x=1) | Q(y=2)) & Q(z=3)
        self.assertTrue(q.evaluate({"x": 2, "y": 3, "z": 3}))  # Q(x=1) and Q(y=2) both fail
        self.assertFalse(q.evaluate({"x": 1, "z": 3}))  # Q(x=1) succeeds
        self.assertFalse(q.evaluate({"y": 2, "z": 3}))  # Q(y=2) succeeds
        self.assertFalse(q.evaluate({"x": 1, "y": 2, "z": 3}))  # Both Q(x=1) and Q(y=2) succeed

    def test_not_with_missing_key(self) -> None:
        q = ~Q(x=1)
        self.assertTrue(q.evaluate({}))  # Should return True as x is not 1 (or not present)

    def test_not_on_empty_q(self) -> None:
        q = ~Q()
        self.assertFalse(q.evaluate({"x": 1}))  # Assuming an empty Q matches any input, NOT should return False

    def test_not_with_complex_condition(self) -> None:
        q = ~(Q(x=1) & (Q(y=2) | Q(z=3)))
        self.assertTrue(q.evaluate({"x": 2, "y": 3}))  # First condition fails
        self.assertTrue(q.evaluate({"x": 1, "y": 3}))  # OR fails because y=2 doesn't match and z=3 isn't evaluated
        self.assertTrue(q.evaluate({"x": 2, "y": 2}))  # First condition fails
        self.assertFalse(q.evaluate({"x": 1, "y": 2}))  # All conditions succeed, so NOT should return False


if __name__ == "__main__":
    unittest.main()
