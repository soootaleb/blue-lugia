from typing import Any, List

from blue_lugia.models.model import Model


class Embedding(List[float], Model):
    def __init__(self, *args: list[Any], **kwargs: Any) -> None:
        list.__init__(self, *args) # type: ignore
        Model.__init__(self, **kwargs)


class EmbeddingList(List[Embedding], Model):
    def __init__(self, *args: list[Any], **kwargs: Any) -> None:
        list.__init__(self, *args) # type: ignore
        Model.__init__(self, **kwargs)
