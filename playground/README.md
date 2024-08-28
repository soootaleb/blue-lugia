

We want a table, a two dimension array of data
Tables can be a SQL table, an Excel sheet, etc... DataFrame seems a cool base class

Tables must have

- [OK] a structure definition => PYDANTIC MODELS
  - fields names
  - fields types
  - (opt) fields descriptions
  - (opt) fields defaults

- a way to be hydrated => MANAGERS API ?
  - from an excel sheet to a table instance
  - from an SQL table to a table instance
  - from a list of dictionaries to a table instance
  - ...

- [OK] a way to be queried => MANAGERS API
  - Q api
  - ...? Pandas api?