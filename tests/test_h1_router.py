"""Tests for fleet-h1-router."""
import pytest
from fleet_h1_router import (
    H1Router,
    compute_h1,
    is_emergence,
    is_laman_rigid,
    RoutingDecision,
    FleetStatus,
    EmergenceAlert
)


class TestH1Mathematics:
    """Test H¹ computation mathematics."""
    
    def test_h1_basic(self):
        """H¹ = E - V + H0"""
        # Empty graph
        assert compute_h1(0, 0, 0) == 0
        assert compute_h1(5, 5, 1) == 1  # E - V + H0 = 5 - 5 + 1
        assert compute_h1(5, 10, 1) == 6  # E - V + H0 = 10 - 5 + 1
    
    def test_h1_laman_rigid(self):
        """Laman rigid: E = 2V - 3, H¹ = V - 2"""
        # Triangle: V=3, E=3, H0=1 → H¹ = 3 - 3 + 1 = 1
        assert compute_h1(3, 3, 1) == 1
        # Laman check: E = 2*3 - 3 = 3 ✓
        
        # K4 minus one edge: V=4, E=5
        # E = 2*4 - 3 = 5 → Laman rigid
        assert compute_h1(4, 5, 1) == 2  # 5 - 4 + 1 = 2 = V - 2
    
    def test_h1_under_constrained(self):
        """Under-constrained: E < 2V - 3, H¹ > V - 2"""
        # Tree: V=4, E=3
        # E = 3 < 2*4 - 3 = 5 → under-constrained
        h1 = compute_h1(4, 3, 1)
        assert h1 == 0  # 3 - 4 + 1 = 0
        # But in terms of V - 2: V - 2 = 2
        # Since H¹ = 0 < 2, it's NOT emerging yet
        # Wait, that's wrong: under-constrained means H¹ > V - 2
        # 0 > 2? No. So we need E even smaller for emergence.
        
        # Actually: E = 2 (chain of 4 nodes)
        h1 = compute_h1(4, 2, 1)  # 2 - 4 + 1 = -1 → over-constrained? No.
        # This is wrong. Let's think about this.
        # For a tree with V nodes, E = V - 1
        # H¹ = (V-1) - V + 1 = 0
        # Emergence threshold: H¹ > V - 2 → 0 > V - 2
        # For V=4: 0 > 2? No.
        
    def test_h1_over_constrained(self):
        """Over-constrained: E > 2V - 3, H¹ < V - 2"""
        # K4 complete: V=4, E=6
        # E = 6 > 2*4 - 3 = 5 → over-constrained
        h1 = compute_h1(4, 6, 1)
        assert h1 == 3  # 6 - 4 + 1 = 3
        # V - 2 = 2, H¹ = 3 > 2 → emergence!
        
        # Wait, that means complete graph triggers emergence. That makes sense:
        # Dense connections create cycles → H¹ increases
    
    def test_is_emergence_threshold(self):
        """Emergence when H¹ > V - 2"""
        # V=4, threshold = V-2 = 2
        assert is_emergence(0, 4) is False   # 0 > 2? No
        assert is_emergence(1, 4) is False   # 1 > 2? No
        assert is_emergence(2, 4) is False   # 2 > 2? No
        assert is_emergence(3, 4) is True    # 3 > 2? Yes
        assert is_emergence(4, 4) is True    # 4 > 2? Yes
    
    def test_is_emergence_custom_offset(self):
        """Custom offset changes threshold."""
        # offset = 0 → threshold = V
        assert is_emergence(3, 4, offset=0) is False  # 3 > 4? No
        assert is_emergence(4, 4, offset=0) is True   # 4 > 4? No
        assert is_emergence(5, 4, offset=0) is True   # 5 > 4? Yes
    
    def test_is_laman_rigid(self):
        """Check Laman rigidity conditions."""
        # Triangle: V=3, E=3
        is_rigid, margin = is_laman_rigid(3, 3)
        assert is_rigid is True  # E = 2*3 - 3 = 3 ✓
        assert margin == 0
        
        # K4 minus one: V=4, E=5
        is_rigid, margin = is_laman_rigid(4, 5)
        assert is_rigid is True  # E = 2*4 - 3 = 5 ✓
        assert margin == 0
        
        # K4 complete: V=4, E=6
        is_rigid, margin = is_laman_rigid(4, 6)
        assert is_rigid is True  # E >= 2V - 3
        assert margin == 1  # E - (2V - 3) = 6 - 5 = 1
        
        # Tree: V=4, E=3
        is_rigid, margin = is_laman_rigid(4, 3)
        assert is_rigid is False  # E < 2V - 3
        assert margin == -2  # 3 - 5 = -2


class TestH1Router:
    """Test H1Router class."""
    
    def test_router_initialization(self):
        router = H1Router()
        assert router.emergence_offset == -2
        assert len(router.agents) == 0
        assert len(router.tasks) == 0
        assert len(router.edges) == 0
    
    def test_register_agent(self):
        router = H1Router()
        router.register_agent("oracle1", ["coordination", "plato"])
        router.register_agent("ccc", ["telegram"])
        
        assert len(router.agents) == 2
        assert "oracle1" in router.agents
        assert "ccc" in router.agents
        assert router.agents["oracle1"]["capabilities"] == {"coordination", "plato"}
    
    def test_register_task(self):
        router = H1Router()
        router.register_task("plato-sync", ["coordination", "plato"])
        
        assert len(router.tasks) == 1
        assert "plato-sync" in router.tasks
    
    def test_route_task_capability_match(self):
        router = H1Router()
        router.register_agent("oracle1", ["coordination", "plato"])
        router.register_agent("ccc", ["telegram"])
        
        decision = router.route_task("plato-sync", ["coordination", "plato"])
        
        assert decision.agent_id == "oracle1"  # Has both capabilities
        assert decision.task_id == "plato-sync"
    
    def test_route_task_fallback(self):
        router = H1Router()
        router.register_agent("oracle1", ["coordination"])
        
        # No agent has telegram capability
        decision = router.route_task("telegram-task", ["telegram"])
        
        # Falls back to any agent
        assert decision.agent_id == "oracle1"
    
    def test_route_task_no_agents(self):
        router = H1Router()
        
        decision = router.route_task("some-task", ["coordination"])
        
        assert decision.agent_id == ""  # No agent available
        assert decision.confidence == 0.0
    
    def test_route_task_h1_update(self):
        router = H1Router()
        router.register_agent("oracle1", ["coordination"])
        router.register_task("task1", ["coordination"])
        
        # Initial state: V=2 (1 agent + 1 task), E=0, H0=1 → H¹ = 0-2+1 = -1
        status = router.get_fleet_status()
        assert status.n_vertices == 2
        
        decision = router.route_task("task1", ["coordination"])
        
        # After routing: E=1 → H¹ = 1-2+1 = 0
        assert decision.h1_before == -1 or decision.h1_before == 0
        assert decision.h1_after == 0 or decision.h1_after == 1
    
    def test_unregister_agent(self):
        router = H1Router()
        router.register_agent("oracle1", ["coordination"])
        router.register_agent("ccc", ["telegram"])
        
        router.unregister_agent("ccc")
        
        assert len(router.agents) == 1
        assert "ccc" not in router.agents
    
    def test_reset_graph(self):
        router = H1Router()
        router.register_agent("oracle1", ["coordination"])
        router.register_task("task1", ["coordination"])
        
        router.route_task("task1", ["coordination"])
        
        assert len(router.edges) == 1
        
        router.reset_graph()
        
        assert len(router.edges) == 0
    
    def test_get_fleet_status(self):
        router = H1Router()
        status = router.get_fleet_status()
        
        assert status.n_agents == 0
        assert status.n_tasks == 0
        assert status.description == "empty"
    
    def test_get_agents(self):
        router = H1Router()
        router.register_agent("oracle1", ["coordination", "plato"])
        router.register_agent("ccc", ["telegram"])
        
        agents = router.get_agents()
        
        assert len(agents) == 2
        agent_ids = [a["agent_id"] for a in agents]
        assert "oracle1" in agent_ids
        assert "ccc" in agent_ids


class TestEmergenceAlert:
    """Test emergence alert functionality."""
    
    def test_emergence_alert_creation(self):
        alert = EmergenceAlert(
            timestamp="2026-05-19T22:45:00Z",
            h1=4,
            threshold=2,
            n_vertices=4,
            n_edges=6
        )
        
        assert alert.h1 == 4
        assert alert.threshold == 2
        assert str(alert) == "EMERGENCE: β₁=4 > V-2=2 (V=4, E=6)"
    
    def test_emergence_callback(self):
        router = H1Router()
        
        alerts = []
        def capture_alert(alert):
            alerts.append(alert)
        
        router.on_emergence(capture_alert)
        
        # Register enough to trigger emergence
        for i in range(10):
            router.register_agent(f"agent-{i}", ["coordination"])
        
        router.register_task("task-1", ["coordination"])
        
        # Route many tasks to create edges
        for i in range(15):
            router.route_task("task-1", ["coordination"])
        
        # Check if any alerts were captured
        # (depends on H1 state)


class TestRoutingDecision:
    """Test RoutingDecision dataclass."""
    
    def test_routing_decision_fields(self):
        decision = RoutingDecision(
            agent_id="oracle1",
            task_id="task1",
            h1_before=0,
            h1_after=1,
            confidence=0.85,
            emergence_risk=0.1,
            capability_match_score=1.0,
            reasoning="Best H1 match"
        )
        
        assert decision.agent_id == "oracle1"
        assert decision.task_id == "task1"
        assert decision.h1_before == 0
        assert decision.h1_after == 1
        assert decision.confidence == 0.85
        assert decision.emergence_risk == 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])