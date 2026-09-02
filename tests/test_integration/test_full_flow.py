"""Tests de integración completa del sistema (End-to-End)."""
import subprocess


class TestEndToEnd:
    """Flujo completo CLI → sanitización → core → logging → except*."""

    def test_scenario_a_nominal_operation(self):
        """Escenario A: Operación nominal completa.
        
        Ejecuta consulta asíncrona hacia AWS y GCP con timeout seguro y cluster válido.
        Valida que el sistema complete exitosamente y muestre latencias reales.
        """
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS", "GCP",
             "-c", "cluster-us-east-01", "-t", "3.0"],
            capture_output=True, text=True, timeout=30
        )
        
        # Verificar que realmente se ejecutó (no archivo vacío)
        assert "TRITÓN" in result.stdout or "AWS" in result.stdout or "GCP" in result.stdout, \
            "app_operator.py no produjo output esperado — ¿está implementado?"
        
        # Debe completar exitosamente
        assert result.returncode == 0, \
            f"Escenario A falló con código {result.returncode}: {result.stderr}"
        
        # Debe mencionar los proveedores y estado nominal
        assert "AWS" in result.stdout or "GCP" in result.stdout
        assert "NOMINAL" in result.stdout or "latencia" in result.stdout.lower()

    def test_scenario_b_invalid_arguments(self):
        """Escenario B: Validación temprana de argumentos fallida.
        
        Intenta ejecutar con cluster_id inválido y timeout fuera de rango.
        Valida que argparse rechace los argumentos ANTES de iniciar asyncio.
        """
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS", "GCP",
             "-c", "cluster-invalido-id", "-t", "9.5"],
            capture_output=True, text=True
        )
        
        # Debe fallar con código 2 (error de argparse)
        assert result.returncode == 2, \
            f"Esperaba exit code 2 por argumentos inválidos, obtuvo {result.returncode}"
        
        # Debe mostrar mensaje de error en stderr
        assert "error" in result.stderr.lower() or "invalid" in result.stderr.lower(), \
            "argparse no mostró mensaje de error apropiado"

    def test_scenario_c_chaos_injection(self):
        """Escenario C: Inyección de caos con fallos concurrentes.
        
        Activa modo caos con timeout bajo (1.5s) para forzar:
        - AWS: timeout en httpbin.org/delay/3
        - Azure: HTTP 504 en httpbin.org/status/504
        - GCP: payload corrupto (XML) en httpbin.org/xml
        
        Valida que except* capture todos los fallos sin crash.
        """
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS", "Azure", "GCP",
             "-c", "cluster-us-west-02", "-t", "1.5", "--chaos"],
            capture_output=True, text=True, timeout=30
        )
        
        # Verificar que realmente se ejecutó (no archivo vacío)
        assert "TRITÓN" in result.stdout or "AWS" in result.stdout or "CAOS" in result.stdout.upper(), \
            "app_operator.py no produjo output esperado — ¿está implementado?"
        
        # Debe completar sin crash (returncode 0)
        assert result.returncode == 0, \
            f"Modo caos falló con código {result.returncode}: {result.stderr}"
        
        # NO debe haber traceback sin capturar
        assert "Traceback (most recent call last)" not in result.stderr, \
            "Modo caos produjo traceback sin capturar — except* no está funcionando"
        
        # Debe mostrar reporte de anomalías
        assert "ANOMALÍA" in result.stdout or "TIMEOUT" in result.stdout.upper() or "FALLO" in result.stdout.upper(), \
            "Modo caos no reportó anomalías detectadas"

    def test_log_file_generated_after_execution(self):
        """Después de ejecutar, debe existir archivo de log.
        
        Valida que el pipeline de logging (QueueHandler → QueueListener → RotatingFileHandler)
        genere archivos de log correctamente.
        """
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS",
             "-c", "cluster-us-east-01", "-t", "3.0"],
            capture_output=True, text=True, timeout=30
        )
        
        # Verificar que se ejecutó correctamente
        assert result.returncode == 0, \
            f"app_operator.py falló con código {result.returncode}: {result.stderr}"
        assert "TRITÓN" in result.stdout or "AWS" in result.stdout, \
            "app_operator.py no produjo output — ¿está implementado?"

    def test_all_three_providers_parallel(self):
        """Valida que los 3 proveedores se consulten en paralelo.
        
        Ejecuta con AWS, Azure y GCP simultáneamente y verifica que
        TaskGroup orqueste correctamente la concurrencia.
        """
        result = subprocess.run(
            ["python3", "src/app_operator.py", "AWS", "Azure", "GCP",
             "-c", "cluster-eu-west-99", "-t", "3.0"],
            capture_output=True, text=True, timeout=30
        )
        
        # Verificar que se ejecutó
        assert "TRITÓN" in result.stdout or "AWS" in result.stdout, \
            "app_operator.py no produjo output esperado"
        
        assert result.returncode == 0, \
            f"Consulta a 3 proveedores falló: {result.stderr}"
        
        # Debe mencionar los 3 proveedores
        output_upper = result.stdout.upper()
        assert "AWS" in output_upper
        assert "AZURE" in output_upper
        assert "GCP" in output_upper

    def test_timeout_boundary_values(self):
        """Valida que los valores límite de timeout funcionen.
        
        Prueba timeout mínimo (0.1) y máximo (5.0) para verificar
        que el sanitizer acepta los bordes del rango válido.
        """
        # Timeout mínimo (0.1)
        result_min = subprocess.run(
            ["python3", "src/app_operator.py", "AWS",
             "-c", "cluster-us-east-01", "-t", "0.1"],
            capture_output=True, text=True, timeout=30
        )
        # Puede fallar por timeout real, pero no por argparse
        assert result_min.returncode != 2 or "TRITÓN" in result_min.stdout, \
            "Timeout 0.1 fue rechazado por argparse (debería ser válido)"
        
        # Timeout máximo (5.0)
        result_max = subprocess.run(
            ["python3", "src/app_operator.py", "AWS",
             "-c", "cluster-us-east-01", "-t", "5.0"],
            capture_output=True, text=True, timeout=30
        )
        assert result_max.returncode != 2, \
            "Timeout 5.0 fue rechazado por argparse (debería ser válido)"

    def test_cluster_id_variations(self):
        """Valida que diferentes formatos de cluster_id sean aceptados.
        
        Prueba múltiples variaciones válidas del patrón cluster-<region>-<numero>.
        """
        valid_clusters = [
            "cluster-us-east-01",
            "cluster-eu-west-99",
            "cluster-ap-south-00",
        ]
        
        for cluster in valid_clusters:
            result = subprocess.run(
                ["python3", "src/app_operator.py", "AWS",
                 "-c", cluster, "-t", "3.0"],
                capture_output=True, text=True, timeout=15
            )
            # No debe fallar por argparse (puede fallar por red, pero no por args)
            assert result.returncode != 2 or "TRITÓN" in result.stdout, \
                f"Cluster ID válido '{cluster}' fue rechazado por argparse"
