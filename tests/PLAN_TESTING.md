# Plan de Testing — Proyecto Tritón (TP-1)

Plan de pruebas automatizadas organizado por participante, diseñado para validar el desarrollo individual de cada integrante y la integración final del sistema.

---

## Tabla de Contenidos

1. [Configuración del Entorno de Testing](#1-configuración-del-entorno-de-testing)
2. [Estructura de Tests](#2-estructura-de-tests)
3. [Tests por Participante](#3-tests-por-participante)
   - [Integrante 1: Robustez de Entradas y Excepciones](#integrante-1-robustez-de-entradas-y-excepciones)
   - [Integrante 2: Concurrencia y Telemetría Asíncrona](#integrante-2-concurrencia-y-telemetría-asíncrona)
   - [Integrante 3: Formateo JSON Forense](#integrante-3-formateo-json-forense)
   - [Integrante 4: Pipeline No Bloqueante](#integrante-4-pipeline-no-bloqueante)
   - [Integrante 5: Integración CLI y except*](#integrante-5-integración-cli-y-except)
   - [Integrante 6: Simulación de Caos y Forense](#integrante-6-simulación-de-caos-y-forense)
4. [Tests de Hard Gates (Obligatorios)](#4-tests-de-hard-gates-obligatorios)
5. [Tests de Integración End-to-End](#5-tests-de-integración-end-to-end)
6. [Ejecución y Reportes](#6-ejecución-y-reportes)

---

## 1. Configuración del Entorno de Testing

### 1.1. Dependencias de Testing

Agregar al `requirements.txt`:

```txt
# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
respx>=0.21.0          # Mock de httpx para tests deterministas
pytest-cov>=5.0.0      # Cobertura de código
```

### 1.2. Configuración de pytest

Crear `pyproject.toml` (agregar sección):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "unit: Tests unitarios aislados",
    "integration: Tests de integración entre módulos",
    "e2e: Tests end-to-end con APIs reales",
    "chaos: Tests de inyección de caos",
    "hardgate: Tests de hard gates obligatorios",
    "slow: Tests que requieren red real (pueden ser lentos)",
]
filterwarnings = [
    "error",
    "ignore::DeprecationWarning",
]
```

### 1.3. Instalación

```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio respx pytest-cov
```

---

## 2. Estructura de Tests

```
tests/
├── __init__.py
├── conftest.py                    # Fixtures compartidos
├── test_integrante_1/             # Robustez de entradas
│   ├── test_exceptions.py
│   └── test_sanitizer.py
├── test_integrante_2/             # Concurrencia asíncrona
│   ├── test_core_nominal.py
│   ├── test_core_chaos.py
│   └── test_task_group.py
├── test_integrante_3/             # Formateo JSON
│   └── test_json_formatter.py
├── test_integrante_4/             # Pipeline no bloqueante
│   └── test_logging_pipeline.py
├── test_integrante_5/             # CLI e integración
│   ├── test_cli_parser.py
│   └── test_except_handling.py
├── test_hard_gates/               # Hard gates obligatorios
│   └── test_pep765_compliance.py
├── test_integration/              # End-to-end
│   └── test_full_flow.py
└── [chaos/ o forense/]            # Integrante 6 crea aquí sus tests
    ├── test_chaos_suite.py        # (a crear por el Integrante 6)
    └── test_forensic_validator.py # (a crear por el Integrante 6)
```

> **Nota:** El Integrante 6 es responsable de **desarrollar** la suite de tests de caos y el validador forense. Por lo tanto, no existen tests pre-creados para este integrante — sus tests son el entregable en sí mismo. Puede crearlos en `tests/chaos/`, `tests/forense/`, o directamente en `tests/`.

---

## 3. Tests por Participante

### Integrante 1: Robustez de Entradas y Excepciones

**Archivos bajo prueba:** `exceptions.py`, `sanitizer.py`

#### 3.1.1. Tests de Excepciones (`test_exceptions.py`)

```python
"""Tests para el módulo de excepciones semánticas de Triton."""
import pytest
from triton_telemetry.exceptions import (
    TritonError,
    ProviderTimeoutError,
    CorruptedPayloadError,
    NetworkPeeringError,
)


class TestTritonErrorHierarchy:
    """Valida la jerarquía de excepciones del dominio Triton."""

    def test_triton_error_inherits_from_exception(self):
        """HARD GATE: TritonError DEBE heredar de Exception, NUNCA de BaseException."""
        assert issubclass(TritonError, Exception)
        assert not issubclass(TritonError, BaseException) or TritonError is not BaseException

    def test_provider_timeout_inherits_triton_error(self):
        assert issubclass(ProviderTimeoutError, TritonError)

    def test_corrupted_payload_inherits_triton_error(self):
        assert issubclass(CorruptedPayloadError, TritonError)

    def test_network_peering_inherits_triton_error(self):
        assert issubclass(NetworkPeeringError, TritonError)

    def test_triton_error_is_catchable_as_exception(self):
        """Ctrl+C (KeyboardInterrupt) NO debe ser capturado por TritonError."""
        with pytest.raises(KeyboardInterrupt):
            try:
                raise KeyboardInterrupt()
            except TritonError:
                pass  # No debe llegar aquí

    def test_all_subclasses_catchable_as_triton_error(self):
        """Todas las subclases deben capturarse con except TritonError."""
        for exc_class in [ProviderTimeoutError, CorruptedPayloadError, NetworkPeeringError]:
            with pytest.raises(TritonError):
                raise exc_class("test")

    def test_exception_messages_preserved(self):
        err = ProviderTimeoutError("Timeout en AWS")
        assert str(err) == "Timeout en AWS"

    def test_add_note_support(self):
        """Las excepciones deben soportar add_note() para contexto forense."""
        err = ProviderTimeoutError("Timeout")
        err.add_note("Provider: AWS")
        err.add_note("Timeout: 1.0s")
        assert len(err.__notes__) == 2
        assert "Provider: AWS" in err.__notes__
```

#### 3.1.2. Tests de Sanitizer (`test_sanitizer.py`)

```python
"""Tests para los validadores CLI de Triton."""
import argparse
import pytest
from triton_telemetry.sanitizer import parse_timeout, parse_cluster_id


class TestParseTimeout:
    """Valida el sanitizador de timeout [0.1, 5.0]."""

    # Casos válidos
    @pytest.mark.parametrize("value,expected", [
        ("0.1", 0.1),
        ("1.0", 1.0),
        ("2.5", 2.5),
        ("5.0", 5.0),
        ("3.14", 3.14),
    ])
    def test_valid_timeout_values(self, value, expected):
        result = parse_timeout(value)
        assert result == pytest.approx(expected)

    # Casos inválidos — fuera de rango
    @pytest.mark.parametrize("value", [
        "0.05",   # Por debajo del mínimo
        "0.0",
        "-1.0",
        "5.1",
        "10.0",
        "100.0",
    ])
    def test_timeout_out_of_range_raises_argument_type_error(self, value):
        with pytest.raises(argparse.ArgumentTypeError):
            parse_timeout(value)

    # Casos inválidos — no numéricos
    @pytest.mark.parametrize("value", [
        "abc",
        "timeout",
        "",
        "1.2.3",
        "None",
    ])
    def test_non_numeric_timeout_raises_argument_type_error(self, value):
        with pytest.raises(argparse.ArgumentTypeError):
            parse_timeout(value)

    def test_exit_code_2_on_invalid_timeout(self):
        """argparse debe salir con código 2 ante ArgumentTypeError."""
        import subprocess
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS", "-c", "cluster-us-east-01", "-t", "99.0"],
            capture_output=True, text=True
        )
        assert result.returncode == 2


class TestParseClusterId:
    """Valida el sanitizador de cluster_id con regex."""

    # Casos válidos
    @pytest.mark.parametrize("cluster_id", [
        "cluster-us-east-01",
        "cluster-eu-west-99",
        "cluster-ap-south-00",
        "cluster-sa-east-12",
        "cluster-eu-central-05",
    ])
    def test_valid_cluster_ids(self, cluster_id):
        result = parse_cluster_id(cluster_id)
        assert result == cluster_id.lower()

    # Casos inválidos
    @pytest.mark.parametrize("cluster_id", [
        "invalido",
        "cluster-INVALIDO-01",      # Mayúsculas
        "cluster-us-01",            # Falta sub-región
        "cluster-us-east-1",        # Un solo dígito
        "cluster-us-east-001",      # Tres dígitos
        "cluster-123-east-01",      # Números en región
        "CLUSTER-US-EAST-01",       # Todo mayúsculas
        "cluster-us-east-aa",       # Letras en vez de dígitos
        "",
    ])
    def test_invalid_cluster_ids_raise_argument_type_error(self, cluster_id):
        with pytest.raises(argparse.ArgumentTypeError):
            parse_cluster_id(cluster_id)
```

**Comando para ejecutar solo tests del Integrante 1:**
```bash
pytest tests/test_integrante_1/ -v
```

---

### Integrante 2: Concurrencia y Telemetría Asíncrona

**Archivo bajo prueba:** `core.py`

#### 3.2.1. Tests Nominales con Mock (`test_core_nominal.py`)

```python
"""Tests para core.py en modo nominal — usa respx para mockear httpx."""
import pytest
import httpx
import respx
from triton_telemetry.core import (
    query_provider_telemetry,
    scan_all_providers,
    PROVIDER_ENDPOINTS,
)


class TestQueryProviderNominal:
    """Tests de consulta individual en modo nominal."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_aws_nominal_returns_expected_dict(self):
        """AWS nominal debe retornar dict con provider, status, latency_sec, payload_id."""
        respx.get(PROVIDER_ENDPOINTS["AWS"]).mock(
            return_value=httpx.Response(200, json={"id": 1, "title": "test"})
        )
        result = await query_provider_telemetry("AWS", timeout=3.0)
        
        assert result["provider"] == "AWS"
        assert result["status"] == "NOMINAL"
        assert "latency_sec" in result
        assert result["payload_id"] == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_all_three_providers_nominal(self):
        """Los 3 proveedores deben responder correctamente en modo nominal."""
        for provider, post_id in [("AWS", 1), ("Azure", 2), ("GCP", 3)]:
            respx.get(PROVIDER_ENDPOINTS[provider]).mock(
                return_value=httpx.Response(200, json={"id": post_id})
            )
        
        results = await scan_all_providers(["AWS", "Azure", "GCP"], timeout=3.0)
        assert len(results) == 3
        providers_returned = {r["provider"] for r in results}
        assert providers_returned == {"AWS", "Azure", "GCP"}

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_raises_provider_timeout_error(self):
        """Timeout debe lanzar ProviderTimeoutError con notas forenses."""
        from triton_telemetry.exceptions import ProviderTimeoutError
        
        respx.get(PROVIDER_ENDPOINTS["AWS"]).mock(
            side_effect=httpx.TimeoutException("Connection timed out")
        )
        
        with pytest.raises(ProviderTimeoutError) as exc_info:
            await query_provider_telemetry("AWS", timeout=1.0)
        
        err = exc_info.value
        assert "AWS" in str(err)
        assert len(err.__notes__) >= 2  # Provider_ID + Timeout limit
        assert err.__cause__ is not None
        assert isinstance(err.__cause__, httpx.TimeoutException)

    @respx.mock
    @pytest.mark.asyncio
    async def test_http_504_raises_corrupted_payload_error(self):
        """HTTP 504 debe lanzar CorruptedPayloadError con encadenamiento."""
        from triton_telemetry.exceptions import CorruptedPayloadError
        
        respx.get(PROVIDER_ENDPOINTS["Azure"]).mock(
            return_value=httpx.Response(504)
        )
        
        with pytest.raises(CorruptedPayloadError) as exc_info:
            await query_provider_telemetry("Azure", timeout=3.0)
        
        err = exc_info.value
        assert "504" in str(err) or "HTTP" in str(err)
        assert err.__cause__ is not None
        assert isinstance(err.__cause__, httpx.HTTPStatusError)

    @respx.mock
    @pytest.mark.asyncio
    async def test_corrupt_json_raises_corrupted_payload_error(self):
        """Payload no-JSON debe lanzar CorruptedPayloadError."""
        from triton_telemetry.exceptions import CorruptedPayloadError
        
        respx.get(PROVIDER_ENDPOINTS["GCP"]).mock(
            return_value=httpx.Response(200, text="<xml>not json</xml>")
        )
        
        with pytest.raises(CorruptedPayloadError):
            await query_provider_telemetry("GCP", timeout=3.0)

    @respx.mock
    @pytest.mark.asyncio
    async def test_dns_failure_raises_network_peering_error(self):
        """Fallo de red/DNS debe lanzar NetworkPeeringError."""
        from triton_telemetry.exceptions import NetworkPeeringError
        
        respx.get("https://jsonplaceholder.typicode.com/posts/1").mock(
            side_effect=httpx.ConnectError("Could not resolve host")
        )
        
        with pytest.raises(NetworkPeeringError) as exc_info:
            await query_provider_telemetry("AWS", timeout=3.0)
        
        err = exc_info.value
        assert err.__cause__ is not None
```

#### 3.2.2. Tests de TaskGroup (`test_task_group.py`)

```python
"""Tests de orquestación con asyncio.TaskGroup."""
import pytest
import httpx
import respx
from triton_telemetry.core import scan_all_providers, PROVIDER_ENDPOINTS
from triton_telemetry.exceptions import (
    ProviderTimeoutError,
    CorruptedPayloadError,
    NetworkPeeringError,
)


class TestTaskGroupOrchestration:
    """Valida que TaskGroup agrupa excepciones en ExceptionGroup."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_concurrent_failures_produce_exception_group(self):
        """Múltiples fallos concurrentes deben propagarse como ExceptionGroup."""
        # AWS: timeout
        respx.get(PROVIDER_ENDPOINTS["AWS"]).mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        # Azure: HTTP error
        respx.get(PROVIDER_ENDPOINTS["Azure"]).mock(
            return_value=httpx.Response(504)
        )
        # GCP: éxito
        respx.get(PROVIDER_ENDPOINTS["GCP"]).mock(
            return_value=httpx.Response(200, json={"id": 3})
        )
        
        with pytest.raises(ExceptionGroup) as exc_info:
            await scan_all_providers(["AWS", "Azure", "GCP"], timeout=1.0)
        
        eg = exc_info.value
        # Debe contener al menos un ProviderTimeoutError y un CorruptedPayloadError
        exception_types = {type(e) for e in eg.exceptions}
        assert ProviderTimeoutError in exception_types
        assert CorruptedPayloadError in exception_types

    @respx.mock
    @pytest.mark.asyncio
    async def test_task_names_are_set_for_tracing(self):
        """Cada tarea debe tener un nombre asignado para trazabilidad."""
        respx.get(PROVIDER_ENDPOINTS["AWS"]).mock(
            return_value=httpx.Response(200, json={"id": 1})
        )
        
        results = await scan_all_providers(["AWS"], timeout=3.0)
        assert len(results) == 1
```

**Comando para ejecutar solo tests del Integrante 2:**
```bash
pytest tests/test_integrante_2/ -v
```

---

### Integrante 3: Formateo JSON Forense

**Archivo bajo prueba:** `logging_engine.py` (clase `AsyncJSONFormatter`)

```python
"""Tests para el formateador JSON forense (Integrante 3)."""
import json
import logging
import pytest
from datetime import datetime, timezone
from triton_telemetry.logging_engine import AsyncJSONFormatter
from triton_telemetry.exceptions import ProviderTimeoutError, CorruptedPayloadError


class TestAsyncJSONFormatter:
    """Valida la serialización JSON de log records."""

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
        # Verificar que es parseable como datetime
        datetime.fromisoformat(ts.replace("Z", "+00:00"))

    def test_contains_required_fields(self):
        record = self._make_record()
        output = self.formatter.format(record)
        parsed = json.loads(output)
        
        required = ["timestamp", "level", "logger", "message", "process", "threadName"]
        for field in required:
            assert field in parsed, f"Falta campo requerido: {field}"

    def test_extra_metadata_captured(self):
        """Metadatos inyectados vía 'extra' deben aparecer en el JSON."""
        record = self._make_record(extra={"provider": "AWS", "status_code": 200})
        output = self.formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["provider"] == "AWS"
        assert parsed["status_code"] == 200

    def test_exception_serialization(self):
        """Las excepciones deben serializarse con tipo, mensaje y traceback."""
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = self._make_record(exc_info=exc_info)
        output = self.formatter.format(record)
        parsed = json.loads(output)
        
        assert "exception" in parsed
        exc_data = parsed["exception"]
        assert exc_data["type"] == "ValueError"
        assert "test error" in exc_data["message"]

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
            import sys
            exc_info = sys.exc_info()
        
        record = self._make_record(exc_info=exc_info)
        output = self.formatter.format(record)
        parsed = json.loads(output)
        
        exc_data = parsed["exception"]
        assert exc_data["type"] == "ExceptionGroup"
        assert "sub_exceptions" in exc_data
        assert len(exc_data["sub_exceptions"]) == 2

    def test_exception_cause_chain_serialized(self):
        """El encadenamiento 'raise ... from' debe serializar la causa."""
        try:
            try:
                raise httpx.TimeoutException("original")
            except httpx.TimeoutException as orig:
                raise ProviderTimeoutError("wrapped") from orig
        except ProviderTimeoutError:
            import sys
            exc_info = sys.exc_info()
        
        record = self._make_record(exc_info=exc_info)
        output = self.formatter.format(record)
        parsed = json.loads(output)
        
        exc_data = parsed["exception"]
        assert "cause" in exc_data
        assert exc_data["cause"]["type"] == "TimeoutException"

    def test_notes_included_in_exception_data(self):
        """Las notas de add_note() deben aparecer en la serialización."""
        err = ProviderTimeoutError("timeout")
        err.add_note("Provider: AWS")
        err.add_note("Limit: 1.0s")
        
        try:
            raise err
        except ProviderTimeoutError:
            import sys
            exc_info = sys.exc_info()
        
        record = self._make_record(exc_info=exc_info)
        output = self.formatter.format(record)
        parsed = json.loads(output)
        
        notes = parsed["exception"]["notes"]
        assert "Provider: AWS" in notes
        assert "Limit: 1.0s" in notes
```

**Comando para ejecutar solo tests del Integrante 3:**
```bash
pytest tests/test_integrante_3/ -v
```

---

### Integrante 4: Pipeline No Bloqueante

**Archivo bajo prueba:** `logging_engine.py` (clase `NonBlockingLoggingEngine`)

```python
"""Tests para el pipeline de logging no bloqueante (Integrante 4)."""
import json
import gzip
import os
import logging
import logging.handlers
import pytest
import tempfile
from pathlib import Path
from triton_telemetry.logging_engine import (
    NonBlockingLoggingEngine,
    AsyncJSONFormatter,
    get_async_logger,
)


class TestNonBlockingPipeline:
    """Valida QueueHandler + QueueListener + RotatingFileHandler."""

    def test_engine_creates_log_directory(self, tmp_path):
        log_file = tmp_path / "subdir" / "test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        assert log_file.parent.exists()
        engine.start()
        engine.stop()

    def test_queue_handler_is_non_blocking(self):
        """El logger debe usar QueueHandler (no handlers de archivo directos)."""
        logger, engine = get_async_logger("test_nonblocking")
        try:
            assert len(logger.handlers) == 1
            assert isinstance(logger.handlers[0], logging.handlers.QueueHandler)
        finally:
            engine.stop()

    def test_listener_processes_queued_messages(self, tmp_path):
        """Los mensajes encolados deben procesarse al hacer stop()."""
        log_file = tmp_path / "pipeline_test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        engine.start()
        
        logger = logging.getLogger("pipeline_test")
        logger.handlers = [engine.queue_handler]
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        
        logger.info("Test message through pipeline")
        engine.stop()  # Flush
        
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message through pipeline" in content

    def test_rotating_handler_config(self, tmp_path):
        """RotatingFileHandler debe tener maxBytes=2MB y backupCount=3."""
        log_file = tmp_path / "rotate_test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        
        assert engine.rotating_handler.maxBytes == 2 * 1024 * 1024
        assert engine.rotating_handler.backupCount == 3
        engine.start()
        engine.stop()

    def test_gzip_namer_appends_gz_extension(self, tmp_path):
        """El namer debe agregar extensión .gz a los backups."""
        log_file = tmp_path / "gzip_test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        
        namer = engine.rotating_handler.namer
        assert namer("test.log.1") == "test.log.1.gz"
        engine.start()
        engine.stop()

    def test_gzip_rotator_compresses_and_removes_original(self, tmp_path):
        """El rotator debe comprimir a .gz y eliminar el archivo plano."""
        source = tmp_path / "source.log"
        dest = tmp_path / "dest.log.gz"
        source.write_text("test log data " * 100)
        
        log_file = tmp_path / "rotator_test.log"
        engine = NonBlockingLoggingEngine(log_file_path=str(log_file))
        rotator = engine.rotating_handler.rotator
        
        rotator(str(source), str(dest))
        
        assert not source.exists(), "El archivo original debe eliminarse"
        assert dest.exists(), "El archivo .gz debe crearse"
        
        # Verificar que se puede descomprimir
        with gzip.open(dest, "rt") as f:
            content = f.read()
        assert "test log data" in content
        engine.start()
        engine.stop()

    def test_no_concurrent_file_descriptor_access(self):
        """HARD GATE: El file descriptor NO se abre desde múltiples hilos directamente.
        Todo pasa por QueueHandler -> QueueListener."""
        logger, engine = get_async_logger("test_no_concurrent_fd")
        try:
            # El logger solo debe tener QueueHandler, no RotatingFileHandler directo
            for handler in logger.handlers:
                assert not isinstance(handler, logging.handlers.RotatingFileHandler), \
                    "El logger no debe tener RotatingFileHandler directo (violación de cola)"
        finally:
            engine.stop()
```

**Comando para ejecutar solo tests del Integrante 4:**
```bash
pytest tests/test_integrante_4/ -v
```

---

### Integrante 5: Integración CLI y except*

**Archivos bajo prueba:** `app_operator.py`, `__init__.py`

> **⚠️ Nota:** Estos tests requieren que el Integrante 5 complete `app_operator.py` y `__init__.py`.

#### 3.5.1. Tests del CLI Parser (`test_cli_parser.py`)

```python
"""Tests para el parser CLI de app_operator.py (Integrante 5)."""
import subprocess
import pytest


class TestCLIParser:
    """Valida argparse con sanitizadores integrados."""

    def test_valid_nominal_invocation(self):
        """Invocación válida con todos los argumentos correctos."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS", "GCP",
             "-c", "cluster-us-east-01", "-t", "3.0"],
            capture_output=True, text=True, timeout=30
        )
        # Debe ejecutar sin error de argparse (puede fallar por red, pero no por args)
        assert result.returncode != 2  # 2 = error de argparse

    def test_missing_cluster_id_exits_with_code_2(self):
        """Faltar --cluster-id debe salir con código 2."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS"],
            capture_output=True, text=True
        )
        assert result.returncode == 2

    def test_invalid_provider_rejected(self):
        """Proveedor no válido debe ser rechazado por choices."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "InvalidCloud",
             "-c", "cluster-us-east-01"],
            capture_output=True, text=True
        )
        assert result.returncode == 2

    def test_invalid_timeout_exits_with_code_2(self):
        """Timeout fuera de rango debe salir con código 2."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS",
             "-c", "cluster-us-east-01", "-t", "99.0"],
            capture_output=True, text=True
        )
        assert result.returncode == 2

    def test_invalid_cluster_id_exits_with_code_2(self):
        """Cluster ID inválido debe salir con código 2."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS",
             "-c", "invalid-id", "-t", "2.0"],
            capture_output=True, text=True
        )
        assert result.returncode == 2

    def test_chaos_flag_accepted(self):
        """La bandera --chaos debe ser aceptada."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS",
             "-c", "cluster-us-east-01", "-t", "3.0", "--chaos"],
            capture_output=True, text=True, timeout=30
        )
        # No debe fallar por argparse
        assert "invalid argument" not in result.stderr.lower()

    def test_mode_choices(self):
        """Los modos nominal, debug, emergency deben ser aceptados."""
        for mode in ["nominal", "debug", "emergency"]:
            result = subprocess.run(
                ["python3", "src/app_operator.py", "AWS",
                 "-c", "cluster-us-east-01", "-m", mode],
                capture_output=True, text=True, timeout=15
            )
            assert result.returncode != 2

    def test_invalid_mode_rejected(self):
        """Modo inválido debe ser rechazado."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS",
             "-c", "cluster-us-east-01", "-m", "invalid_mode"],
            capture_output=True, text=True
        )
        assert result.returncode == 2
```

#### 3.5.2. Tests de except* Handling (`test_except_handling.py`)

```python
"""Tests de captura quirúrgica con except* (Integrante 5)."""
import subprocess
import pytest


class TestExceptStarHandling:
    """Valida que except* captura ExceptionGroups correctamente."""

    def test_chaos_mode_does_not_crash(self):
        """HARD GATE: El programa NUNCA debe cerrarse abruptamente ante fallos."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS", "Azure", "GCP",
             "-c", "cluster-us-west-02", "-t", "1.5", "--chaos"],
            capture_output=True, text=True, timeout=30
        )
        # No debe haber traceback sin capturar
        assert "Traceback (most recent call last)" not in result.stderr
        # Debe salir limpiamente (0) o con error controlado
        assert result.returncode == 0

    def test_except_star_does_not_mix_with_plain_except(self):
        """HARD GATE: No mezclar except y except* en el mismo try."""
        import ast
        with open("src/app_operator.py") as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.TryStar):  # try/except*
                # Verificar que no haya exceptores normales mezclados
                # (TryStar solo permite ExceptHandler, no exceptores planos)
                pass  # Python ya lo garantiza sintácticamente
```

#### 3.5.3. Tests de __init__.py

```python
"""Tests para la API pública del paquete (Integrante 5)."""
import pytest


class TestPackageAPI:
    """Valida que __init__.py expone correctamente la API pública."""

    def test_all_exceptions_importable(self):
        from triton_telemetry import (
            TritonError,
            ProviderTimeoutError,
            CorruptedPayloadError,
            NetworkPeeringError,
        )
        assert TritonError is not None

    def test_sanitizers_importable(self):
        from triton_telemetry import parse_timeout, parse_cluster_id
        assert callable(parse_timeout)
        assert callable(parse_cluster_id)

    def test_core_functions_importable(self):
        from triton_telemetry import scan_all_providers
        assert callable(scan_all_providers)

    def test_logging_setup_importable(self):
        from triton_telemetry import setup_triton_logging
        assert callable(setup_triton_logging)

    def test_all_attribute_defined(self):
        import triton_telemetry
        assert hasattr(triton_telemetry, "__all__")
        expected = {
            "TritonError", "ProviderTimeoutError",
            "CorruptedPayloadError", "NetworkPeeringError",
            "parse_timeout", "parse_cluster_id",
            "setup_triton_logging", "scan_all_providers",
        }
        assert set(triton_telemetry.__all__) == expected
```

**Comando para ejecutar solo tests del Integrante 5:**
```bash
pytest tests/test_integrante_5/ -v
```

---

### Integrante 6: Simulación de Caos y Forense

> **⚠️ Importante:** Este integrante es responsable de **desarrollar** la suite de pruebas de caos y el validador forense. Por lo tanto, **no existen tests pre-creados para este integrante** — sus tests son el entregable en sí mismo.

#### Responsabilidades del Integrante 6

1. **Suite de Simulación de Caos**: Desarrollar tests automatizados que inyecten fallos reales en las APIs:
   - Timeout forzado (reducir `--timeout` a `0.1`)
   - Hosts inexistentes para gatillar `NetworkPeeringError`
   - Validar que el sistema sobrevive a múltiples fallos concurrentes

2. **Validador de Telemetría JSON**: Desarrollar tests forenses que:
   - Abran archivos de log comprimidos (`.gz`)
   - Verifiquen que el JSON contenga el árbol completo de `ExceptionGroups`
   - Certifique la integridad de los metadatos (timestamps ISO 8601 UTC, notas forenses)
   - Compruebe la correcta descompresión Gzip

#### Ubicación de los Tests

El Integrante 6 puede crear sus tests en:
- `tests/chaos/` (recomendado para tests de caos)
- `tests/forense/` (recomendado para validador forense)
- Directamente en `tests/` si prefiere

#### Marcadores Automáticos

El `conftest.py` detecta automáticamente directorios con "chaos" o "forensic" en el nombre y aplica los markers `@pytest.mark.chaos` o `@pytest.mark.e2e` respectivamente.

#### Ejemplo de Estructura (a crear por el Integrante 6)

```
tests/
├── chaos/
│   ├── __init__.py
│   ├── test_timeout_injection.py
│   ├── test_network_failures.py
│   └── test_concurrent_chaos.py
└── forense/
    ├── __init__.py
    ├── test_log_integrity.py
    └── test_gzip_decompression.py
```

#### Herramientas Disponibles

- **`respx`**: Para mockear `httpx` y simular fallos de red
- **`pytest-asyncio`**: Para tests asíncronos
- **`subprocess`**: Para ejecutar la CLI completa
- **`gzip`**: Para validar compresión/descompresión

---

## 4. Tests de Hard Gates (Obligatorios)

Estos tests validan las restricciones obligatorias del TP-1. **Fallar cualquiera de estos = desaprobación directa.**

```python
"""Tests de Hard Gates — restricciones obligatorias del TP-1."""
import ast
import pytest


class TestHardGates:
    """Validación estática de restricciones obligatorias."""

    def _parse_file(self, filepath):
        with open(filepath) as f:
            return ast.parse(f.read())

    def test_no_base_exception_subclass(self):
        """HARD GATE: Ninguna excepción puede heredar de BaseException."""
        tree = self._parse_file("src/triton_telemetry/exceptions.py")
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = base.id if isinstance(base, ast.Name) else ""
                    assert base_name != "BaseException", \
                        f"{node.name} hereda de BaseException — VIOLACIÓN HARD GATE"

    def test_no_return_break_continue_in_finally(self):
        """HARD GATE (PEP 765): No return/break/continue en bloques finally."""
        files = [
            "src/app_operator.py",
            "src/triton_telemetry/core.py",
            "src/triton_telemetry/logging_engine.py",
        ]
        
        for filepath in files:
            tree = self._parse_file(filepath)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Try, ast.TryStar)):
                    for stmt in node.finalbody:
                        for child in ast.walk(stmt):
                            if isinstance(child, (ast.Return, ast.Break, ast.Continue)):
                                pytest.fail(
                                    f"{filepath}: {type(child).__name__} en bloque finally "
                                    f"— VIOLACIÓN PEP 765 / Python 3.14"
                                )

    def test_no_plain_except_with_except_star(self):
        """HARD GATE: No mezclar except y except* en el mismo try."""
        tree = self._parse_file("src/app_operator.py")
        
        for node in ast.walk(tree):
            if isinstance(node, ast.TryStar):
                # TryStar (except*) no puede coexistir con exceptores planos
                # Python ya lo garantiza sintácticamente en 3.11+
                pass

    def test_no_bare_except_pass(self):
        """HARD GATE: Prohibido 'except: pass' que silencia ciegamente."""
        files = [
            "src/app_operator.py",
            "src/triton_telemetry/core.py",
            "src/triton_telemetry/logging_engine.py",
            "src/triton_telemetry/exceptions.py",
            "src/triton_telemetry/sanitizer.py",
        ]
        
        for filepath in files:
            tree = self._parse_file(filepath)
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:  # bare except
                        # Verificar si el body es solo 'pass'
                        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                            pytest.fail(
                                f"{filepath}: 'except: pass' encontrado "
                                f"— VIOLACIÓN HARD GATE"
                            )

    def test_requirements_txt_contains_httpx(self):
        """HARD GATE: requirements.txt debe incluir httpx."""
        with open("requirements.txt") as f:
            content = f.read()
        assert "httpx" in content

    def test_readme_exists_and_has_mermaid(self):
        """HARD GATE: README.md debe existir y contener diagrama Mermaid."""
        readme = Path("README.md")
        assert readme.exists(), "README.md no existe"
        content = readme.read_text()
        assert "```mermaid" in content, "README.md debe contener diagrama Mermaid"

    def test_init_exposes_all_api(self):
        """__init__.py debe definir __all__ con la API pública."""
        import triton_telemetry
        assert hasattr(triton_telemetry, "__all__")
        assert len(triton_telemetry.__all__) >= 6


# Necesario para el test de README
from pathlib import Path
```

**Comando para ejecutar solo hard gates:**
```bash
pytest tests/test_hard_gates/ -v
```

---

## 5. Tests de Integración End-to-End

```python
"""Tests de integración completa del sistema."""
import subprocess
import json
import pytest
from pathlib import Path


class TestEndToEnd:
    """Flujo completo CLI → sanitización → core → logging → except*."""

    def test_scenario_a_nominal_operation(self):
        """Escenario A: Operación nominal completa."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS", "GCP",
             "-c", "cluster-us-east-01", "-t", "3.0"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0
        # Debe mencionar los proveedores en la salida
        assert "AWS" in result.stdout or "NOMINAL" in result.stdout

    def test_scenario_b_invalid_arguments(self):
        """Escenario B: Validación temprana de argumentos fallida."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS", "GCP",
             "-c", "cluster-invalido-id", "-t", "9.5"],
            capture_output=True, text=True
        )
        assert result.returncode == 2
        assert "error" in result.stderr.lower()

    def test_scenario_c_chaos_injection(self):
        """Escenario C: Inyección de caos con fallos concurrentes."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS", "Azure", "GCP",
             "-c", "cluster-us-west-02", "-t", "1.5", "--chaos"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0
        # No debe haber crash
        assert "Traceback (most recent call last)" not in result.stderr

    def test_log_file_generated_after_execution(self, tmp_path):
        """Después de ejecutar, debe existir archivo de log."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS",
             "-c", "cluster-us-east-01", "-t", "3.0"],
            capture_output=True, text=True, timeout=30,
            cwd=str(tmp_path)
        )
        # Buscar archivos de log
        log_files = list(Path(tmp_path).rglob("*.log")) + \
                    list(Path(tmp_path).rglob("*.log.gz"))
        # El log puede generarse en el cwd del script
        assert result.returncode == 0
```

**Comando para ejecutar tests de integración:**
```bash
pytest tests/test_integration/ -v --timeout=60
```

---

## 6. Ejecución y Reportes

### 6.1. Comandos de Ejecución

```bash
# Todos los tests
pytest tests/ -v

# Solo tests unitarios (sin red real)
pytest tests/ -v -m "not slow and not e2e"

# Solo un participante
pytest tests/test_integrante_1/ -v
pytest tests/test_integrante_2/ -v
pytest tests/test_integrante_3/ -v
pytest tests/test_integrante_4/ -v
pytest tests/test_integrante_5/ -v
pytest tests/test_integrante_6/ -v

# Hard gates (obligatorios para aprobación)
pytest tests/test_hard_gates/ -v

# Con cobertura de código
pytest tests/ -v --cov=src/triton_telemetry --cov-report=term-missing

# Tests rápidos (sin red, sin subprocess)
pytest tests/ -v -m "unit" --timeout=10
```

### 6.2. Matriz de Responsabilidad

| Participante | Módulo | Tests | Estado |
|---|---|---|---|
| **Integrante 1** | `exceptions.py`, `sanitizer.py` | `test_integrante_1/` | ✅ Implementado |
| **Integrante 2** | `core.py` | `test_integrante_2/` | ✅ Implementado |
| **Integrante 3** | `logging_engine.py` (Formatter) | `test_integrante_3/` | ✅ Implementado |
| **Integrante 4** | `logging_engine.py` (Pipeline) | `test_integrante_4/` | ✅ Implementado |
| **Integrante 5** | `app_operator.py`, `__init__.py` | `test_integrante_5/` | ✅ Creado (falla hasta implementar) |
| **Integrante 6** | Suite de caos + forense | `tests/chaos/` o `tests/forense/` | 🔲 A crear por el integrante |
| **E2E** | Flujo completo | `test_integration/` | ✅ Creado (falla hasta implementar) |

### 6.3. Criterios de Aceptación por Participante

Cada integrante debe cumplir:

- [ ] **Todos sus tests pasan** (verde en `pytest`)
- [ ] **Cobertura > 80%** en su módulo
- [ ] **Hard gates pasan** (tests en `test_hard_gates/`)
- [ ] **PEP 8** (verificar con `ruff check src/`)
- [ ] **No rompe tests de otros integrantes**

### 6.4. Orden de Ejecución Recomendado

1. **Primero:** Hard gates (si fallan, nada sirve)
2. **Segundo:** Integrante 1 (base para todos)
3. **Tercero:** Integrante 2 (depende de excepciones)
4. **Cuarto:** Integrante 3 + 4 (logging, independiente de core)
5. **Quinto:** Integrante 5 (integra todo)
6. **Sexto:** Integrante 6 (validación final)
7. **Final:** Tests de integración end-to-end

---

## Notas Finales

- Los tests usan `respx` para mockear `httpx` — **no requieren internet** para los tests unitarios
- Los tests marcados como `@pytest.mark.slow` o `e2e` sí requieren conexión real
- Python 3.14 está activo — PEP 765 es **SyntaxError**, no warning
- El proyecto usa Python 3.11+ (asyncio.TaskGroup, except*, ExceptionGroup)
