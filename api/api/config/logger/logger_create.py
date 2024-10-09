import json
import logging
import sys
import time
from datetime import date, datetime, timezone
from typing import Any, List, Literal, Tuple
from uuid import UUID

import click
from pydantic import BaseModel

#
# there's no way to get the "extra" dict from the """logger.info("...", extra={ ... })"""
# we need to manually lookup the non-reserved attributes because they are merged into the log record
#
# https://github.com/madzak/python-json-logger/blob/838939b72a521f07eebab6d67dbeeb9041f29130/src/pythonjsonlogger/jsonlogger.py#L20
# https://github.com/open-telemetry/opentelemetry-python/blob/606d535551c14fbc5a68921d485be35ddb5a6ce2/opentelemetry-sdk/src/opentelemetry/sdk/_logs/__init__.py#L277
# https://discuss.python.org/t/preserve-unpacked-extra-in-logrecord/15630
#
RESERVED_ATTRS: Tuple[str, ...] = (
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
)


TRACE_LOG_LEVEL = 5


class LogFormatter(logging.Formatter):
    level_name_colors = {
        TRACE_LOG_LEVEL: lambda level_name: click.style(str(level_name), fg="blue"),
        logging.DEBUG: lambda level_name: click.style(str(level_name), fg="cyan"),
        logging.INFO: lambda level_name: click.style(str(level_name), fg="green"),
        logging.WARNING: lambda level_name: click.style(str(level_name), fg="yellow"),
        logging.ERROR: lambda level_name: click.style(str(level_name), fg="red"),
        logging.CRITICAL: lambda level_name: click.style(
            str(level_name), fg="bright_red"
        ),
    }

    def color_level_name(self, level_name: str, level_no: int) -> str:
        def default(level_name: str) -> str:
            return str(level_name)

        func = self.level_name_colors.get(level_no, default)
        return func(level_name)

    def format(self, record):
        seperator = " " * (9 - len(record.levelname))
        levelname = self.color_level_name(record.levelname, record.levelno)
        timestamp = self.formatTime(record)

        log_message = (
            f"{levelname}:{seperator}{timestamp}{' ' * 2}{record.getMessage()}"
        )

        if record.exc_info:
            return f"{log_message}{record.exc_info}"

        return log_message

    def formatTime(self, record):
        """LogFormatter timestamp is in local time"""
        return (
            datetime.fromtimestamp(record.created, timezone.utc)
            .astimezone()
            .strftime("%H:%M:%S")
        )


class JSONFormatter(logging.Formatter):
    converter = time.gmtime

    def format(self, record):
        log_record: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "pathname": f"{record.pathname}:{record.lineno}",
            "timestamp": self.formatTime(record),
        }

        for attr in record.__dict__:
            if attr not in RESERVED_ATTRS:
                if log_record.get("extra") is None:
                    log_record["extra"] = {}
                log_record["extra"][attr] = self.make_serializable(
                    getattr(record, attr)
                )

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record, default=str)

    def formatTime(self, record):
        """JSONFormatter timestamp is in UTC ISO 8601 format"""
        return datetime.fromtimestamp(record.created, timezone.utc).isoformat(
            sep="T", timespec="milliseconds"
        )

    def make_serializable(self, obj):
        """Convert object to JSON serializable format."""
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self.make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self.make_serializable(item) for item in obj]
        elif isinstance(obj, bytes):
            try:
                return json.loads(obj.decode())
            except Exception:
                return obj.decode()
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, BaseModel):
            return obj.model_dump()
        else:
            try:
                data = dict(obj)
            except Exception as e:
                errors: List[Exception] = []
                errors.append(e)
                try:
                    data = vars(obj)
                except Exception as e:
                    errors.append(e)
                    raise ValueError(errors) from e
            return self.make_serializable(data)


def logger_create(
    logger_name: str | Literal["root"],
    as_json: bool = False,
    handler_filters: List[logging.Filter] = [],
    logger_level: str = logging.getLevelName(logging.INFO),
):
    application_logger = logging.getLogger(
        name=None if logger_name == "root" else logger_name,
    )
    application_logger.setLevel(logger_level)

    logger_handler = logging.StreamHandler(stream=sys.stderr)

    if as_json:
        logger_handler.setFormatter(JSONFormatter())
    else:
        logger_handler.setFormatter(LogFormatter())

    for filter in handler_filters:
        logger_handler.addFilter(filter)

    application_logger.addHandler(logger_handler)

    if logger_name == "root":
        application_logger.debug("created root logger")
    else:
        application_logger.debug(f"created logger {logger_name}")

    return application_logger
