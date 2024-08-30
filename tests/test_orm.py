import unittest

from pydantic import Field

from blue_lugia.models.query import Q
from blue_lugia.orm.model import Model


class Memory(Model):
    message: str = Field(...)
    valid: bool = Field(...)
    price: int = Field()


class TestMessage(unittest.TestCase):
    def test_default(self) -> None:
        Memory.objects.create(Memory(message="M11", valid=True, price=10))
        Memory.objects.create(Memory(message="M20", valid=False, price=10))
        Memory.objects.create(Memory(message="M30", valid=True, price=50))

        self.assertEqual(len(Memory.objects.filter()), 3)
        self.assertEqual(len(Memory.objects.filter(Q(message__endswith="0"))), 2)
        self.assertEqual(len(Memory.objects.filter((Q(message__endswith="0") | Q(message__endswith="1")) & Q(price__lte=10))), 2)


if __name__ == "__main__":
    unittest.main()
