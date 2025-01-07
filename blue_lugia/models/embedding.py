from typing import Any

from blue_lugia.models.model import Model


class Embedding(list[float], Model):
    def __init__(self, *args: list[Any], **kwargs: Any) -> None:
        list.__init__(self, *args)  # type: ignore
        Model.__init__(self, **kwargs)


class EmbeddingList(list[Embedding], Model):
    def __init__(self, *args: list[Any], **kwargs: Any) -> None:
        list.__init__(self, *args)  # type: ignore
        Model.__init__(self, **kwargs)
