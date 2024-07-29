import json
from typing import Any


class Store(dict[str, Any]):
    def set(self, key: str, value: Any) -> "Store":
        self[key] = value
        return self

    def json(self, indent: int = 2) -> str:
        return json.dumps(self, indent=indent)
