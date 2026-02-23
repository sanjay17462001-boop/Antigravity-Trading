"""
Antigravity Trading — Structured Logging
Console (rich) + rotating file logs with separate loggers per subsystem.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from core.config import get_settings


def setup_logging(log_dir: Optional[Path] = None, level: Optional[str] = None) -> None:
    """
    Initialize the logging system.
    
    Creates loggers:
        antigravity          — root logger
        antigravity.data     — data feeds and storage
        antigravity.strategy — strategy execution
        antigravity.engine   — backtester, executor
        antigravity.broker   — broker API calls
        antigravity.risk     — risk management
        antigravity.events   — event bus
    """
    settings = get_settings()
    log_level = level or settings.logging.level
    log_path = Path(log_dir or settings.logging.log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Root logger
    root = logging.getLogger("antigravity")
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Console handler (human readable)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        "%(asctime)s │ %(levelname)-7s │ %(name)-25s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    console.setFormatter(console_fmt)
    root.addHandler(console)

    # File handler (detailed, rotated)
    file_handler = RotatingFileHandler(
        log_path / "antigravity.log",
        maxBytes=settings.logging.max_file_size_mb * 1024 * 1024,
        backupCount=settings.logging.backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    root.addHandler(file_handler)

    # Separate trade log (for audit trail)
    trade_logger = logging.getLogger("antigravity.trades")
    trade_handler = RotatingFileHandler(
        log_path / "trades.log",
        maxBytes=settings.logging.max_file_size_mb * 1024 * 1024,
        backupCount=settings.logging.backup_count,
        encoding="utf-8",
    )
    trade_handler.setFormatter(file_fmt)
    trade_logger.addHandler(trade_handler)

    root.info("Logging initialized — level=%s, dir=%s", log_level, log_path)


def get_logger(name: str) -> logging.Logger:
    """
    Get a namespaced logger.
    
    Usage:
        logger = get_logger("strategy")  → antigravity.strategy
        logger = get_logger("broker.dhan") → antigravity.broker.dhan
    """
    return logging.getLogger(f"antigravity.{name}")
