"""Tests para el pipeline de logging no bloqueante (Integrante 4)."""
import json
import gzip
import logging
import logging.handlers
import pytest
from pathlib import Path

from triton_telemetry.logging_engine import (
    NonBlockingLoggingEngine,
    AsyncJSONFormatter,
    get_async_logger,
)


class TestNonBlockingEngineSetup:
    """Tests de configuración del motor de logging."""

    def test_engine_creates_log_directory(self, tmp_path):
        log_file = tmp_path / "subdir" / "test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        assert log_file.parent.exists()
        engine.start()
        engine.stop()

    def test_rotating_handler_max_bytes(self, tmp_path):
        """RotatingFileHandler debe tener maxBytes=2MB."""
        log_file = tmp_path / "test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        assert engine.rotating_handler.maxBytes == 2 * 1024 * 1024
        engine.start()
        engine.stop()

    def test_rotating_handler_backup_count(self, tmp_path):
        """RotatingFileHandler debe tener backupCount=3."""
        log_file = tmp_path / "test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        assert engine.rotating_handler.backupCount == 3
        engine.start()
        engine.stop()

    def test_default_formatter_is_async_json(self, tmp_path):
        """El formatter por defecto debe ser AsyncJSONFormatter."""
        log_file = tmp_path / "test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        assert isinstance(engine.rotating_handler.formatter, AsyncJSONFormatter)
        engine.start()
        engine.stop()

    def test_custom_formatter_accepted(self, tmp_path):
        """Se debe poder pasar un formatter custom."""
        log_file = tmp_path / "test.log"
        custom = logging.Formatter("%(message)s")
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file), formatter=custom)
        assert engine.rotating_handler.formatter is custom
        engine.start()
        engine.stop()


class TestQueuePipeline:
    """Tests de QueueHandler + QueueListener."""

    def test_queue_handler_is_used(self, tmp_path):
        """El logger debe usar QueueHandler (no handlers de archivo directos)."""
        log_file = tmp_path / "test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        assert isinstance(engine.queue_handler, logging.handlers.QueueHandler)
        engine.start()
        engine.stop()

    def test_listener_processes_queued_messages(self, tmp_path):
        """Los mensajes encolados deben procesarse al hacer stop()."""
        log_file = tmp_path / "pipeline_test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        engine.start()

        test_logger = logging.getLogger("test_pipeline")
        test_logger.handlers = [engine.queue_handler]
        test_logger.setLevel(logging.DEBUG)
        test_logger.propagate = False

        test_logger.info("Test message through pipeline")
        engine.stop()  # Flush

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message through pipeline" in content

    def test_no_direct_file_descriptor_access(self, tmp_path):
        """HARD GATE: El logger externo NO debe tener RotatingFileHandler directo."""
        logger, engine = get_async_logger("test_no_concurrent_fd")
        try:
            for handler in logger.handlers:
                assert not isinstance(handler, logging.handlers.RotatingFileHandler), \
                    "El logger no debe tener RotatingFileHandler directo"
        finally:
            engine.stop()

    def test_multiple_messages_processed_in_order(self, tmp_path):
        """Múltiples mensajes deben procesarse en orden."""
        log_file = tmp_path / "order_test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        engine.start()

        test_logger = logging.getLogger("test_order")
        test_logger.handlers = [engine.queue_handler]
        test_logger.setLevel(logging.DEBUG)
        test_logger.propagate = False

        for i in range(5):
            test_logger.info(f"Message {i}")

        engine.stop()

        content = log_file.read_text()
        for i in range(5):
            assert f"Message {i}" in content


class TestGzipRotation:
    """Tests de compresión gzip en rotación."""

    def test_gzip_namer_appends_extension(self, tmp_path):
        """El namer debe agregar extensión .gz."""
        log_file = tmp_path / "test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        namer = engine.rotating_handler.namer
        assert namer("test.log.1") == "test.log.1.gz"
        engine.start()
        engine.stop()

    def test_gzip_rotator_compresses_file(self, tmp_path):
        """El rotator debe comprimir a .gz."""
        source = tmp_path / "source.log"
        dest = tmp_path / "dest.log.gz"
        source.write_text("test log data " * 100)

        log_file = tmp_path / "test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        rotator = engine.rotating_handler.rotator

        rotator(str(source), str(dest))

        assert dest.exists(), "El archivo .gz debe crearse"
        with gzip.open(dest, "rt") as f:
            content = f.read()
        assert "test log data" in content
        engine.start()
        engine.stop()

    def test_gzip_rotator_removes_original(self, tmp_path):
        """El rotator debe eliminar el archivo plano original."""
        source = tmp_path / "source.log"
        dest = tmp_path / "dest.log.gz"
        source.write_text("data")

        log_file = tmp_path / "test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        rotator = engine.rotating_handler.rotator

        rotator(str(source), str(dest))

        assert not source.exists(), "El archivo original debe eliminarse"
        engine.start()
        engine.stop()

    def test_gzip_compression_level(self, tmp_path):
        """La compresión debe usar nivel 9 (máxima compresión)."""
        source = tmp_path / "source.log"
        dest = tmp_path / "dest.log.gz"
        # Datos repetitivos para verificar compresión
        source.write_text("ABCDEFGHIJ" * 1000)

        log_file = tmp_path / "test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        rotator = engine.rotating_handler.rotator

        rotator(str(source), str(dest))

        # El archivo comprimido debe ser significativamente menor
        original_size = len("ABCDEFGHIJ" * 1000)
        compressed_size = dest.stat().st_size
        assert compressed_size < original_size / 2, "La compresión debe reducir el tamaño"
        engine.start()
        engine.stop()


class TestGetAsyncLogger:
    """Tests de la función factory get_async_logger."""

    def test_returns_logger_and_engine(self, tmp_path):
        logger, engine = get_async_logger("test_factory")
        try:
            assert isinstance(logger, logging.Logger)
            assert isinstance(engine, NonBlockingLoggingEngine)
        finally:
            engine.stop()

    def test_logger_has_queue_handler(self, tmp_path):
        logger, engine = get_async_logger("test_factory_handler")
        try:
            assert len(logger.handlers) == 1
            assert isinstance(logger.handlers[0], logging.handlers.QueueHandler)
        finally:
            engine.stop()

    def test_logger_does_not_propagate(self, tmp_path):
        logger, engine = get_async_logger("test_no_propagate")
        try:
            assert logger.propagate is False
        finally:
            engine.stop()
