import json
from datetime import datetime
from typing import List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from blue_lugia.app import App
from blue_lugia.config import ModuleConfig
from blue_lugia.models import Message
from blue_lugia.state import StateManager


# 1. User model
class User(BaseModel):
    user_id: int = Field(..., title="User ID", description="The unique identifier for a user")
    username: str = Field(..., title="Username", max_length=50, description="The user's username")
    email: str = Field(..., title="Email", max_length=100, description="The user's email address")
    created_at: datetime = Field(default_factory=datetime.utcnow, title="Created At", description="Timestamp of when the user was created")


# 2. Product model
class Product(BaseModel):
    product_id: int = Field(..., title="Product ID", description="The unique identifier for a product")
    name: str = Field(..., title="Product Name", max_length=100, description="The name of the product")
    description: Optional[str] = Field(None, title="Product Description", max_length=500, description="The description of the product")
    price: float = Field(..., title="Product Price", description="The price of the product")
    in_stock: int = Field(..., title="In Stock", description="The number of products currently in stock")


# 3. Order model
class Order(BaseModel):
    order_id: int = Field(..., title="Order ID", description="The unique identifier for an order")
    user_id: int = Field(..., title="User ID", description="The identifier of the user who placed the order")
    product_ids: List[int] = Field(..., title="Product IDs", description="The list of product IDs included in the order")
    total_amount: float = Field(..., title="Total Amount", description="The total amount for the order")
    ordered_at: datetime = Field(default_factory=datetime.utcnow, title="Ordered At", description="Timestamp of when the order was placed")


class TextToSqlQuery(BaseModel):
    """Use this tool to generate an SQL query from a text"""

    query: str = Field(..., title="The generated SQL query")

    def run(self, call_id: str, state: StateManager, extra: dict, *args) -> str:
        return self.query


class TextToSqlStruct(BaseModel):
    """Use this tool to generate a query structure"""

    full_query: str = Field(..., description="The full query string you expect to generate")

    select_fields: Optional[List[str]] = Field(
        default=["*"],
        description="The fields to include in the SELECT clause. This can include fields and aggregation functions."
    )
    conditions: Optional[List[Tuple[str, str, Union[str, int, float]]]] = Field(
        default_factory=list,
        description="Conditions for the WHERE clause, each defined as a tuple (field_name, operator, value)."
    )
    joins: Optional[List[Tuple[str, str, str]]] = Field(
        default_factory=list,
        description="Details of JOIN operations, specified as tuples (table_name, left_key, right_key) to define how tables are joined."
    )
    groups: Optional[List[str]] = Field(
        default_factory=list,
        description="List of field names to be included in the GROUP BY clause."
    )
    havings: Optional[List[Tuple[str, str, Union[str, int, float]]]] = Field(
        default_factory=list,
        description="Conditions for the HAVING clause, each defined as a tuple (aggregated_field, operator, value), used for filtering aggregated data."
    )
    table: str = Field(..., description="The primary table name from which data is retrieved, used in the FROM clause.")


    def run(self, call_id: str, state: StateManager, extra: dict, *args) -> str:
        conditions = ""

        for key, op, val in self.conditions or []:
            if conditions:
                conditions += " AND "
            conditions += f"{key} {op} {val}"

        query = f"""SELECT {','.join(self.select_fields or ["*"])} FROM {self.table}{' '.join([f"JOIN {table} ON {left} = {right}" for table, left, right in self.joins or []])}{' WHERE ' + conditions if conditions else ''}{' GROUP BY ' + ','.join(self.groups) if self.groups else ''}{' HAVING ' + ' AND '.join([f"{key} {op} {val}" for key, op, val in self.havings]) if self.havings else ''}"""

        return query

    @classmethod
    def on_validation_error(cls, call_id: str, arguments: dict, state: StateManager, extra: dict, *args) -> str:
        raise extra.get("validation_error")


def module(state: StateManager[ModuleConfig]) -> None:
    questions = [
        "How many users are there in the database?",
        "What are the names of the products that are currently in stock?",
        "What are the names and prices of all products that cost more than $50 and are currently in stock?",
        "What is the total amount spent by each user on orders?",
        "Which users have placed orders totaling more than $500, and what are the total amounts of their orders?",
        "Which users made purchases in every month of 2023, and for each of those users, what is their average spending per month, considering only months where they made at least 3 purchases? Also, how many distinct products have they purchased in total?"
    ]

    models = [User, Product, Order]

    state.using(state.llm.using("AZURE_GPT_4_TURBO_2024_0409"))

    for question in questions:
        state.last_ass_message.append(f"======== {question} =========")
        for tool in [TextToSqlQuery, TextToSqlStruct]:
            completion = (
                state.context(
                    [
                        Message.SYSTEM("Your role is to query data based on the user demand. It's mandatory that you fullfill every details in the demand, potentially by complexifying the resulting query. You can't return a query that does not answer all user questions and fields"),
                        Message.SYSTEM("Here are the pydantic models that represent the database schema, represented as json schemas:"),
                        Message.SYSTEM("\n\n".join([json.dumps(o.model_json_schema(), indent=2) for o in models])),
                        Message.USER(question),
                    ]
                )
                .register([TextToSqlQuery, TextToSqlStruct])
                .complete(tool_choice=tool)
            )

            tools_called, _, _ = state.call(completion)

            if tools_called:
                query = tools_called[0].get("call").get("run")
                state.last_ass_message.append(f"**{tool.__name__}**")
                state.last_ass_message.append(query)
            else:
                state.last_ass_message.append(f"{tool.__name__} Not Called")


app = App("Petal").threaded(False).of(module)  # .listen()
