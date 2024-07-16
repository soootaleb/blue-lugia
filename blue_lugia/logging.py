import logging

from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


class ColorFormatter(logging.Formatter):
    """Custom formatter to add colors to log level names only."""

    COLORS = {
        logging.DEBUG: Fore.BLACK + Style.BRIGHT,
        logging.INFO: Fore.BLUE + Style.BRIGHT,
        logging.WARNING: Fore.YELLOW + Style.BRIGHT,
        logging.ERROR: Fore.RED + Style.BRIGHT,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
    }

    # Define a format that will color only the level name
    def format(self, record: logging.LogRecord) -> str:
        # Preserve the original formatting for the rest of the log message
        original_format = self._fmt
        # Apply color to levelname only
        log_fmt = f"%(asctime)s - %(name)s - {self.COLORS.get(record.levelno, '')}%(levelname)s{Style.RESET_ALL} - %(message)s"

        # Create a new formatter with the customized format
        formatter = logging.Formatter(log_fmt, "%Y-%m-%d %H:%M:%S")
        # Reset format to avoid altering global state
        self._fmt = original_format

        # Return the formatted record
        return formatter.format(record)
