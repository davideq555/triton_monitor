#!/usr/bin/env python3
"""Punto de entrada CLI de TritonMonitor (Integrante 5).

Orquesta argparse, el esquema declarativo de logging (dictConfig),
la captura quirúrgica con except* y el apagado ordenado del listener
sin return/break/continue en finally (PEP 765 / PIE790).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import logging.config

from triton_telemetry.core import scan_all_providers
from triton_telemetry.exceptions import (
    CorruptedPayloadError,
    NetworkPeeringError,
    ProviderTimeoutError,
    TritonError,
)
from triton_telemetry.logging_engine import (
    AsyncJSONFormatter,
    NonBlockingLoggingEngine,
)
from triton_telemetry.sanitizer import parse_cluster_id, parse_timeout

LOGGER_NAME = "triton_monitor"
LOG_FILE_PATH = "logs/triton_services.log"


def build_logging_schema(console_level: str) -> dict:
    """Esquema declarativo inyectado con logging.config.dictConfig.

    La consola vive en este esquema. El I/O a disco lo toma el
    NonBlockingLoggingEngine del Integrante 4 (un solo descriptor,
    detrás de QueueHandler + QueueListener).
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json_structured": {
                "()": AsyncJSONFormatter,
            },
            "console_clean": {
                "format": "%(asctime)s [%(levelname)s] (%(taskName)s) %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "stdout_console": {
                "class": "logging.StreamHandler",
                "level": console_level,
                "formatter": "console_clean",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            LOGGER_NAME: {
                "level": "DEBUG",
                "handlers": ["stdout_console"],
                "propagate": False,
            }
        },
    }


def configure_logging(
    mode: str,
    quiet: bool,
    json_stdout: bool,
) -> tuple[logging.Logger, NonBlockingLoggingEngine]:
    """Inyecta dictConfig y acopla el pipeline no bloqueante del Integrante 4."""
    if quiet:
        console_level = "ERROR"
    elif json_stdout or mode == "debug":
        console_level = "DEBUG"
    elif mode == "emergency":
        console_level = "WARNING"
    else:
        console_level = "INFO"

    logging.config.dictConfig(build_logging_schema(console_level))
    app_logger = logging.getLogger(LOGGER_NAME)

    if json_stdout:
        json_formatter = AsyncJSONFormatter()
        for handler in app_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setFormatter(json_formatter)

    engine = NonBlockingLoggingEngine(
        log_file_path=LOG_FILE_PATH,
        formatter=AsyncJSONFormatter(),
    )
    engine.rotating_handler.setLevel(logging.DEBUG)
    engine.queue_handler.setLevel(logging.DEBUG)
    app_logger.addHandler(engine.queue_handler)
    engine.start()

    return app_logger, engine


def build_cli_parser() -> argparse.ArgumentParser:
    """Parser declarativo: validadores del Integrante 1, modos y salida excluyente."""
    parser = argparse.ArgumentParser(
        prog="TritonMonitor",
        description=(
            "Consola de Telemetría Multicloud y Observabilidad Asíncrona "
            "(PROYECTO TRITÓN)."
        ),
    )
    parser.add_argument(
        "proveedores",
        nargs="+",
        choices=["AWS", "Azure", "GCP"],
        help="Identificadores de los proveedores cloud a monitorear.",
    )
    parser.add_argument(
        "-c",
        "--cluster-id",
        type=parse_cluster_id,
        default="cluster-us-east-01",
        help="ID de clúster (formato cluster-<region>-<numero>, ej. cluster-us-east-01).",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=parse_timeout,
        default=2.5,
        help="Timeout HTTP en segundos (rango 0.1 a 5.0).",
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["nominal", "debug", "emergency"],
        default="nominal",
        help="Modo operativo del despachador de telemetría.",
    )
    parser.add_argument(
        "--chaos",
        action="store_true",
        help="Inyecta fallos reales de red contra httpbin / payloads no JSON.",
    )

    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--quiet",
        action="store_true",
        help="Silencia stdout: solo ERROR o superior.",
    )
    output_group.add_argument(
        "--verbose",
        action="store_true",
        help="Fuerza nivel DEBUG en consola.",
    )
    output_group.add_argument(
        "--json-stdout",
        action="store_true",
        help="Emite la telemetría de consola en JSON estructurado.",
    )
    return parser


def _emit_forensic_notes(app_logger: logging.Logger, exc: BaseException) -> None:
    """Vuelca en consola las notas adjuntadas con Exception.add_note()."""
    for note in getattr(exc, "__notes__", []):
        app_logger.error("     └─ [FORENSE TRITÓN] %s", note)


def _log_exception_member(
    app_logger: logging.Logger, prefix: str, exc: BaseException
) -> None:
    app_logger.error("%s %s", prefix, exc, exc_info=exc)
    _emit_forensic_notes(app_logger, exc)


async def async_main() -> None:
    args = build_cli_parser().parse_args()
    effective_mode = "debug" if args.verbose else args.mode
    app_logger, engine = configure_logging(
        mode=effective_mode,
        quiet=args.quiet,
        json_stdout=args.json_stdout,
    )

    use_chaos = bool(args.chaos or args.mode == "emergency")

    app_logger.info("=" * 64)
    app_logger.info("  INICIANDO MONITOREO MULTICLOUD: PROYECTO TRITÓN")
    app_logger.info("=" * 64)
    app_logger.info("  Clúster objetivo: %s", args.cluster_id)
    app_logger.info("  Modo operativo: %s", args.mode.upper())
    app_logger.info("  Proveedores: %s", ", ".join(args.proveedores))
    app_logger.info("  Timeout límite: %ss", args.timeout)
    if use_chaos:
        app_logger.warning(
            "  ADVERTENCIA: inyección de caos activa (--chaos o modo emergency)."
        )
    app_logger.info("=" * 64)

    try:
        results = await scan_all_providers(
            args.proveedores,
            args.timeout,
            use_chaos=use_chaos,
        )
        app_logger.info("ESCANEO COMPLETADO SIN ANOMALÍAS NO CONTROLADAS:")
        for item in results:
            latency = item.get("latency_sec")
            latency_txt = f"{latency:.3f}" if isinstance(latency, int | float) else "n/a"
            app_logger.info(
                "  • %s -> latencia=%s s | payload_id=%s | estado=%s",
                item.get("provider"),
                latency_txt,
                item.get("payload_id", "-"),
                item.get("status", "UNKNOWN"),
            )

    except* ProviderTimeoutError as group:
        app_logger.error(
            "ANOMALÍA: TIMEOUTS CONCURRENTES EN PROVEEDORES (%s incidentes)",
            len(group.exceptions),
        )
        for exc in group.exceptions:
            _log_exception_member(app_logger, "   Fallo:", exc)

    except* CorruptedPayloadError as group:
        app_logger.error(
            "ADVERTENCIA: PAYLOADS HTTP CORRUPTOS O ESTATUS NO ESPERADO (%s incidentes)",
            len(group.exceptions),
        )
        for exc in group.exceptions:
            _log_exception_member(app_logger, "   Fallo mitigado:", exc)
        app_logger.warning(
            "Mitigación aplicada: el operador no aborta ante payload corrupto."
        )

    except* NetworkPeeringError as group:
        app_logger.error(
            "ANOMALÍA: FALLO CATASTRÓFICO DE RED/DNS/PEERING (%s incidentes)",
            len(group.exceptions),
        )
        for exc in group.exceptions:
            _log_exception_member(app_logger, "   Fallo:", exc)

    except* TritonError as group:
        app_logger.error(
            "ERROR OPERACIONAL NO CATALOGADO EN ECOSISTEMA TRITÓN (%s incidentes)",
            len(group.exceptions),
        )
        for exc in group.exceptions:
            _log_exception_member(app_logger, "   Fallo:", exc)

    finally:
        # PEP 765: solo liberación de recursos. Sin return/break/continue.
        app_logger.info("=" * 64)
        app_logger.info("  [FIN DE CICLO] Liberando listener de observabilidad.")
        app_logger.info("=" * 64)
        engine.stop()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
