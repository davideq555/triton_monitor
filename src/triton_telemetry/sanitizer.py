"""Módulo de sanitización y validación de parámetros para Triton."""

import argparse
import re


def parse_timeout(value: str) -> float:
    """Sanitiza y valida el tiempo de espera (timeout) para las peticiones HTTP.

    Debe ser un flotante estrictamente en el rango [0.1, 5.0] segundos.
    """
    try:
        val = float(value)
        if not (0.1 <= val <= 5.0):
            raise ValueError("El timeout debe estar entre 0.1 y 5.0 segundos.")
        return val
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"Timeout inválido '{value}': {str(e)}"
        ) from e


def parse_cluster_id(value: str) -> str:
    """Valida que el identificador del clúster siga el patrón formal de regex.

    Formato requerido: cluster-<region>-<numero_dos_digitos>
    (ejemplo: cluster-us-east-01).
    """
    pattern = r"^cluster-[a-z]{2,10}-[a-z]+-\d{2}$"
    clean_val = value.strip().lower()

    if not re.match(pattern, clean_val):
        raise argparse.ArgumentTypeError(
            f"El ID del clúster '{value}' no cumple con el formato requerido "
            "(ejemplo válido: 'cluster-us-east-01')."
        )
    return clean_val
