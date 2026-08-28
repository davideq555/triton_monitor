"""Tests para el formateador JSON forense (Integrante 3)."""
import json
import logging
import sys
import pytest
from datetime import datetime, timezone

import httpx

from triton_telemetry.logging_engine import AsyncJSONFormatter
from triton_telemetry.exceptions import (
    ProviderTimeoutError,
    CorruptedPayloadError,
    NetworkPeeringError,
)


class TestAsyncJSONFormatterBasic:
    """Tests básicos del formateador JSON."""

    def setup_method(self):
        self.formatter = AsyncJSONFormatter()

    def _make_record(self, msg="test", level=logging.INFO, exc_info=None, extra=None):
        record = logging.LogRecord(
            name="triton_monitor",
            level=level,
            pathname="test.py",
            lineno=1,
            msg=msg,
            args=(),
            exc_info=exc_info,
        )
        if extra:
            for k, v in extra.items():
                setattr(record, k, v)
        return record

    def test_output_is_valid_json(self):
        record = self._make_record("Hello Triton")
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_timestamp_is_iso8601_utc_with_z_suffix(self):
        """HARD GATE: timestamp debe ser ISO 8601 UTC con sufijo 'Z'."""
        record = self._make_record()
        output = self.formatter.format(record)
        parsed = json.loads(output)

        ts = parsed["timestamp"]
        assert ts.endswith("Z"), f"Timestamp debe terminar en 'Z', obtuvo: {ts}"
        # Verificar que es parseable como datetime UTC
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert dt.tzinfo is not None

    def test_contains_required_fields(self):
        record = self._make_record()
        output = self.formatter.format(record)
        parsed = json.loads(output)

        required = ["timestamp", "level", "logger", "message", "process", "threadName"]
        for field in required:
            assert field in parsed, f"Falta campo requerido: {field}"

    def test_level_is_correct(self):
        for level, name in [(logging.DEBUG, "DEBUG"), (logging.INFO, "INFO"),
                            (logging.WARNING, "WARNING"), (logging.ERROR, "ERROR")]:
            record = self._make_record(level=level)
            output = self.formatter.format(record)
            parsed = json.loads(output)
            assert parsed["level"] == name

    def test_message_content_preserved(self):
        record = self._make_record("Triton cloud monitoring active")
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "Triton cloud monitoring active"

    def test_extra_metadata_captured(self):
        """Metadatos inyectados vía 'extra' deben aparecer en el JSON."""
        record = self._make_record(extra={"provider": "AWS", "status_code": 200})
        output = self.formatter.format(record)
        parsed = json.loads(output)

        assert parsed["provider"] == "AWS"
        assert parsed["status_code"] == 200

    def test_private_fields_excluded(self):
        """Campos que empiezan con _ no deben incluirse."""
        record = self._make_record(extra={"_internal": "secret", "public": "visible"})
        output = self.formatter.format(record)
        parsed = json.loads(output)

        assert "_internal" not in parsed
        assert parsed.get("public") == "visible"


class TestAsyncJSONFormatterExceptions:
    """Tests de serialización de excepciones."""

    def setup_method(self):
        self.formatter = AsyncJSONFormatter()

    def _make_record_with_exc(self, exc):
        try:
            raise exc
        except type(exc):
            exc_info = sys.exc_info()

        return logging.LogRecord(
            name="triton_monitor",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="error occurred",
            args=(),
            exc_info=exc_info,
        )

    def test_simple_exception_serialization(self):
        record = self._make_record_with_exc(ValueError("test error"))
        output = self.formatter.format(record)
        parsed = json.loads(output)

        assert "exception" in parsed
        exc_data = parsed["exception"]
        assert exc_data["type"] == "ValueError"
        assert "test error" in exc_data["message"]

    def test_triton_exception_with_notes(self):
        """Las notas de add_note() deben aparecer en la serialización."""
        err = ProviderTimeoutError("timeout")
        err.add_note("Provider: AWS")
        err.add_note("Limit: 1.0s")

        record = self._make_record_with_exc(err)
        output = self.formatter.format(record)
        parsed = json.loads(output)

        notes = parsed["exception"]["notes"]
        assert "Provider: AWS" in notes
        assert "Limit: 1.0s" in notes

    def test_exception_cause_chain_serialized(self):
        """El encadenamiento 'raise ... from' debe serializar la causa."""
        try:
            try:
                raise httpx.TimeoutException("original")
            except httpx.TimeoutException as orig:
                raise ProviderTimeoutError("wrapped") from orig
        except ProviderTimeoutError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="triton_monitor",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="error",
            args=(),
            exc_info=exc_info,
        )
        output = self.formatter.format(record)
        parsed = json.loads(output)

        exc_data = parsed["exception"]
        assert exc_data["type"] == "ProviderTimeoutError"
        assert "cause" in exc_data
        assert exc_data["cause"]["type"] == "TimeoutException"

    def test_exception_group_recursive_serialization(self):
        """ExceptionGroups anidados deben serializarse recursivamente."""
        inner_errors = [
            ProviderTimeoutError("timeout AWS"),
            CorruptedPayloadError("corrupt GCP"),
        ]
        inner_errors[0].add_note("Provider: AWS")

        try:
            raise ExceptionGroup("multi-failure", inner_errors)
        except ExceptionGroup:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="triton_monitor",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="group error",
            args=(),
            exc_info=exc_info,
        )
        output = self.formatter.format(record)
        parsed = json.loads(output)

        exc_data = parsed["exception"]
        assert exc_data["type"] == "ExceptionGroup"
        assert "sub_exceptions" in exc_data
        assert len(exc_data["sub_exceptions"]) == 2

        # Verificar que las sub-excepciones tienen sus tipos
        sub_types = {s["type"] for s in exc_data["sub_exceptions"]}
        assert "ProviderTimeoutError" in sub_types
        assert "CorruptedPayloadError" in sub_types

    def test_nested_exception_group(self):
        """ExceptionGroups dentro de ExceptionGroups deben serializarse."""
        inner_group = ExceptionGroup("inner", [ValueError("v1"), TypeError("t1")])
        outer_group = ExceptionGroup("outer", [inner_group, RuntimeError("r1")])

        try:
            raise outer_group
        except ExceptionGroup:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="triton_monitor",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="nested",
            args=(),
            exc_info=exc_info,
        )
        output = self.formatter.format(record)
        parsed = json.loads(output)

        exc_data = parsed["exception"]
        assert exc_data["type"] == "ExceptionGroup"
        assert len(exc_data["sub_exceptions"]) == 2
