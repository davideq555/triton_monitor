"""Módulo de sanitización y validación de parámetros para Triton."""

import argparse
import re

# Formato permitido: cluster-<region>-<numero> (ej. cluster-us-east-01)
CLUSTER_ID_PATTERN = re.compile(r"^cluster-[a-z0-9]+-[0-9]+$")


def validate_cluster_id(cluster_id: str) -> str:
    """Valida y limpia el ID de un cluster mediante regex."""
    if not isinstance(cluster_id, str):
        msg = "El ID del cluster debe ser una cadena de texto."
        raise argparse.ArgumentTypeError(msg)

    clean_id = cluster_id.strip().lower()

    if not CLUSTER_ID_PATTERN.match(clean_id):
        msg = (
            f"ID de cluster '{cluster_id}' inválido. "
            "Formato requerido: 'cluster-<region>-<numero>'."
        )
        raise argparse.ArgumentTypeError(msg)

    return clean_id


def validate_timeout(timeout_val: str | float | int) -> float:
    """Valida que el timeout esté entre 0.1 y 5.0 segundos."""
    try:
        val = float(timeout_val)
    except (ValueError, TypeError) as err:
        msg = "El timeout debe ser un número válido."
        raise argparse.ArgumentTypeError(msg) from err

    if not 0.1 <= val <= 5.0:
        msg = "El timeout debe ser un flotante entre 0.1 y 5.0 segundos."
        raise argparse.ArgumentTypeError(msg)

    return val
