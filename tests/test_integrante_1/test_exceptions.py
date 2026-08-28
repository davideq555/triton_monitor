"""Tests para el módulo de excepciones semánticas de Triton (Integrante 1)."""
import pytest
from triton_telemetry.exceptions import (
    TritonError,
    ProviderTimeoutError,
    CorruptedPayloadError,
    NetworkPeeringError,
)


class TestTritonErrorHierarchy:
    """Valida la jerarquía de excepciones del dominio Triton."""

    def test_triton_error_inherits_from_exception(self):
        """HARD GATE: TritonError DEBE heredar de Exception, NUNCA de BaseException."""
        assert issubclass(TritonError, Exception)

    def test_triton_error_is_not_base_exception(self):
        """TritonError no debe ser BaseException para no capturar Ctrl+C."""
        assert TritonError is not BaseException
        # KeyboardInterrupt hereda de BaseException, NO de Exception
        assert not issubclass(KeyboardInterrupt, TritonError)

    def test_ctrl_c_not_caught_by_triton_error(self):
        """Ctrl+C (KeyboardInterrupt) NO debe ser capturado por TritonError."""
        with pytest.raises(KeyboardInterrupt):
            try:
                raise KeyboardInterrupt()
            except TritonError:
                pytest.fail("TritonError capturó KeyboardInterrupt — VIOLACIÓN HARD GATE")

    def test_provider_timeout_inherits_triton_error(self):
        assert issubclass(ProviderTimeoutError, TritonError)

    def test_corrupted_payload_inherits_triton_error(self):
        assert issubclass(CorruptedPayloadError, TritonError)

    def test_network_peering_inherits_triton_error(self):
        assert issubclass(NetworkPeeringError, TritonError)

    def test_all_subclasses_catchable_as_triton_error(self):
        """Todas las subclases deben capturarse con except TritonError."""
        for exc_class in [ProviderTimeoutError, CorruptedPayloadError, NetworkPeeringError]:
            with pytest.raises(TritonError):
                raise exc_class("test error")

    def test_exception_messages_preserved(self):
        err = ProviderTimeoutError("Timeout en AWS")
        assert str(err) == "Timeout en AWS"

    def test_add_note_support(self):
        """Las excepciones deben soportar add_note() para contexto forense."""
        err = ProviderTimeoutError("Timeout")
        err.add_note("Provider: AWS")
        err.add_note("Timeout: 1.0s")
        assert hasattr(err, "__notes__")
        assert len(err.__notes__) == 2
        assert "Provider: AWS" in err.__notes__
        assert "Timeout: 1.0s" in err.__notes__

    def test_exception_chaining_with_from(self):
        """Las excepciones deben soportar encadenamiento raise ... from."""
        original = ValueError("original cause")
        try:
            try:
                raise original
            except ValueError as e:
                raise ProviderTimeoutError("wrapped") from e
        except ProviderTimeoutError as err:
            assert err.__cause__ is original
            assert isinstance(err.__cause__, ValueError)

    def test_exceptions_are_independent(self):
        """Las subclases no deben capturarse entre sí (solo por su tipo o TritonError)."""
        # CorruptedPayloadError NO debe capturarse como ProviderTimeoutError
        with pytest.raises(CorruptedPayloadError):
            try:
                raise CorruptedPayloadError("not a timeout")
            except ProviderTimeoutError:
                pytest.fail("CorruptedPayloadError fue capturada como ProviderTimeoutError")
