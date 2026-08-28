"""Validador forense de archivos de log JSON comprimidos."""
import json
import gzip
import pytest
import subprocess
import tempfile
from pathlib import Path


class TestForensicValidator:
    """Valida la integridad de los logs JSON generados."""

    @pytest.fixture(autouse=True)
    def run_chaos_and_collect_logs(self, tmp_path):
        """Ejecuta modo caos y recopila logs generados."""
        # Ejecutar en modo caos para generar logs con errores
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS", "Azure", "GCP",
             "-c", "cluster-us-west-02", "-t", "1.5", "--chaos"],
            capture_output=True, text=True, timeout=30,
            cwd=str(tmp_path)
        )
        # Verificar que app_operator.py se ejecutó correctamente
        assert result.returncode == 0, \
            f"app_operator.py falló con código {result.returncode}: {result.stderr}"
        assert "TRITÓN" in result.stdout or "AWS" in result.stdout, \
            "app_operator.py no produjo output — ¿está implementado?"
        
        self.log_dir = tmp_path
        self.log_files = list(tmp_path.rglob("*.log")) + list(tmp_path.rglob("*.log.gz"))

    def test_log_files_are_created(self):
        """Deben generarse archivos de log."""
        assert len(self.log_files) > 0, "No se generaron archivos de log"

    def test_gzip_files_are_valid(self):
        """Los archivos .gz deben ser descomprimibles."""
        gz_files = [f for f in self.log_files if f.suffix == ".gz"]
        for gz_file in gz_files:
            with gzip.open(gz_file, "rt") as f:
                content = f.read()
            assert len(content) > 0

    def test_json_lines_are_valid(self):
        """Cada línea del log debe ser JSON válido."""
        for log_file in self.log_files:
            if log_file.suffix == ".gz":
                with gzip.open(log_file, "rt") as f:
                    lines = f.readlines()
            else:
                lines = log_file.read_text().strip().split("\n")

            for line in lines:
                if line.strip():
                    parsed = json.loads(line)
                    assert isinstance(parsed, dict)

    def test_json_contains_timestamp(self):
        """Cada entrada JSON debe tener timestamp ISO 8601 UTC."""
        for log_file in self.log_files:
            if log_file.suffix == ".gz":
                with gzip.open(log_file, "rt") as f:
                    lines = f.readlines()
            else:
                lines = log_file.read_text().strip().split("\n")

            for line in lines:
                if line.strip():
                    parsed = json.loads(line)
                    assert "timestamp" in parsed
                    assert parsed["timestamp"].endswith("Z")

    def test_exception_entries_have_full_tree(self):
        """Las entradas de error deben tener árbol de excepciones completo."""
        for log_file in self.log_files:
            if log_file.suffix == ".gz":
                with gzip.open(log_file, "rt") as f:
                    lines = f.readlines()
            else:
                lines = log_file.read_text().strip().split("\n")

            for line in lines:
                if line.strip():
                    parsed = json.loads(line)
                    if parsed.get("level") in ("ERROR", "CRITICAL"):
                        if "exception" in parsed:
                            exc = parsed["exception"]
                            assert "type" in exc
                            assert "message" in exc
