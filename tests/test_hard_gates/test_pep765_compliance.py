"""Tests de Hard Gates — restricciones obligatorias del TP-1."""
import ast
import pytest
from pathlib import Path


class TestNoBaseExceptionSubclass:
    """HARD GATE: Ninguna excepción puede heredar de BaseException."""

    def test_no_base_exception_in_exceptions_py(self):
        tree = self._parse("src/triton_telemetry/exceptions.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = base.id if isinstance(base, ast.Name) else ""
                    assert base_name != "BaseException", \
                        f"{node.name} hereda de BaseException — VIOLACIÓN HARD GATE"

    def _parse(self, filepath):
        with open(filepath) as f:
            return ast.parse(f.read())


class TestPEP765Compliance:
    """HARD GATE (PEP 765 / Python 3.14): No return/break/continue en finally."""

    @pytest.mark.parametrize("filepath", [
        "src/app_operator.py",
        "src/triton_telemetry/core.py",
        "src/triton_telemetry/logging_engine.py",
        "src/triton_telemetry/exceptions.py",
        "src/triton_telemetry/sanitizer.py",
    ])
    def test_no_return_break_continue_in_finally(self, filepath):
        with open(filepath) as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, (ast.Try, ast.TryStar)):
                for stmt in node.finalbody:
                    for child in ast.walk(stmt):
                        if isinstance(child, ast.Return):
                            pytest.fail(
                                f"{filepath}: Return en bloque finally "
                                f"— VIOLACIÓN PEP 765 / Python 3.14"
                            )
                        if isinstance(child, ast.Break):
                            pytest.fail(
                                f"{filepath}: Break en bloque finally "
                                f"— VIOLACIÓN PEP 765 / Python 3.14"
                            )
                        if isinstance(child, ast.Continue):
                            pytest.fail(
                                f"{filepath}: Continue en bloque finally "
                                f"— VIOLACIÓN PEP 765 / Python 3.14"
                            )


class TestNoBareExceptPass:
    """HARD GATE: Prohibido 'except: pass' que silencia ciegamente."""

    @pytest.mark.parametrize("filepath", [
        "src/app_operator.py",
        "src/triton_telemetry/core.py",
        "src/triton_telemetry/logging_engine.py",
        "src/triton_telemetry/exceptions.py",
        "src/triton_telemetry/sanitizer.py",
    ])
    def test_no_bare_except_pass(self, filepath):
        with open(filepath) as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:  # bare except
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        pytest.fail(
                            f"{filepath}: 'except: pass' encontrado "
                            f"— VIOLACIÓN HARD GATE"
                        )


class TestRequirementsAndDocs:
    """HARD GATE: requirements.txt y README.md obligatorios."""

    def test_requirements_txt_contains_httpx(self):
        content = Path("requirements.txt").read_text()
        assert "httpx" in content, "requirements.txt debe incluir httpx"

    def test_readme_exists(self):
        assert Path("README.md").exists(), "README.md debe existir"

    @pytest.mark.skip(reason="Depende de README.md — pendiente Integrante 5")
    def test_readme_has_mermaid_diagram(self):
        content = Path("README.md").read_text()
        assert "```mermaid" in content, \
            "README.md debe contener diagrama de flujo Mermaid"


class TestProjectStructure:
    """Valida la estructura modular obligatoria del proyecto."""

    @pytest.mark.parametrize("filepath", [
        "src/triton_telemetry/__init__.py",
        "src/triton_telemetry/exceptions.py",
        "src/triton_telemetry/sanitizer.py",
        "src/triton_telemetry/core.py",
        "src/triton_telemetry/logging_engine.py",
        "src/app_operator.py",
    ])
    def test_required_file_exists(self, filepath):
        assert Path(filepath).exists(), f"Archivo obligatorio faltante: {filepath}"
