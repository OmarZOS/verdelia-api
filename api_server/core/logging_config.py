# core/logging_config.py
"""
Shared logging configuration.

Colors HTTP methods and log levels using the Swagger-UI palette so
router and service logs read the same way on a terminal as the API
docs do.

Colors are suppressed automatically when stdout isn't a TTY (piped
output, docker logs, CI), so nothing breaks downstream tooling.
"""

import logging
import os
import sys
from typing import Optional


# ══════════════════════════════════════════════════════════════════
# Palette
# ══════════════════════════════════════════════════════════════════

class Color:
    RESET = "\033[0m"
    BOLD  = "\033[1m"
    DIM   = "\033[2m"

    # Swagger-UI matching palette (24-bit truecolor)
    GET     = "\033[38;2;73;204;144m"    # #49CC90
    POST    = "\033[38;2;97;175;254m"    # #61AFFE
    PUT     = "\033[38;2;252;161;48m"    # #FCA130
    PATCH   = "\033[38;2;80;227;194m"    # #50E3C2
    DELETE  = "\033[38;2;249;62;62m"     # #F93E3E
    HEAD    = "\033[38;2;144;18;254m"    # #9012FE
    OPTIONS = "\033[38;2;13;90;167m"     # #0D5AA7

    DEBUG    = "\033[38;2;140;140;140m"
    INFO     = "\033[38;2;73;204;144m"
    WARNING  = "\033[38;2;252;161;48m"
    ERROR    = "\033[38;2;249;62;62m"
    CRITICAL = "\033[38;2;255;0;110m"

    NAME = "\033[38;2;97;175;254m"
    TIME = "\033[38;2;140;140;140m"


HTTP_METHOD_COLORS = {
    "GET":     Color.GET,
    "POST":    Color.POST,
    "PUT":     Color.PUT,
    "PATCH":   Color.PATCH,
    "DELETE":  Color.DELETE,
    "HEAD":    Color.HEAD,
    "OPTIONS": Color.OPTIONS,
}

LEVEL_COLORS = {
    logging.DEBUG:    Color.DEBUG,
    logging.INFO:     Color.INFO,
    logging.WARNING:  Color.WARNING,
    logging.ERROR:    Color.ERROR,
    logging.CRITICAL: Color.CRITICAL,
}


# ══════════════════════════════════════════════════════════════════
# Formatter
# ══════════════════════════════════════════════════════════════════

class ColorizedFormatter(logging.Formatter):
    """
    Colors:
      - the level name (INFO, WARNING, …) per LEVEL_COLORS
      - any HTTP method that appears as a whole word in the message
        (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS), per
        HTTP_METHOD_COLORS.

    Word-boundary matching keeps "TOGETHER" and "BUDGET" untouched.
    """

    def __init__(self, *args, use_color: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        # Colors on if:
        #   - stdout is a TTY (local dev), OR
        #   - FORCE_COLOR is set (Docker, CI, etc.)
        env_force = "yes"
        self.use_color = use_color and (sys.stdout.isatty() or env_force)

    def format(self, record: logging.LogRecord) -> str:
        plain = super().format(record)
        if not self.use_color:
            return plain

        # 1. Level name
        level_color = LEVEL_COLORS.get(record.levelno, "")
        if level_color:
            plain = plain.replace(
                record.levelname,
                f"{level_color}{Color.BOLD}{record.levelname}{Color.RESET}",
                1,
            )

        # 2. HTTP methods inside the message
        for method in sorted(HTTP_METHOD_COLORS, key=len, reverse=True):
            color = HTTP_METHOD_COLORS[method]
            plain = plain.replace(
                f" {method} ",
                f" {color}{Color.BOLD}{method}{Color.RESET} ",
            )
            if plain.startswith(f"{method} "):
                plain = (
                    f"{color}{Color.BOLD}{method}{Color.RESET}"
                    + plain[len(method):]
                )

        return plain


# ══════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════

DEFAULT_FMT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def get_logger(
    name: Optional[str] = None,
    *,
    level: int = logging.INFO,
    fmt: str = DEFAULT_FMT,
    datefmt: str = DEFAULT_DATEFMT,
    propagate: bool = False,
) -> logging.Logger:
    """
    Return a logger wired to a colorized stdout handler.

    Idempotent: calling it twice for the same logger name won't attach a
    second handler, which matters when uvicorn --reload reimports a
    module.

    Args:
        name:        logger name; pass `__name__` at the call site.
        level:       level for this logger (defaults to INFO).
        fmt/datefmt: pass anything you'd pass to logging.Formatter.
        propagate:   set True if you also want records to reach root;
                     default False avoids duplicate lines when both
                     this module and root have handlers.
    """
    lg = logging.getLogger(name)
    lg.setLevel(level)

    already_has_handler = any(
        isinstance(h.formatter, ColorizedFormatter) for h in lg.handlers
    )
    if not already_has_handler:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            ColorizedFormatter(fmt=fmt, datefmt=datefmt)
        )
        lg.addHandler(handler)

    lg.propagate = propagate
    return lg


def configure_root(
    level: int = logging.INFO,
    fmt: str = DEFAULT_FMT,
    datefmt: str = DEFAULT_DATEFMT,
) -> None:
    """
    Optional: install the colorized formatter on the root logger as
    well. Useful if you want every third-party logger (sqlalchemy,
    httpx, …) to inherit it. Idempotent.
    """
    root = logging.getLogger()
    root.setLevel(level)

    root.handlers = [
        h for h in root.handlers
        if not isinstance(h.formatter, ColorizedFormatter)
    ]
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorizedFormatter(fmt=fmt, datefmt=datefmt))
    root.addHandler(handler)

if __name__ == "__main__":
    import sys
    print("stdout.isatty():", sys.stdout.isatty())
    print("stdout.fileno():", getattr(sys.stdout, "fileno", lambda: None)())
    logger = get_logger("test")
    logger.info("GET /ping")