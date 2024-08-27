from typing import TypeVar, Generic, Type, Any
from pydantic import BaseModel

# This TypeVar now captures any subclass of BaseModel
TableType = TypeVar('TableType', bound=BaseModel)

# A new TypeVar to bind the manager to a specific type
ManagerType = TypeVar('ManagerType', bound='TableManager')

# Define the base class for TableManagers as a generic class
class TableManager(Generic[TableType]):
    def __init__(self, model: Type[TableType]):
        self.model = model

    def all(self) -> str:
        return f"Fetching all records of {self.model.__name__}"

# Metaclass to dynamically type the manager according to the subclass's Meta manager
class TableMeta(type):
    @property
    def objs(cls) -> Any:  # Type Any used here for broader compatibility, will be narrowed in usage
        # Fetch the manager class from the subclass's Meta attribute
        manager_class = getattr(cls.Meta, 'manager', TableManager)
        # The returned manager is instantiated as the specific manager bound to cls
        return manager_class(cls)

# Base table model using the TableMeta metaclass
class Table(BaseModel, metaclass=TableMeta):
    class Config:
        arbitrary_types_allowed = True
        fields = {'objects': {'exclude': True}}

    class Meta:
        manager = TableManager  # Default manager

# Example of a specific manager for specific tables
class SpecificTableManager(TableManager[TableType]):
    def specific_method(self) -> str:
        return "This is a method specific to SpecificTableManager"

# Example of a table subclass using a specific manager
class UserTable(Table):
    class Meta:
        manager = SpecificTableManager

# Example Usage
user_table_manager = UserTable.objs.specific_method()  # Should return the specific manager
print(user_table_manager.all())  # Should work and return the specific type
print(user_table_manager.specific_method())  # Specific to SpecificTableManager
