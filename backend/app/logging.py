import logging
import sys
import structlog
from structlog.types import EventDict, Processor

def add_severity_level(logger: logging.Logger, name: str, event_dict: EventDict) -> EventDict:
    """Translate standard level names to severity key (for structured log formatting)."""
    level = event_dict.get("level")
    if level:
        event_dict["severity"] = level.upper()
    return event_dict

def setup_logging():
    """Sets up global logging to route through structlog processors."""
    # Reset existing root logging handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_severity_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Use friendly console renderer for local TTY output; use JSON log in non-TTY (production/containers)
    if sys.stdout.isatty():
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
