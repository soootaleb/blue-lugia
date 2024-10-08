class MessageFormatError(ValueError):
    pass


class MessageRemoteError(Exception):
    pass


class ChatMessageManagerError(Exception):
    pass


class ChatFileManagerError(Exception):
    pass


class ChatParseError(Exception):
    pass


class ConfigError(ValueError):
    pass


class ParserError(Exception):
    pass


class LanguageModelManagerError(Exception):
    pass


class QError(Exception):
    pass


class StateError(Exception):
    pass
