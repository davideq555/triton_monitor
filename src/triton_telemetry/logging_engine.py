import gzip
import json
import logging
import logging.handlers
import os
import queue
import shutil
import traceback
from datetime import UTC, datetime
from pathlib import Path


class AsyncJSONFormatter(logging.Formatter):
    """
    Integrante 3: Formateador JSON Forense para el Proyecto Tritón.
    Traduce la estructura nativa del LogRecord en un string JSON serializado,
    soporta serialización recursiva de ExceptionGroups y trazas complejas.
    """

    def _format_exception_recursively(self, exc_info):
        if not exc_info:
            return None

        exc_type, exc_value, exc_tb = exc_info

        error_data = {
            "type": exc_type.__name__ if exc_type else None,
            "message": str(exc_value),
            "notes": getattr(exc_value, "__notes__", []),
            "traceback": "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        }

        # Soporte para ExceptionGroups (Python 3.11+)
        if hasattr(exc_value, "exceptions"):
            error_data["sub_exceptions"] = [
                self._format_exception_recursively((type(sub_exc), sub_exc, sub_exc.__traceback__))
                for sub_exc in exc_value.exceptions
            ]

        if exc_value and exc_value.__cause__:
            error_data["cause"] = self._format_exception_recursively(
                (type(exc_value.__cause__), exc_value.__cause__, exc_value.__cause__.__traceback__)
            )

        return error_data

    def format(self, record: logging.LogRecord) -> str:
        # Timestamp ISO 8601 UTC estricto con sufijo 'Z'
        dt_utc = datetime.fromtimestamp(record.created, tz=UTC)
        timestamp_str = dt_utc.isoformat().replace("+00:00", "Z")

        log_data = {
            "timestamp": timestamp_str,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "process": record.process,
            "threadName": record.threadName,
            "taskName": getattr(record, "taskName", None),
            "module": record.module,
            "line": record.lineno
        }

        standard_keys = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "taskName"
        }

        # Mapeo dinámico de 'extra' omitiendo propiedades privadas (_)
        for key, value in record.__dict__.items():
            if key not in standard_keys and not key.startswith('_'):
                log_data[key] = value

        if record.exc_info:
            log_data["exception"] = self._format_exception_recursively(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class NonBlockingLoggingEngine:
    """
    Integrante 4 / Integración: Motor de logging asíncrono y no bloqueante
    que utiliza el AsyncJSONFormatter del Integrante 3.
    """

    def __init__(self, log_file_path="logs/app.log", formatter=None):
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

        self.log_queue = queue.Queue(-1)
        self.rotating_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_file_path,
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )

        if formatter is None:
            formatter = AsyncJSONFormatter()

        self.rotating_handler.setFormatter(formatter)
        self._setup_gzip_rotation()

        self.queue_handler = logging.handlers.QueueHandler(self.log_queue)
        self.listener = logging.handlers.QueueListener(
            self.log_queue, self.rotating_handler, respect_handler_level=True
        )

    def _setup_gzip_rotation(self):
        def rotator(source, dest):
            with open(source, "rb") as f_in:
                with gzip.open(dest, "wb", compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(source)

        def namer(default_name):
            return default_name + ".gz"

        self.rotating_handler.rotator = rotator
        self.rotating_handler.namer = namer

    def start(self):
        self.listener.start()

    def stop(self):
        self.listener.stop()


def get_async_logger(name="AsyncPipelineLogger", formatter=None):
    engine = NonBlockingLoggingEngine(formatter=formatter)
    engine.start()

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(engine.queue_handler)
    logger.propagate = False

    return logger, engine
