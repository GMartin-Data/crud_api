"""Module devoted to global logger setup."""

from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys


class CustomFormatter(logging.Formatter):
    """Formatter adding colors to log in console output."""

    COLORS = {
        logging.DEBUG: "\x1b[38;21m",  # Grey
        logging.INFO: "\x1b[38;5;39m",  # Blue
        logging.WARNING: "\x1b[38;5;226m",  # Yellow
        logging.ERROR: "\x1b[38;5;196m",  # Red
        logging.CRITICAL: "\x1b[31;1m",  # Bold Red
    }
    RESET = "\x1b[0m"

    def __init__(self) -> None:
        """Initialize formatter with specific format."""
        super().__init__()
        self.fmt = (
            "%(asctime)s | %(module)s:%(lineno)d | %(funcName)s| "
            "%(levelname)-8s | %(message)s"
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors for console output."""
        color = self.COLORS.get(record.levelno)
        formatter = logging.Formatter(color + self.fmt + self.RESET)
        return formatter.format(record)


def setup_logger(
    name: str,
    log_file: str | None = None,
    level: int = logging.INFO,
    rotation_size: int = 5_242_880,  # 5 MB
    backup_count: int = 5,
) -> logging.Logger:
    """Set up and configure a logger instance.

    Args:
        name: the logger's name
        log_file: optional file for logging
        level: logging level (defaults to logging.INFO)
        rotation_size: size in bytes before log rotation
        backup_count: number of backup files to keep

    Returns:
        configures logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # If logger already exists and has handlers, return it as is
    if logger.handlers:
        return logger

    # Only add handlers if this is a new logger
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)

    # File handler (if log_file is provided)
    if log_file:
        log_path = Path("logs")
        log_path.mkdir(exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path / log_file,
            maxBytes=rotation_size,
            backupCount=backup_count,
        )
        file_formatter = logging.Formatter(
            "%(asctime)s | %(module)s:%(lineno)d | %(funcName)s | "
            + "%(levelname)-8s | %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


# Create default application logger
app_logger = setup_logger(
    name="aw_crud_api",
    log_file=f"app_{datetime.now().strftime('%Y%m%d')}.log",
)
