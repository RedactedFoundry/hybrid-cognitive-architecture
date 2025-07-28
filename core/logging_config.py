# core/logging_config.py

import logging
import sys
import structlog

def setup_logging(log_level: str = "INFO"):
    """
    Configures structured logging for the entire application.

    This function sets up structlog to process all logs from Python's standard
    logging library, ensuring that any log message from any library is
    formatted as a JSON object.

    Args:
        log_level: The minimum log level to output (e.g., "DEBUG", "INFO").
    """
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())
    handler = logging.StreamHandler(sys.stdout)
    root_logger.addHandler(handler) 