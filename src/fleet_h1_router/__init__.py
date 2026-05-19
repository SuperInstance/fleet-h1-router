# Fleet H1 Router — Constraint-Theory-Driven Fleet Routing

"""
Fleet H1 Router: Route agents by H¹ cohomology, not just capabilities.

Mathematical foundation:
- H¹_dim = E - V + H0 (cohomology dimension)
- Emergence threshold: H¹ > V - 2
- Laman rigidity: E = 2V - 3, H¹ = V - 2

Usage:
    from fleet_h1_router import H1Router
    
    router = H1Router()
    router.register_agent("oracle1", ["coordination", "plato"])
    decision = router.route_task("my-task", ["coordination"])
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
import json

__version__ = "0.1.0"

# ── H1 Mathematics ──────────────────────────────────────────────────────────

def compute_h1(n_vertices: int, n_edges: int, n_components: int = 1) -> int:
    """
    Compute H¹ cohomology dimension for a constraint graph.
    
    H¹ = E - V + H0
    
    Where:
    - E = number of edges (routing relationships)
    - V = number of vertices (agents + tasks)  
    - H0 = number of connected components
    
    Emergence threshold: H¹ > V - 2
    Laman rigid: H¹ = V - 2 (E = 2V - 3)
    
    Args:
        n_vertices: Number of nodes in graph
        n_edges: Number of edges in graph
        n_components: Number of connected components
        
    Returns:
        H¹ cohomology dimension (integer)
    """
    return n_edges - n_vertices + n_components

def is_emergence(h1: int, n_vertices: int, offset: int = -2) -> bool:
    """
    Check if graph is in emergence regime.
    
    Emergence occurs when H¹ exceeds threshold = V + offset.
    Default offset = -2, so threshold = V - 2.
    
    Args:
        h1: Current H¹ dimension
        n_vertices: Number of vertices
        offset: Threshold offset from V (default: -2)
        
    Returns:
        True if emergence detected
    """
    return h1 > (n_vertices + offset)

def is_laman_rigid(n_vertices: int, n_edges: int) -> Tuple[bool, int]:
    """
    Check if graph satisfies Laman rigidity conditions.
    
    Laman conditions:
    1. E = 2V - 3 (minimally rigid)
    2. For all subgraphs: E' ≤ 2V' - 3
    
    Args:
        n_vertices: Number of vertices
        n_edges: Number of edges
        
    Returns:
        (is_rigid, margin) — margin = E - (2V - 3)
    """
    expected = 2 * n_vertices - 3
    margin = n_edges - expected
    is_rigid = (margin >= 0)  # At least minimally rigid
    
    # Note: full Laman check requires subgraph enumeration
    # This is a simplified O(1) check
    
    return is_rigid, margin

# ── Data Structures ─────────────────────────────────────────────────────────

@dataclass
class RoutingDecision:
    """Result of a routing decision."""
    agent_id: str
    task_id: str
    h1_before: int
    h1_after: int
    confidence: float = 0.8
    emergence_risk: float = 0.0
    capability_match_score: float = 1.0
    reasoning: str = ""

@dataclass 
class FleetStatus:
    """Current state of the fleet constraint graph."""
    n_agents: int
    n_tasks: int
    n_edges: int
    n_vertices: int
    h1_dimension: int
    n_components: int
    description: str
    emergence_detected: bool
    margin: int  # H¹ - (V-2) — positive = under-constrained
    
@dataclass
class EmergenceAlert:
    """Triggered when H¹ exceeds threshold."""
    timestamp: str
    h1: int
    threshold: int
    n_vertices: int
    n_edges: int
    routing_decision: Optional[RoutingDecision] = None
    
    def __str__(self):
        return f"EMERGENCE: β₁={self.h1} > V-2={self.threshold} (V={self.n_vertices}, E={self.n_edges})"

# ── H1Router ────────────────────────────────────────────────────────────────

class H1Router:
    """
    Fleet router driven by H¹ cohomology constraints.
    
    Routes agents based on both capability matching AND H¹ minimization.
    The goal is to keep the fleet's constraint graph below the emergence threshold.
    
    Example:
        router = H1Router()
        router.register_agent("oracle1", ["coordination", "plato"])
        router.register_task("sync-task", ["coordination"])
        
        decision = router.route_task("sync-task", ["coordination"])
        print(f"Route to: {decision.agent_id}")
    """
    
    def __init__(
        self,
        emergence_threshold_offset: int = -2,
        min_confidence: float = 0.5,
        plato_url: Optional[str] = None
    ):
        """
        Initialize H1 router.
        
        Args:
            emergence_threshold_offset: H¹ offset from V to trigger emergence
                Default -2 means emergence when H¹ > V - 2
            min_confidence: Minimum confidence for routing decisions
            plato_url: PLATO server URL (optional, for alerts)
        """
        self.emergence_offset = emergence_threshold_offset
        self.min_confidence = min_confidence
        self.plato_url = plato_url or os.environ.get("PLATO_URL", "http://localhost:8848")
        
        # Fleet state
        self.agents: Dict[str, Dict] = {}  # agent_id -> {capabilities, ...}
        self.tasks: Dict[str, Dict] = {}   # task_id -> {required_capabilities, ...}
        self.edges: Set[Tuple[str, str]] = set()  # (agent_id, task_id) pairs
        
        # Callbacks
        self._on_emergence: Optional[callable] = None
        
    def register_agent(self, agent_id: str, capabilities: List[str]) -> None:
        """
        Register an agent with its capabilities.
        
        Args:
            agent_id: Unique identifier for the agent
            capabilities: List of capability tags
        """
        self.agents[agent_id] = {
            "agent_id": agent_id,
            "capabilities": set(capabilities),
            "registered_at": datetime.utcnow().isoformat() + "Z",
            "n_tasks": 0  # How many tasks routed to this agent
        }
        
    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent and its edges."""
        self.agents.pop(agent_id, None)
        # Remove edges involving this agent
        self.edges = {(a, t) for a, t in self.edges if a != agent_id}
        
    def register_task(self, task_id: str, required_capabilities: List[str]) -> None:
        """
        Register a task with its requirements.
        
        Args:
            task_id: Unique identifier for the task
            required_capabilities: List of required capability tags
        """
        self.tasks[task_id] = {
            "task_id": task_id,
            "required_capabilities": set(required_capabilities),
            "registered_at": datetime.utcnow().isoformat() + "Z"
        }
        
    def _get_eligible_agents(self, required_capabilities: List[str]) -> List[str]:
        """
        Get agents that match required capabilities.
        
        Args:
            required_capabilities: Capabilities the agent must have
            
        Returns:
            List of eligible agent IDs
        """
        required = set(required_capabilities)
        eligible = []
        
        for agent_id, agent_data in self.agents.items():
            if required.issubset(agent_data["capabilities"]):
                eligible.append(agent_id)
                
        return eligible
    
    def _compute_graph_state(self) -> Tuple[int, int, int]:
        """
        Compute current graph state for H¹ calculation.
        
        Returns:
            (n_vertices, n_edges, n_components)
        """
        # Nodes = all agents + all registered tasks
        n_vertices = len(self.agents) + len(self.tasks)
        
        # Edges = routing relationships
        n_edges = len(self.edges)
        
        # Components = connected subgraphs
        # For simplicity, assume 1 if both agents and tasks exist, else 1
        if n_vertices == 0:
            n_components = 0
        elif len(self.agents) == 0 or len(self.tasks) == 0:
            n_components = 1
        else:
            # Estimate: at least 1 component
            n_components = 1
            
        return n_vertices, n_edges, n_components
    
    def _project_h1_after_routing(
        self, 
        agent_id: str, 
        task_id: str
    ) -> int:
        """
        Project H¹ after routing agent to task.
        
        Args:
            agent_id: Agent being routed
            task_id: Task being assigned
            
        Returns:
            Projected H¹ dimension
        """
        # Current state
        n_vertices, n_edges, n_components = self._compute_graph_state()
        
        # Simulate adding the edge
        new_edge = (agent_id, task_id)
        would_add = new_edge not in self.edges
        
        new_n_edges = n_edges + (1 if would_add else 0)
        
        return compute_h1(n_vertices, new_n_edges, n_components)
    
    def _compute_emergence_risk(self, h1_after: int, n_vertices: int) -> float:
        """
        Compute emergence risk as probability.
        
        Args:
            h1_after: H¹ after routing
            n_vertices: Number of vertices
            
        Returns:
            Probability of emergence (0.0 to 1.0)
        """
        threshold = n_vertices + self.emergence_offset
        margin = h1_after - threshold
        
        if margin <= 0:
            return 0.0  # No risk
        
        # Risk increases as margin increases
        # Map margin to probability
        if margin == 1:
            return 0.3
        elif margin == 2:
            return 0.6
        elif margin >= 3:
            return 0.9
        else:
            return float(margin) * 0.3
    
    def route_task(
        self,
        task_id: str,
        required_capabilities: List[str],
        prefer_agents: Optional[List[str]] = None
    ) -> RoutingDecision:
        """
        Route a task to the best agent based on H¹.
        
        Algorithm:
        1. Filter agents by capability match
        2. For each eligible agent, compute projected H¹
        3. Select agent that minimizes H¹
        4. If tie, prefer agent with fewer assigned tasks
        
        Args:
            task_id: Unique task identifier
            required_capabilities: Required capability tags
            prefer_agents: Preferred agent IDs (optional)
            
        Returns:
            RoutingDecision with selected agent and H¹ analysis
        """
        # Register task if not already
        if task_id not in self.tasks:
            self.register_task(task_id, required_capabilities)
        
        # Get eligible agents
        eligible = self._get_eligible_agents(required_capabilities)
        
        if not eligible:
            # No capable agent — fall back to any agent
            eligible = list(self.agents.keys())
            
        if not eligible:
            # No agents available
            n_vertices, n_edges, n_components = self._compute_graph_state()
            return RoutingDecision(
                agent_id="",
                task_id=task_id,
                h1_before=compute_h1(n_vertices, n_edges, n_components),
                h1_after=compute_h1(n_vertices, n_edges, n_components),
                confidence=0.0,
                reasoning="No agents available"
            )
        
        # Apply preference filter
        if prefer_agents:
            eligible = [a for a in eligible if a in prefer_agents] or eligible
        
        # Compute current H¹
        n_vertices, n_edges, n_components = self._compute_graph_state()
        h1_before = compute_h1(n_vertices, n_edges, n_components)
        
        # Score each eligible agent by projected H¹
        best_agent = None
        best_h1_after = float('inf')
        best_task_load = float('inf')
        
        for agent_id in eligible:
            h1_after = self._project_h1_after_routing(agent_id, task_id)
            task_load = self.agents[agent_id].get("n_tasks", 0)
            
            # Select: minimize H¹, then minimize load
            if (h1_after < best_h1_after) or \
               (h1_after == best_h1_after and task_load < best_task_load):
                best_agent = agent_id
                best_h1_after = h1_after
                best_task_load = task_load
        
        # Emit emergence alert if crossing threshold
        emergence_risk = self._compute_emergence_risk(best_h1_after, n_vertices)
        
        if is_emergence(best_h1_after, n_vertices, self.emergence_offset):
            alert = EmergenceAlert(
                timestamp=datetime.utcnow().isoformat() + "Z",
                h1=best_h1_after,
                threshold=n_vertices + self.emergence_offset,
                n_vertices=n_vertices,
                n_edges=len(self.edges) + 1
            )
            if self._on_emergence:
                self._on_emergence(alert)
        
        # Record the edge
        edge = (best_agent, task_id)
        if edge not in self.edges:
            self.edges.add(edge)
            self.agents[best_agent]["n_tasks"] += 1
        
        # Compute capability match score
        agent_caps = self.agents[best_agent]["capabilities"]
        required_set = set(required_capabilities)
        match_score = len(required_set & agent_caps) / len(required_set) if required_set else 1.0
        
        # Confidence based on match and emergence risk
        confidence = min(1.0, match_score * (1.0 - emergence_risk))
        confidence = max(confidence, self.min_confidence)
        
        return RoutingDecision(
            agent_id=best_agent,
            task_id=task_id,
            h1_before=h1_before,
            h1_after=best_h1_after,
            confidence=confidence,
            emergence_risk=emergence_risk,
            capability_match_score=match_score,
            reasoning=f"Selected {best_agent} (H¹: {h1_before}→{best_h1_after})"
        )
    
    def get_fleet_status(self) -> FleetStatus:
        """
        Get current fleet constraint graph status.
        
        Returns:
            FleetStatus with H¹ and emergence info
        """
        n_vertices, n_edges, n_components = self._compute_graph_state()
        
        if n_vertices == 0:
            return FleetStatus(
                n_agents=0, n_tasks=0, n_edges=0,
                n_vertices=0, h1_dimension=0, n_components=0,
                description="empty",
                emergence_detected=False,
                margin=0
            )
        
        h1 = compute_h1(n_vertices, n_edges, n_components)
        
        # Description
        lam_is_rigid, lam_margin = is_laman_rigid(n_vertices, n_edges)
        
        if lam_margin > 0:
            description = "over-constrained" if h1 < (n_vertices - 2) else "rigid"
        elif lam_margin < 0:
            description = "under-constrained"
        else:
            description = "laman-rigid"
        
        # Emergence detection
        threshold = n_vertices + self.emergence_offset
        emergence = is_emergence(h1, n_vertices, self.emergence_offset)
        margin = h1 - threshold
        
        return FleetStatus(
            n_agents=len(self.agents),
            n_tasks=len(self.tasks),
            n_edges=n_edges,
            n_vertices=n_vertices,
            h1_dimension=h1,
            n_components=n_components,
            description=description,
            emergence_detected=emergence,
            margin=margin
        )
    
    def get_h1_snapshot(self) -> Dict:
        """
        Get detailed H¹ computation snapshot.
        
        Returns:
            Dict with all H¹ computation details
        """
        n_vertices, n_edges, n_components = self._compute_graph_state()
        h1 = compute_h1(n_vertices, n_edges, n_components)
        lam_is_rigid, lam_margin = is_laman_rigid(n_vertices, n_edges)
        
        return {
            "n_vertices": n_vertices,
            "n_edges": n_edges,
            "n_components": n_components,
            "h1_dimension": h1,
            "threshold": n_vertices + self.emergence_offset,
            "emergence": is_emergence(h1, n_vertices, self.emergence_offset),
            "laman_rigid": lam_is_rigid,
            "laman_margin": lam_margin,
            "n_agents": len(self.agents),
            "n_tasks": len(self.tasks),
            "description": self.get_fleet_status().description
        }
    
    def on_emergence(self, callback: callable) -> None:
        """
        Register callback for emergence alerts.
        
        Args:
            callback: Function(EmergenceAlert) to call on emergence
        """
        self._on_emergence = callback
    
    def reset_graph(self) -> None:
        """Clear all edges (keep agents and tasks)."""
        self.edges.clear()
        for agent in self.agents.values():
            agent["n_tasks"] = 0
    
    def get_agents(self) -> List[Dict]:
        """Get all registered agents."""
        return [
            {
                "agent_id": a["agent_id"],
                "capabilities": list(a["capabilities"]),
                "n_tasks": a.get("n_tasks", 0)
            }
            for a in self.agents.values()
        ]
    
    def get_tasks(self) -> List[Dict]:
        """Get all registered tasks."""
        return [
            {
                "task_id": t["task_id"],
                "required_capabilities": list(t["required_capabilities"])
            }
            for t in self.tasks.values()
        ]
    
    def __repr__(self) -> str:
        status = self.get_fleet_status()
        return (
            f"H1Router(agents={status.n_agents}, tasks={status.n_tasks}, "
            f"edges={status.n_edges}, H¹={status.h1_dimension}, "
            f"emergence={status.emergence_detected})"
        )


# ── CLI ──────────────────────────────────────────────────────────────────────

def serve(port: int = 8902):
    """Run H1 router as HTTP service."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse
    
    router = H1Router()
    
    # Pre-populate with fleet agents
    router.register_agent("oracle1", ["coordination", "plato", "research", "publishing", "crates"])
    router.register_agent("ccc", ["telegram", "messaging", "ai"])
    router.register_agent("forgemaster", ["compilation", "llvm", "constraint-theory"])
    
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/status":
                status = router.get_fleet_status()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(status.__dict__, indent=2).encode())
            elif self.path == "/agents":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(router.get_agents(), indent=2).encode())
            elif self.path == "/h1-snapshot":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(router.get_h1_snapshot(), indent=2).encode())
            else:
                self.send_response(404)
                self.end_headers()
        
        def do_POST(self):
            if self.path == "/route":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode()
                data = json.loads(body)
                
                decision = router.route_task(
                    data["task_id"],
                    data.get("required_capabilities", [])
                )
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(decision.__dict__, indent=2).encode())
            elif self.path == "/register/agent":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode()
                data = json.loads(body)
                router.register_agent(data["agent_id"], data.get("capabilities", []))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"status": "registered"}')
            else:
                self.send_response(404)
                self.end_headers()
    
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Fleet H1 Router serving on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8902
        serve(port)
    else:
        # Demo mode
        router = H1Router()
        router.register_agent("oracle1", ["coordination", "plato", "research"])
        router.register_agent("ccc", ["telegram", "messaging"])
        router.register_agent("forgemaster", ["compilation", "llvm"])
        
        print(f"Initialized: {router}")
        
        for task_name, caps in [
            ("plato-sync", ["coordination", "plato"]),
            ("model-benchmark", ["compilation"]),
            ("fleet-health", ["coordination"]),
        ]:
            d = router.route_task(task_name, caps)
            print(f"  Route {task_name} → {d.agent_id} (H¹: {d.h1_before}→{d.h1_after})")
        
        status = router.get_fleet_status()
        print(f"\nFleet Status: H¹={status.h1_dimension}, {status.description}")
        print(f"  Emergence: {status.emergence_detected}, Margin: {status.margin}")