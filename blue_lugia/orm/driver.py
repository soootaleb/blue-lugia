import csv
import io
import json
import pickle
import sqlite3
from typing import Any, Tuple

import pandas as pd


class DataDriver:
    def decode(self, data: bytes) -> Any:
        loaded = []
        stream = io.BytesIO(data)
        while True:
            try:
                obj = pickle.load(stream)
                loaded.append(obj)
            except EOFError:
                break
        if len(loaded) == 1:
            return loaded[0]
        else:
            return loaded

    def encode(self, data: dict) -> Tuple[bytes, tuple]:
        return pickle.dumps(data.get("_item", {})), ()


class JSONDriver(DataDriver):
    def decode(self, data: bytes) -> dict | list:
        return json.loads(data) if data else {}

    def encode(self, data: dict) -> Tuple[bytes, tuple]:
        return json.dumps(data.get("_item", {}), ensure_ascii=False, indent=2).encode("utf-8"), ()


class CSVDriver(DataDriver):
    def decode(self, data: bytes) -> dict | list:
        return list(csv.DictReader(data.decode("utf-8").splitlines()))

    def encode(self, data: dict) -> Tuple[bytes, tuple]:
        # Get the column names and prepare placeholders
        columns = data.get("_item", {}).keys()

        # Create a CSV writer object
        with open("temp.csv", "w", newline="") as file:
            csv_writer = csv.DictWriter(file, fieldnames=columns)

        # Write the column names to the CSV file
        csv_writer.writeheader()

        # Write the data to the CSV file
        csv_writer.writerow(data.get("_item", {}))

        with open("temp.csv", "rb") as file:
            return file.read(), ()

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


class ExcelDriver(DataDriver):
    def decode(self, data: bytes) -> dict | list:
        dataframe = pd.read_excel(data, sheet_name=None)
        return {sheet_name: dataframe[sheet_name].where(pd.notna(dataframe[sheet_name]), None).to_dict(orient="records") for sheet_name in dataframe}

    def encode(self, data: dict) -> Tuple[bytes, tuple]:
        pd.DataFrame(data.get("_item", {})).to_excel("temp.xlsx", index=False)
        with open("temp.xlsx", "rb") as file:
            return file.read(), ()
