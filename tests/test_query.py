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

    def test_and_multiple_conditions(self) -> None:
        """Test combining more than two conditions using AND."""
        q = Q(x=1) & Q(y=2) & Q(z=3)
        self.assertTrue(q.evaluate({"x": 1, "y": 2, "z": 3}))
        self.assertFalse(q.evaluate({"x": 1, "y": 2, "z": 4}))

    def test_or_multiple_conditions(self) -> None:
        """Test combining more than two conditions using OR."""
        q = Q(x=1) | Q(y=2) | Q(z=3)
        self.assertTrue(q.evaluate({"x": 1}))
        self.assertTrue(q.evaluate({"y": 2}))
        self.assertTrue(q.evaluate({"z": 3}))
        self.assertFalse(q.evaluate({"x": 4, "y": 5, "z": 6}))

    def test_nested_and_or(self) -> None:
        """Test multiple levels of nested AND and OR conditions."""
        q = Q(x=1) & (Q(y=2) | (Q(z=3) & Q(w=4)))
        self.assertTrue(q.evaluate({"x": 1, "y": 2}))
        self.assertTrue(q.evaluate({"x": 1, "z": 3, "w": 4}))
        self.assertTrue(q.evaluate({"x": 1, "y": 3, "z": 3, "w": 4}))
        self.assertFalse(q.evaluate({"x": 1, "z": 3}))

    def test_nested_negations(self) -> None:
        """Test combining multiple levels of negations."""
        q = ~(Q(x=1) & ~(Q(y=2) | Q(z=3)))
        self.assertTrue(q.evaluate({"x": 2}))
        self.assertTrue(q.evaluate({"x": 1, "y": 2}))
        self.assertFalse(q.evaluate({"x": 1, "y": 4, "z": 5}))
        self.assertTrue(q.evaluate({"x": 1, "y": 4, "z": 3}))

    def test_combining_empty_and_nonempty_q(self) -> None:
        """Test combining empty Q objects with non-empty ones using AND."""
        q = Q() & Q(x=1)
        self.assertTrue(q.evaluate({"x": 1}))
        self.assertFalse(q.evaluate({"x": 2}))
        self.assertTrue(q.evaluate({"x": 1, "y": 2}))

    def test_or_with_empty_q(self) -> None:
        """Test combining empty Q objects with non-empty ones using OR."""
        q = Q() | Q(x=1)
        self.assertTrue(q.evaluate({"x": 2}))
        self.assertTrue(q.evaluate({"x": 1}))
        self.assertTrue(q.evaluate({}))

    def test_combining_q_with_itself(self) -> None:
        """Test combining a Q object with itself."""
        q1 = Q(x=1)
        q = q1 & q1
        self.assertTrue(q.evaluate({"x": 1}))
        self.assertFalse(q.evaluate({"x": 2}))

    def test_negation_of_empty_q(self) -> None:
        """Test negating an empty Q object."""
        q = ~Q()
        self.assertFalse(q.evaluate({"x": 1}))
        self.assertFalse(q.evaluate({}))

    def test_large_nested_structure(self) -> None:
        """Test evaluating a deeply nested Q object."""
        q = Q(x1=1)
        for i in range(2, 20):
            q = q & Q(**{f"x{i}": i})
        data = {f"x{i}": i for i in range(1, 20)}
        self.assertTrue(q.evaluate(data))
        data["x10"] = 0
        self.assertFalse(q.evaluate(data))

    def test_condition_with_none_value(self) -> None:
        """Test condition where the value is None."""
        q = Q(x=None)
        self.assertTrue(q.evaluate({"x": None}))
        self.assertFalse(q.evaluate({"x": 1}))
        self.assertTrue(q.evaluate({}))

    def test_condition_with_value_none_in_data(self) -> None:
        """Test condition where the data contains None as a value."""
        q = Q(x=1)
        self.assertFalse(q.evaluate({"x": None}))
        self.assertFalse(q.evaluate({}))

    def test_contradictory_conditions(self) -> None:
        """Test conditions that are contradictory and should always be False."""
        q = Q(x=1) & Q(x=2)
        self.assertFalse(q.evaluate({"x": 1}))
        self.assertFalse(q.evaluate({"x": 2}))
        self.assertFalse(q.evaluate({"x": 1, "x": 2}))

    def test_combining_q_with_different_connectors(self) -> None:
        """Test combining Q objects with different connectors."""
        q1 = Q(x=1)
        q1._connector = Op.AND
        q2 = Q(y=2)
        q2._connector = Op.OR
        q = q1 & q2
        self.assertTrue(q.evaluate({"x": 1, "y": 2}))
        self.assertFalse(q.evaluate({"x": 1, "y": 3}))
        self.assertFalse(q.evaluate({"x": 2, "y": 2}))

    def test_multiple_negations(self) -> None:
        """Test multiple levels of negations."""
        q = ~~~Q(x=1)
        self.assertFalse(q.evaluate({"x": 1}))
        self.assertTrue(q.evaluate({"x": 2}))

    def test_complex_negations_and_connectors(self) -> None:
        """Test complex combinations of connectors and negations."""
        q = (~Q(x=1) & Q(y=2)) | (Q(z=3) & ~Q(w=4))
        self.assertTrue(q.evaluate({"x": 2, "y": 2}))
        self.assertTrue(q.evaluate({"z": 3, "w": 5}))
        self.assertFalse(q.evaluate({"x": 1, "y": 2}))
        self.assertFalse(q.evaluate({"z": 3, "w": 4}))

    def test_negated_empty_q_combined_with_and(self) -> None:
        """Test negating an empty Q and combining it with another using AND."""
        q = ~Q() & Q(x=1)
        self.assertFalse(q.evaluate({"x": 1}))
        self.assertFalse(q.evaluate({"x": 2}))

    def test_negated_empty_q_combined_with_or(self) -> None:
        """Test negating an empty Q and combining it with another using OR."""
        q = ~Q() | Q(x=1)
        self.assertTrue(q.evaluate({"x": 1}))
        self.assertFalse(q.evaluate({"x": 2}))
        self.assertFalse(q.evaluate({}))

    def test_multiple_empty_qs(self) -> None:
        """Test combining multiple empty Q objects."""
        q = Q() & Q()
        self.assertTrue(q.evaluate({"x": 1}))  # True & True = True
        self.assertTrue(q.evaluate({}))

    def test_negated_empty_qs(self) -> None:
        """Test combining multiple negated empty Q objects."""
        q = ~Q() & ~Q()
        self.assertFalse(q.evaluate({"x": 1}))  # False & False = False
        self.assertFalse(q.evaluate({}))

    def test_condition_with_different_types(self) -> None:
        """Test condition where data types differ between condition and data."""
        q = Q(x="1")
        self.assertTrue(q.evaluate({"x": "1"}))
        self.assertFalse(q.evaluate({"x": 1}))  # Different types
    def test_missing_key_with_negation(self) -> None:
        """Test condition where the key is missing and combined with negation."""
        q = ~Q(x=1)
        self.assertTrue(q.evaluate({}))  # Missing 'x' implies x != 1
        self.assertFalse(q.evaluate({"x": 1}))

    def test_condition_with_list_values(self) -> None:
        """Test condition where the value is a list (if supported)."""
        q = Q(tags__contains="python")
        self.assertTrue(q.evaluate({"tags": ["python", "django"]}))
        self.assertFalse(q.evaluate({"tags": ["java", "c++"]}))

    def test_circular_reference(self) -> None:
        """Test for potential circular references in nested Q objects."""
        q1 = Q(x=1)
        q2 = Q(y=2)
        q1._conditions.append(q2)
        q2._conditions.append(q1)  # Create a circular reference
        with self.assertRaises(RecursionError):
            q1.evaluate({"x": 1, "y": 2})

    def test_deeply_nested_negations(self) -> None:
        """Test evaluating a deeply nested structure with multiple negations."""
        q = Q(x=1)
        for _ in range(10):
            q = ~q
        self.assertTrue(q.evaluate({"x": 1}))
        self.assertFalse(q.evaluate({"x": 2}))

    def test_combination_of_all_ops(self) -> None:
        """Test combining AND, OR, and NOT in a single expression."""
        q = (Q(x=1) & ~Q(y=2)) | (Q(z=3) & Q(w=4)) | ~Q(v=5)
        self.assertTrue(q.evaluate({"x": 1, "y": 3}))
        self.assertTrue(q.evaluate({"z": 3, "w": 4}))
        self.assertTrue(q.evaluate({"v": 6}))
        self.assertTrue(q.evaluate({"x": 1, "y": 2}))
        self.assertFalse(q.evaluate({"v": 5}))

    def test_empty_q_combined_with_contradictory_condition(self) -> None:
        """Test combining an empty Q with a contradictory condition."""
        q = Q() & Q(x=1) & Q(x=2)
        self.assertFalse(q.evaluate({"x": 1}))
        self.assertFalse(q.evaluate({"x": 2}))
        self.assertFalse(q.evaluate({"x": 1, "x": 2}))

    def test_q_with_invalid_operator(self) -> None:
        """Test behavior when an invalid operator is used in a condition."""
        q = Q()
        q._conditions.append(("x", "INVALID_OP", 1))  # Manually adding invalid operator
        with self.assertRaises(AttributeError):
            q.evaluate({"x": 1})

    def test_q_evaluate_with_additional_parameters(self) -> None:
        """Test the evaluate method with additional parameters (if supported)."""
        q = Q(x=1)
        self.assertTrue(q.evaluate({"x": 1}, extra_param=True))

    def test_q_with_in_operator(self) -> None:
        """Test condition using the 'in' operator (if supported)."""
        q = Q(x__in=[1, 2, 3])
        self.assertTrue(q.evaluate({"x": 2}))
        self.assertFalse(q.evaluate({"x": 4}))

    def test_q_with_greater_than_operator(self) -> None:
        """Test condition using the 'greater than' operator (if supported)."""
        q = Q(x__gt=5)
        self.assertTrue(q.evaluate({"x": 6}))
        self.assertFalse(q.evaluate({"x": 5}))



if __name__ == "__main__":
    unittest.main()
