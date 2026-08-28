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
