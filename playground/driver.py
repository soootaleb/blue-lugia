import json
from typing import Any


class DataDriver:
    def decode(self, data: Any) -> Any:
        return data

    def encode(self, data: Any) -> Any:
        return data


class JSONDriver(DataDriver):
    def decode(self, data: bytes) -> dict | list:
        return json.loads(data) if data else {}

    def encode(self, data: dict) -> Any:
        return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
