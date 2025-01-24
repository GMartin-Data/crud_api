"""Test suite for logger configuration."""

import logging
from pathlib import Path

import pytest

from src.config.logger import setup_logger


@pytest.fixture
def temp_log_file(tmp_path: Path) -> Path:
    """Create a temporary log file for testing."""
    return tmp_path / "test.log"


def test_logger_creation() -> None:
    """Test basic logger creation without file handler."""
    logger = setup_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1  # Should have console handler

    # Check handler types
    assert isinstance(logger.handlers[0], logging.StreamHandler)


def test_logger_with_file(temp_log_file: Path) -> None:
    """Test logger creation with file handler."""
    logger = setup_logger(name="test_file_logger", log_file=str(temp_log_file))
    assert len(logger.handlers) == 2

    # Check handler types
    handlers = logger.handlers
    assert any(isinstance(h, logging.StreamHandler) for h in handlers)
    assert any(isinstance(h, logging.handlers.RotatingFileHandler) for h in handlers)


def test_log_message_creation(temp_log_file: Path) -> None:
    """Test actual log message creation and file writing."""
    logger = setup_logger(name="test_message_logger", log_file=str(temp_log_file))
    test_message = "Test log message"
    logger.info(test_message)

    # Check if message was written to file
    assert temp_log_file.exists()
    with open(temp_log_file, "r") as read_file:
        log_content = read_file.read()
        assert test_message in log_content


def test_log_levels() -> None:
    """Test that different log levels work correctly."""
    logger = setup_logger(name="test_levels_logger_1", level=logging.DEBUG)
    assert logger.level == logging.DEBUG

    logger = setup_logger(name="test_levels_logger_2", level=logging.ERROR)
    assert logger.level == logging.ERROR


def test_rotating_file_handler(temp_log_file: Path) -> None:
    """Test rotating file handler configuration."""
    max_bytes = 1_024
    backup_count = 3

    logger = setup_logger(
        name="test_rotation_logger",
        log_file=str(temp_log_file),
        rotation_size=max_bytes,
        backup_count=backup_count,
    )

    # Get the rotating file handler
    handler = next(
        h
        for h in logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    )

    assert handler.maxBytes == max_bytes
    assert handler.backupCount == backup_count


def test_logger_reuse() -> None:
    """Test that getting the same logger name returns the same logger."""
    logger_1 = setup_logger("test_reuse")
    logger_2 = setup_logger("test_reuse")

    assert logger_1 is logger_2
    # Ensure this does not create new handlers
    assert len(logger_1.handlers) == 1
