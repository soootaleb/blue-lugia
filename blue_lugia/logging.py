import logging


class DefaultFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_msg = super().format(record)
        # Split the log message into parts
        parts = log_msg.split(" - ")
        timestamp = parts[0]
        name_parts = parts[1].split(".")
        level = parts[2]
        message = parts[3]

        # Format the logger's name with proper indentation
        formatted_name = f"{name_parts[0]}"
        for part in name_parts[1:]:
            formatted_name += f"\n    {part}"

        # Combine the parts with the desired formatting
        formatted_message = f"{timestamp} - {formatted_name} - {level:<7} - {message}"
        return formatted_message


class ExplainFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return super().format(record)
