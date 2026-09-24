"""One place to set up logging for the whole project."""

import logging

from src.config import LOG_DIR


def get_logger(name: str) -> logging.Logger:
    """Return a logger that writes to the screen and to logs/pipeline.log."""
    logger = logging.getLogger(name)
    if logger.handlers:  # already set up
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    screen = logging.StreamHandler()
    screen.setFormatter(fmt)
    file = logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8")
    file.setFormatter(fmt)

    logger.addHandler(screen)
    logger.addHandler(file)
    logger.setLevel(logging.INFO)
    return logger
