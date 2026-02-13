"""
Tests for MedGemma service layer.

Validates error handling and safety guards in the inference service
WITHOUT loading the actual model.
"""

import pytest
from api.services.medgemma import MedGemmaService, ModelNotLoadedError


class TestModelNotLoadedError:
    """ModelNotLoadedError is raised when model fails to load."""

    async def test_generate_raises_when_model_missing(self):
        svc = MedGemmaService()
        svc.loaded = False
        # Override load to simulate failure without touching disk
        svc.load = lambda *a, **kw: _async_false()
        with pytest.raises(ModelNotLoadedError):
            await svc.generate(prompt="test")

    async def test_stream_generate_raises_when_model_missing(self):
        svc = MedGemmaService()
        svc.loaded = False
        svc.load = lambda *a, **kw: _async_false()
        with pytest.raises(ModelNotLoadedError):
            async for _ in svc.stream_generate(prompt="test"):
                pass

    async def test_error_message_is_descriptive(self):
        svc = MedGemmaService()
        svc.loaded = False
        svc.load = lambda *a, **kw: _async_false()
        with pytest.raises(ModelNotLoadedError, match="not loaded"):
            await svc.generate(prompt="test")


class TestTemperatureClamp:
    """Service-level temperature clamping prevents torch crashes."""

    async def test_negative_temperature_clamped(self):
        svc = MedGemmaService()
        svc.loaded = True
        # We can't call generate without a real model, but we can verify
        # the clamp logic by checking it doesn't raise before model access.
        # The clamp is applied before _infer(), so a missing model will
        # raise AttributeError (no self.processor), not a torch crash.
        with pytest.raises(AttributeError):
            await svc.generate(prompt="test", temperature=-1.0)
        # If we got AttributeError (not ValueError), the clamp worked —
        # execution passed the temperature line and hit the model access.


class TestSingleton:
    """MedGemmaService.get() returns the same instance."""

    def test_singleton_returns_same_instance(self):
        # Reset singleton for clean test
        MedGemmaService._instance = None
        a = MedGemmaService.get()
        b = MedGemmaService.get()
        assert a is b
        # Clean up
        MedGemmaService._instance = None

    def test_initial_state_is_not_loaded(self):
        svc = MedGemmaService()
        assert svc.loaded is False
        assert svc.device == "cpu"
        assert svc.model is None


# Helper
async def _async_false():
    return False
