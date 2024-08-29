import json
import sqlite3
from typing import Any, Tuple


class DataDriver:
    def decode(self, data: Any) -> Any:
        return data

    def encode(self, data: dict) -> Tuple[Any, tuple]:
        return data, ()


class JSONDriver(DataDriver):
    def decode(self, data: bytes) -> dict | list:
        return json.loads(data) if data else {}

    def encode(self, data: dict) -> Tuple[bytes, tuple]:
        return json.dumps(data.get("_item", {}), ensure_ascii=False, indent=2).encode("utf-8"), ()


class SQLiteDriver(DataDriver):
    def decode(self, data: list[sqlite3.Row]) -> dict | list:
        return list(filter(lambda item: bool(item), map(lambda row: dict(row), data)))

    def encode(self, data: dict) -> Tuple[bytes, tuple]:
        # Get the column names and prepare placeholders
        columns = data.get("_item", {}).keys()
        cols_str = ", ".join(columns)

        # Create placeholders for the column values
        placeholders = ", ".join(["?"] * len(columns))

        # Formulate the SQL query string using placeholders
        sql_query = f"INSERT INTO {data.get('_table', '')} ({cols_str}) VALUES ({placeholders});"

        # Prepare the values tuple to be inserted
        values = tuple(data.get("_item", {}).values())

        return sql_query.encode("utf-8"), values
