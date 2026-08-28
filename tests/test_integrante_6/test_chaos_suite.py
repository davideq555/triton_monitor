"""Suite de simulación de caos — pruebas de resiliencia extrema."""
import subprocess
import pytest
import httpx
import respx
from triton_telemetry.core import scan_all_providers, PROVIDER_ENDPOINTS


class TestChaosSuite:
    """Inyección masiva de fallos concurrentes."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_all_providers_timeout_simultaneously(self):
        """Todos los proveedores con timeout simultáneo."""
        from triton_telemetry.exceptions import ProviderTimeoutError

        for provider in ["AWS", "Azure", "GCP"]:
            respx.get(PROVIDER_ENDPOINTS[provider]).mock(
                side_effect=httpx.TimeoutException("mass timeout")
            )

        with pytest.raises(ExceptionGroup) as exc_info:
            await scan_all_providers(["AWS", "Azure", "GCP"], timeout=0.1)

        eg = exc_info.value
        assert len(eg.exceptions) == 3
        assert all(isinstance(e, ProviderTimeoutError) for e in eg.exceptions)

    @respx.mock
    @pytest.mark.asyncio
    async def test_mixed_failure_types(self):
        """Mezcla de timeout + HTTP error + network error simultáneos."""
        from triton_telemetry.exceptions import (
            ProviderTimeoutError, CorruptedPayloadError, NetworkPeeringError
        )

        respx.get(PROVIDER_ENDPOINTS["AWS"]).mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        respx.get(PROVIDER_ENDPOINTS["Azure"]).mock(
            return_value=httpx.Response(504)
        )
        respx.get(PROVIDER_ENDPOINTS["GCP"]).mock(
            side_effect=httpx.ConnectError("DNS failure")
        )

        with pytest.raises(ExceptionGroup) as exc_info:
            await scan_all_providers(["AWS", "Azure", "GCP"], timeout=1.0)

        types = {type(e) for e in exc_info.value.exceptions}
        assert ProviderTimeoutError in types
        assert CorruptedPayloadError in types
        assert NetworkPeeringError in types

    @respx.mock
    @pytest.mark.asyncio
    async def test_nonexistent_host_raises_network_peering(self):
        """Host inexistente debe gatillar NetworkPeeringError."""
        from triton_telemetry.exceptions import NetworkPeeringError
        from triton_telemetry.core import query_provider_telemetry

        respx.get("https://jsonplaceholder.typicode.com/posts/1").mock(
            side_effect=httpx.ConnectError("Name or service not known")
        )

        with pytest.raises(NetworkPeeringError):
            await query_provider_telemetry("AWS", timeout=1.0)

    def test_cli_chaos_mode_survives_all_failures(self):
        """La CLI completa debe sobrevivir al modo caos sin crash."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS", "Azure", "GCP",
             "-c", "cluster-us-west-02", "-t", "1.0", "--chaos"],
            capture_output=True, text=True, timeout=30
        )
        # Verificar que realmente se ejecutó (no archivo vacío)
        assert "TRITÓN" in result.stdout or "AWS" in result.stdout or "ANOMALÍA" in result.stdout, \
            "app_operator.py no produjo output esperado — ¿está implementado?"
        assert result.returncode == 0
        assert "Traceback" not in result.stderr
