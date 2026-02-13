"""Lightweight logging helper (console-only)."""

from __future__ import annotations

import logging
import os
from functools import lru_cache


@lru_cache(maxsize=None)
def get_logger(name: str = "firstchild") -> logging.Logger:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)

    return logger


__all__ = ["get_logger"]

