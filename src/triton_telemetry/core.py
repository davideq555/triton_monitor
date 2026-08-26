"""Lógica asíncrona de consulta HTTP paralela para telemetría multicloud."""

import asyncio
import json
import logging
from typing import Any

import httpx

from .exceptions import (
    CorruptedPayloadError,
    NetworkPeeringError,
    ProviderTimeoutError,
)

logger = logging.getLogger("triton_monitor")

# TODO: endpoints nominales — APIs reales de JSONPlaceholder para AWS/Azure/GCP
PROVIDER_ENDPOINTS: dict[str, str] = {
    "AWS": "https://jsonplaceholder.typicode.com/posts/1",
    "Azure": "https://jsonplaceholder.typicode.com/posts/2",
    "GCP": "https://jsonplaceholder.typicode.com/posts/3",
}

# TODO: endpoints de caos — httpbin para inyectar fallos reales de red
CHAOS_ENDPOINTS: dict[str, str] = {
    "TIMEOUT_TRIGGER": "https://httpbin.org/delay/3",
    "BAD_GATEWAY_TRIGGER": "https://httpbin.org/status/504",
    "CORRUPTED_TRIGGER": "https://httpbin.org/xml",
}


async def query_provider_telemetry(
    provider: str, timeout: float, use_chaos: bool = False
) -> dict[str, Any]:
    """Consulta asíncrona la API de telemetría del proveedor con httpx.

    Args:
        provider: Identificador del proveedor cloud (AWS, Azure o GCP).
        timeout: Tiempo máximo de espera en segundos.
        use_chaos: Si es True, inyecta caos real en las APIs.

    Returns:
        Diccionario con provider, status, latency_sec y payload_id.

    Raises:
        ProviderTimeoutError: Si se agota el tiempo de espera.
        CorruptedPayloadError: Si el payload no es JSON válido.
        NetworkPeeringError: Si hay fallo HTTP o de red.
    """
    # TODO: seleccionar endpoint según modo nominal o caos
    if use_chaos:
        if provider == "AWS":
            url = CHAOS_ENDPOINTS["TIMEOUT_TRIGGER"]
        elif provider == "Azure":
            url = CHAOS_ENDPOINTS["BAD_GATEWAY_TRIGGER"]
        else:
            url = CHAOS_ENDPOINTS["CORRUPTED_TRIGGER"]
    else:
        url = PROVIDER_ENDPOINTS.get(
            provider, "https://jsonplaceholder.typicode.com/posts/1"
        )

    logger.debug(
        "Petición asíncrona iniciada hacia %s en URL: %s", provider, url,
        extra={"provider": provider},
    )

    # TODO: ejecutar petición HTTP asíncrona con control estricto de timeout
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=timeout)

            # TODO: lanzar HTTPStatusError si el código es 4xx o 5xx
            response.raise_for_status()

            # TODO: parseo JSON estructurado del payload
            try:
                data = response.json()
                logger.info(
                    "Telemetría recibida exitosamente de %s",
                    provider,
                    extra={
                        "provider": provider,
                        "status_code": response.status_code,
                    },
                )
                return {
                    "provider": provider,
                    "status": "NOMINAL",
                    "latency_sec": response.elapsed.total_seconds(),
                    "payload_id": data.get("id", -1),
                }
            except (json.JSONDecodeError, ValueError) as err:
                # TODO: payload corrupto o no serializable — encadenar excepción
                raise CorruptedPayloadError(
                    f"El proveedor {provider} devolvió un payload no serializable "
                    f"o con errores de paridad."
                ) from err

        except httpx.TimeoutException as err:
            # TODO: capturar timeout nativo y re-lanzar como ProviderTimeoutError
            p_err = ProviderTimeoutError(
                f"Se agotó el tiempo de espera ({timeout}s) al conectar "
                f"con {provider}."
            )
            p_err.add_note(f"Provider_ID: {provider}")
            p_err.add_note(f"Requested_Timeout_Limit: {timeout}s")
            p_err.add_note(f"Target_Endpoint: {url}")
            raise p_err from err

        except httpx.HTTPStatusError as err:
            # TODO: capturar error HTTP y re-lanzar como CorruptedPayloadError
            c_err = CorruptedPayloadError(
                f"Estatus HTTP no esperado recibido del proveedor {provider}. "
                f"Código: {err.response.status_code}."
            )
            c_err.add_note(f"Provider_ID: {provider}")
            c_err.add_note(f"HTTP_Status_Code: {err.response.status_code}")
            c_err.add_note(f"Target_Endpoint: {url}")
            raise c_err from err

        except httpx.RequestError as err:
            # TODO: captura genérica de red (DNS, offline, conexión rechazada)
            n_err = NetworkPeeringError(
                f"Error crítico de transporte de red al intentar "
                f"alcanzar {provider}."
            )
            n_err.add_note(f"Provider_ID: {provider}")
            n_err.add_note(f"Network_Error_Type: {type(err).__name__}")
            raise n_err from err


async def scan_all_providers(
    providers: list[str], timeout: float, use_chaos: bool = False
) -> list[dict[str, Any]]:
    """Orquesta llamadas paralelas con asyncio.TaskGroup.

    Todas las excepciones se agrupan en un ExceptionGroup nativo que
    será capturado quirúrgicamente por app_operator.py con except*.

    Args:
        providers: Lista de proveedores a consultar.
        timeout: Tiempo máximo de espera por petición.
        use_chaos: Si es True, activa inyección de caos real.

    Returns:
        Lista de diccionarios con resultados de telemetría.
    """
    tasks: list[asyncio.Task] = []
    results: list[dict[str, Any]] = []

    # TODO: crear TaskGroup para ejecución concurrente de todas las tareas
    async with asyncio.TaskGroup() as tg:
        for provider in providers:
            # TODO: asignar nombre a cada tarea para trazabilidad en logs
            task = tg.create_task(
                query_provider_telemetry(provider, timeout, use_chaos),
                name=f"Task-{provider}",
            )
            tasks.append(task)

    # TODO: colectar resultados solo si no hubo excepciones
    for task in tasks:
        results.append(task.result())

    return results
