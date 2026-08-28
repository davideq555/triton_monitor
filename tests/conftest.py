"""Fixtures compartidos para la suite de tests del Proyecto Tritón."""
import sys
import logging
import pytest
from pathlib import Path

# Agregar src/ al path para imports
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))


def pytest_collection_modifyitems(config, items):
    """Marca automáticamente los tests según su directorio."""
    for item in items:
        # Obtener el path relativo del test
        test_path = Path(item.fspath).relative_to(Path(__file__).parent)
        
        # Marcar según el directorio
        if "test_integrante_1" in str(test_path):
            item.add_marker(pytest.mark.unit)
        elif "test_integrante_2" in str(test_path):
            item.add_marker(pytest.mark.unit)
        elif "test_integrante_3" in str(test_path):
            item.add_marker(pytest.mark.unit)
        elif "test_integrante_4" in str(test_path):
            item.add_marker(pytest.mark.unit)
        elif "test_integrante_5" in str(test_path):
            item.add_marker(pytest.mark.integration)
        elif "test_hard_gates" in str(test_path):
            item.add_marker(pytest.mark.hardgate)
        elif "test_integration" in str(test_path):
            item.add_marker(pytest.mark.e2e)
        # Integrante 6: cuando cree sus tests de caos/forense
        elif "chaos" in str(test_path).lower():
            item.add_marker(pytest.mark.chaos)
        elif "forensic" in str(test_path).lower():
            item.add_marker(pytest.mark.e2e)


@pytest.fixture
def sample_timeout():
    """Timeout estándar para tests."""
    return 3.0


@pytest.fixture
def sample_cluster_id():
    """Cluster ID válido para tests."""
    return "cluster-us-east-01"


@pytest.fixture
def all_providers():
    """Lista de todos los proveedores cloud."""
    return ["AWS", "Azure", "GCP"]


@pytest.fixture
def clean_logger():
    """Logger limpio sin handlers previos."""
    logger = logging.getLogger("triton_monitor.test")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    yield logger
    logger.handlers.clear()
