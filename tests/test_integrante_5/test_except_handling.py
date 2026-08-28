"""Tests de captura quirúrgica con except* (Integrante 5)."""
import subprocess
import pytest


class TestExceptStarHandling:
    """Valida que except* captura ExceptionGroups correctamente."""

    def test_chaos_mode_does_not_crash(self):
        """HARD GATE: El programa NUNCA debe cerrarse abruptamente ante fallos."""
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS", "Azure", "GCP",
             "-c", "cluster-us-west-02", "-t", "1.5", "--chaos"],
            capture_output=True, text=True, timeout=30
        )
        # Verificar que realmente se ejecutó (no archivo vacío)
        assert "TRITÓN" in result.stdout or "AWS" in result.stdout or "ANOMALÍA" in result.stdout, \
            "app_operator.py no produjo output esperado — ¿está implementado?"
        # No debe haber traceback sin capturar
        assert "Traceback (most recent call last)" not in result.stderr
        # Debe salir limpiamente (0) o con error controlado
        assert result.returncode == 0

    def test_except_star_does_not_mix_with_plain_except(self):
        """HARD GATE: No mezclar except y except* en el mismo try."""
        import ast
        with open("src/app_operator.py") as f:
            content = f.read()
            tree = ast.parse(content)

        # Verificar que app_operator.py tiene contenido real (no vacío)
        assert len(content.strip()) > 0, "app_operator.py está vacío"
        
        # Verificar que existe al menos un TryStar (except*)
        has_trystar = any(isinstance(node, ast.TryStar) for node in ast.walk(tree))
        assert has_trystar, "app_operator.py debe usar except* para captura quirúrgica"

        for node in ast.walk(tree):
            if isinstance(node, ast.TryStar):  # try/except*
                # Verificar que no haya exceptores normales mezclados
                # (TryStar solo permite ExceptHandler, no exceptores planos)
                pass  # Python ya lo garantiza sintácticamente
