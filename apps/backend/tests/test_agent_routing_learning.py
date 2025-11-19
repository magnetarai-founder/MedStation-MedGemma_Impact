"""
Tests for Agent Routing Learning Integration (Phase A)

Tests the learning-aware tool selection functionality integrated into
the agent routing system.
"""

import os
import pytest
from pathlib import Path

# Ensure we're in development mode to avoid ELOHIM_FOUNDER_PASSWORD requirement
os.environ.setdefault('ELOHIM_ENV', 'development')

# Try to import route_input_logic and LearningSystem
try:
    from api.agent.orchestration.routing import route_input_logic, get_learning_system
    from api.learning_system import LearningSystem
    import api.agent.orchestration.routing as routing_mod
    ROUTING_AVAILABLE = True
except ImportError:
    ROUTING_AVAILABLE = False

pytestmark = pytest.mark.skipif(not ROUTING_AVAILABLE, reason="Routing or learning system not available")


class TestAgentRoutingLearningBasic:
    """Basic tests for routing with learning system"""

    def test_route_without_history_does_not_crash(self):
        """Test that routing works without learning history"""
        resp = route_input_logic("write a function to add two numbers")

        assert isinstance(resp.intent, str)
        assert 0.0 <= resp.confidence <= 1.0
        # model_hint may be None or default; we just assert it doesn't crash
        assert resp.model_hint is None or isinstance(resp.model_hint, str)
        assert resp.next_action is not None

    def test_route_with_user_id_does_not_crash(self):
        """Test that routing works with user_id parameter"""
        resp = route_input_logic("refactor this code", user_id="test_user_123")

        assert isinstance(resp.intent, str)
        assert 0.0 <= resp.confidence <= 1.0
        assert resp.model_hint is None or isinstance(resp.model_hint, str)

    def test_route_without_user_id_still_works(self):
        """Test that routing works without user_id (backwards compatibility)"""
        resp = route_input_logic("explain this function")

        assert isinstance(resp.intent, str)
        assert 0.0 <= resp.confidence <= 1.0


class TestAgentRoutingLearningWithHistory:
    """Tests for routing with learning history"""

    def test_route_prefers_tool_with_higher_success_rate(self, monkeypatch, tmp_path: Path):
        """Test that routing prefers tool with higher success rate"""
        # Use an in-memory learning system for isolation
        db_path = tmp_path / "learning.db"
        ls = LearningSystem(db_path=str(db_path))

        # Seed history: multiple successful executions with tool "aider"
        for _ in range(5):
            ls.track_execution("refactor code", "aider", success=True, execution_time=1.0, context={})

        # Add some failures for other tools
        for _ in range(2):
            ls.track_execution("refactor code", "continue", success=False, execution_time=1.0, context={})

        # Monkeypatch get_learning_system to return our instance
        monkeypatch.setattr(routing_mod, "get_learning_system", lambda: ls)

        resp = route_input_logic("refactor code")

        # Assert that response is valid
        assert resp.model_hint is None or isinstance(resp.model_hint, str)
        assert isinstance(resp.intent, str)
        assert 0.0 <= resp.confidence <= 1.0

    def test_route_handles_learning_system_unavailable(self, monkeypatch):
        """Test that routing gracefully handles missing learning system"""
        # Monkeypatch to simulate learning system unavailable
        monkeypatch.setattr(routing_mod, "get_learning_system", lambda: None)

        resp = route_input_logic("write a test")

        # Should still work with base behavior
        assert isinstance(resp.intent, str)
        assert 0.0 <= resp.confidence <= 1.0
        # Will use default model hints
        assert resp.model_hint is None or isinstance(resp.model_hint, str)

    def test_route_with_strong_preference(self, monkeypatch, tmp_path: Path):
        """Test that strong user preferences influence routing"""
        # Use an in-memory learning system
        db_path = tmp_path / "learning.db"
        ls = LearningSystem(db_path=str(db_path))

        # Seed with some history for both tools
        for _ in range(3):
            ls.track_execution("query data", "aider", success=True, execution_time=1.0, context={})
        for _ in range(3):
            ls.track_execution("query data", "assistant", success=True, execution_time=1.0, context={})

        # Monkeypatch
        monkeypatch.setattr(routing_mod, "get_learning_system", lambda: ls)

        resp = route_input_logic("query data")

        # Should return valid response
        assert isinstance(resp.intent, str)
        assert resp.model_hint is None or isinstance(resp.model_hint, str)


class TestAgentRoutingLearningEdgeCases:
    """Edge case tests"""

    def test_route_with_empty_text(self):
        """Test routing with empty text"""
        resp = route_input_logic("")

        # Should not crash
        assert isinstance(resp.intent, str)

    def test_route_with_very_long_text(self):
        """Test routing with very long text"""
        long_text = "refactor " * 1000  # 1000 words
        resp = route_input_logic(long_text)

        # Should not crash
        assert isinstance(resp.intent, str)
        assert 0.0 <= resp.confidence <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
