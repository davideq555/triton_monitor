"""Tests para core.py en modo nominal — usa respx para mockear httpx (Integrante 2)."""
import pytest
import httpx
import respx
from triton_telemetry.core import (
    query_provider_telemetry,
    scan_all_providers,
    PROVIDER_ENDPOINTS,
    CHAOS_ENDPOINTS,
)
from triton_telemetry.exceptions import (
    ProviderTimeoutError,
    CorruptedPayloadError,
    NetworkPeeringError,
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
        assert isinstance(result["latency_sec"], float)
        assert result["payload_id"] == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_azure_nominal(self):
        respx.get(PROVIDER_ENDPOINTS["Azure"]).mock(
            return_value=httpx.Response(200, json={"id": 2})
        )
        result = await query_provider_telemetry("Azure", timeout=3.0)
        assert result["provider"] == "Azure"
        assert result["payload_id"] == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_gcp_nominal(self):
        respx.get(PROVIDER_ENDPOINTS["GCP"]).mock(
            return_value=httpx.Response(200, json={"id": 3})
        )
        result = await query_provider_telemetry("GCP", timeout=3.0)
        assert result["provider"] == "GCP"
        assert result["payload_id"] == 3


class TestQueryProviderErrorMapping:
    """Tests de mapeo de errores httpx → excepciones Triton."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_raises_provider_timeout_error(self):
        """Timeout debe lanzar ProviderTimeoutError con notas forenses."""
        respx.get(PROVIDER_ENDPOINTS["AWS"]).mock(
            side_effect=httpx.TimeoutException("Connection timed out")
        )

        with pytest.raises(ProviderTimeoutError) as exc_info:
            await query_provider_telemetry("AWS", timeout=1.0)

        err = exc_info.value
        assert "AWS" in str(err)
        assert "1.0" in str(err)
        assert len(err.__notes__) >= 2
        assert err.__cause__ is not None
        assert isinstance(err.__cause__, httpx.TimeoutException)

    @respx.mock
    @pytest.mark.asyncio
    async def test_http_504_raises_corrupted_payload_error(self):
        """HTTP 504 debe lanzar CorruptedPayloadError con encadenamiento."""
        respx.get(PROVIDER_ENDPOINTS["Azure"]).mock(
            return_value=httpx.Response(504)
        )

        with pytest.raises(CorruptedPayloadError) as exc_info:
            await query_provider_telemetry("Azure", timeout=3.0)

        err = exc_info.value
        assert "504" in str(err)
        assert err.__cause__ is not None
        assert isinstance(err.__cause__, httpx.HTTPStatusError)

    @respx.mock
    @pytest.mark.asyncio
    async def test_http_422_raises_corrupted_payload_error(self):
        """HTTP 422 también debe lanzar CorruptedPayloadError."""
        respx.get(PROVIDER_ENDPOINTS["GCP"]).mock(
            return_value=httpx.Response(422)
        )

        with pytest.raises(CorruptedPayloadError):
            await query_provider_telemetry("GCP", timeout=3.0)

    @respx.mock
    @pytest.mark.asyncio
    async def test_corrupt_json_raises_corrupted_payload_error(self):
        """Payload no-JSON debe lanzar CorruptedPayloadError."""
        respx.get(PROVIDER_ENDPOINTS["GCP"]).mock(
            return_value=httpx.Response(200, text="<xml>not json</xml>")
        )

        with pytest.raises(CorruptedPayloadError) as exc_info:
            await query_provider_telemetry("GCP", timeout=3.0)

        err = exc_info.value
        assert err.__cause__ is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_dns_failure_raises_network_peering_error(self):
        """Fallo de red/DNS debe lanzar NetworkPeeringError."""
        respx.get(PROVIDER_ENDPOINTS["AWS"]).mock(
            side_effect=httpx.ConnectError("Could not resolve host")
        )

        with pytest.raises(NetworkPeeringError) as exc_info:
            await query_provider_telemetry("AWS", timeout=3.0)

        err = exc_info.value
        assert err.__cause__ is not None
        assert isinstance(err.__cause__, httpx.ConnectError)

    @respx.mock
    @pytest.mark.asyncio
    async def test_connection_refused_raises_network_peering_error(self):
        """Conexión rechazada debe lanzar NetworkPeeringError."""
        respx.get(PROVIDER_ENDPOINTS["AWS"]).mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(NetworkPeeringError):
            await query_provider_telemetry("AWS", timeout=3.0)


class TestScanAllProviders:
    """Tests de orquestación con asyncio.TaskGroup."""

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
    async def test_concurrent_failures_produce_exception_group(self):
        """Múltiples fallos concurrentes deben propagarse como ExceptionGroup."""
        respx.get(PROVIDER_ENDPOINTS["AWS"]).mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        respx.get(PROVIDER_ENDPOINTS["Azure"]).mock(
            return_value=httpx.Response(504)
        )
        respx.get(PROVIDER_ENDPOINTS["GCP"]).mock(
            return_value=httpx.Response(200, json={"id": 3})
        )

        with pytest.raises(ExceptionGroup) as exc_info:
            await scan_all_providers(["AWS", "Azure", "GCP"], timeout=1.0)

        eg = exc_info.value
        exception_types = {type(e) for e in eg.exceptions}
        assert ProviderTimeoutError in exception_types
        assert CorruptedPayloadError in exception_types

    @respx.mock
    @pytest.mark.asyncio
    async def test_all_fail_simultaneously(self):
        """Todos los proveedores fallan simultáneamente."""
        for provider in ["AWS", "Azure", "GCP"]:
            respx.get(PROVIDER_ENDPOINTS[provider]).mock(
                side_effect=httpx.TimeoutException("mass timeout")
            )

        with pytest.raises(ExceptionGroup) as exc_info:
            await scan_all_providers(["AWS", "Azure", "GCP"], timeout=0.5)

        eg = exc_info.value
        assert len(eg.exceptions) == 3
        assert all(isinstance(e, ProviderTimeoutError) for e in eg.exceptions)
