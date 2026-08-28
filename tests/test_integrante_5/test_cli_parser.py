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
        # Debe ejecutar sin error de argparse Y producir output esperado
        assert result.returncode != 2, "Error de argparse"
        # Verificar que realmente se ejecutó la lógica (no archivo vacío)
        assert "TRITÓN" in result.stdout or "AWS" in result.stdout or "GCP" in result.stdout, \
            "app_operator.py no produjo output esperado — ¿está implementado?"

    def test_missing_cluster_id_exits_with_code_2(self):
        """Faltar --cluster-id debe salir con código 2."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS"],
            capture_output=True, text=True
        )
        assert result.returncode == 2, \
            f"Esperaba exit code 2 por argumento faltante, obtuvo {result.returncode}"
        assert "required" in result.stderr.lower() or "error" in result.stderr.lower()

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
        assert result.returncode != 2, "argparse rechazó --chaos"
        # Verificar que realmente se ejecutó (no archivo vacío)
        assert "TRITÓN" in result.stdout or "AWS" in result.stdout or "CAOS" in result.stdout.upper(), \
            "app_operator.py no produjo output esperado — ¿está implementado?"

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
