"""Excepciones personalizadas para el monitor de telemetría Triton."""


class TritonError(Exception):
    """Excepción base para todos los errores del proyecto Triton."""


class ProviderTimeoutError(TritonError):
    """Lanzada cuando la petición al proveedor excede el tiempo límite."""


class CorruptedPayloadError(TritonError):
    """Lanzada ante datos corruptos o respuestas no exitosas del proveedor."""


class NetworkPeeringError(TritonError):
    """Lanzada ante fallos de red o problemas de resolución de host."""
