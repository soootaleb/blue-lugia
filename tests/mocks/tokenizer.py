import tiktoken


class Tokenizer(tiktoken.Encoding):
    def __init__(self, *args, **kwargs) -> None:
        pass

    def encode(
        self,
        text: str,
        *args,
        **kwargs,
    ) -> list[int]:
        return [ord(c) for c in text]

    def decode(self, tokens: list[int], errors: str = "replace") -> str:
        return "".join([chr(c) for c in tokens])
