"""Centralized logging configuration for Barista AI."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support."""
    
    COLORS = {
        'DEBUG': '\033[96m',
        'INFO': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[91m\033[1m'
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None,
                 log_to_console: bool = True, max_file_size: int = 10485760,
                 backup_count: int = 5) -> None:
    """Setup centralized logging configuration."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    file_formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
    console_formatter = ColoredFormatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
    
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_file_size, backupCount=backup_count, encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    root_logger.info(f"Logging initialized at {log_level} level")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(name)
