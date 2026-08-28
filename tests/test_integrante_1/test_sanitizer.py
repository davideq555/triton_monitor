"""Tests para los validadores CLI de Triton (Integrante 1)."""
import argparse
import subprocess
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
        ("0.15", 0.15),
        ("4.99", 4.99),
    ])
    def test_valid_timeout_values(self, value, expected):
        result = parse_timeout(value)
        assert result == pytest.approx(expected)

    # Casos inválidos — fuera de rango
    @pytest.mark.parametrize("value", [
        "0.05",
        "0.0",
        "-1.0",
        "5.1",
        "10.0",
        "100.0",
        "-0.1",
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
        "inf",
        "nan",
    ])
    def test_non_numeric_timeout_raises_argument_type_error(self, value):
        with pytest.raises(argparse.ArgumentTypeError):
            parse_timeout(value)

    def test_boundary_value_minimum(self):
        """0.1 es el mínimo permitido (inclusivo)."""
        assert parse_timeout("0.1") == 0.1

    def test_boundary_value_maximum(self):
        """5.0 es el máximo permitido (inclusivo)."""
        assert parse_timeout("5.0") == 5.0

    @pytest.mark.skip(reason="Depende de app_operator.py — pendiente Integrante 5")
    def test_exit_code_2_on_invalid_timeout(self):
        """argparse debe salir con código 2 ante ArgumentTypeError."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS",
             "-c", "cluster-us-east-01", "-t", "99.0"],
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
        "cluster-ab-cdef-42",
    ])
    def test_valid_cluster_ids(self, cluster_id):
        result = parse_cluster_id(cluster_id)
        assert result is not None
        assert len(result) > 0

    # Casos inválidos
    @pytest.mark.parametrize("cluster_id", [
        "invalido",
        "cluster-us-01",
        "cluster-us-east-1",
        "cluster-us-east-001",
        "cluster-123-east-01",
        "cluster-us-east-aa",
        "",
        "cluster-a-b-01",
        "cluster-us-east-",
        "cluster--east-01",
    ])
    def test_invalid_cluster_ids_raise_argument_type_error(self, cluster_id):
        with pytest.raises(argparse.ArgumentTypeError):
            parse_cluster_id(cluster_id)

    @pytest.mark.skip(reason="Depende de app_operator.py — pendiente Integrante 5")
    def test_exit_code_2_on_invalid_cluster_id(self):
        """argparse debe salir con código 2 ante cluster_id inválido."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS",
             "-c", "invalid-id", "-t", "2.0"],
            capture_output=True, text=True
        )
        assert result.returncode == 2


class TestParseClusterIdNormalization:
    """Valida el comportamiento de normalización del sanitizer."""

    def test_uppercase_is_normalized_to_lowercase(self):
        """El sanitizer normaliza a minúsculas antes de validar (comportamiento válido)."""
        result = parse_cluster_id("CLUSTER-US-EAST-01")
        assert result == "cluster-us-east-01"

    def test_mixed_case_is_normalized(self):
        """Mayúsculas mixtas se normalizan a minúsculas."""
        result = parse_cluster_id("Cluster-Us-East-01")
        assert result == "cluster-us-east-01"

    def test_whitespace_is_stripped(self):
        """Espacios al inicio/final se eliminan."""
        result = parse_cluster_id("  cluster-us-east-01  ")
        assert result == "cluster-us-east-01"
