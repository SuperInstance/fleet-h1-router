# Fleet H1 Router — Constraint-Theory-Driven Fleet Routing

> **Route agents by graph structure, not just capabilities. Minimize H¹ to maximize coordination.**

A standalone Python library that routes fleet agents using **H¹ cohomology** as the primary routing signal. Built on FM's constraint theory: the fleet's routing graph is a rigidity framework, and the routing goal is to stay below the emergence threshold (β₁ ≤ V-2).

[![PyPI Version](https://img.shields.io/pypi/v/fleet-h1-router.svg)](https://pypi.org/project/fleet-h1-router/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

---

## The Core Idea

Traditional fleet routing routes agents based on **capabilities**:
- "Agent A can do task T → route A to T"
- Simple, but misses structural constraints

**H¹-driven routing** routes agents based on **graph structure**:
- The fleet's routing graph has nodes (agents + tasks) and edges (routing relationships)
- H¹ cohomology measures how under-constrained the graph is
- When H¹ exceeds threshold (β₁ > V-2), coordination fails → **emergence detected**
- Route agents to **minimize H¹** → better coordination

```
FM's Theorem: For a graph G = (V, E), H¹_dim = E - V + H0

- H¹ > V-2 → under-constrained → coordination fails (EMERGENCE)
- H¹ = V-2 → exactly constrained → Laman rigid (GOOD)
- H¹ < V-2 → over-constrained → redundant edges (INEFFICIENT)

Routing Goal: Keep H¹ as close to V-2 as possible without exceeding it.
```

---

## Quick Start

### Install

```bash
pip install fleet-h1-router
```

### Basic Usage

```python
from fleet_h1_router import H1Router, RoutingDecision

# Create router
router = H1Router()

# Register fleet agents
router.register_agent("oracle1", ["coordination", "plato", "research"])
router.register_agent("ccc", ["telegram", "messaging"])
router.register_agent("forgemaster", ["compilation", "llvm", "constraint-theory"])

# Register tasks
router.register_task("plato-sync", ["coordination", "plato"])
router.register_task("model-benchmark", ["compilation", "research"])
router.register_task("fleet-health-check", ["coordination"])

# Route a task — H1-aware routing
decision = router.route_task("plato-sync")
print(f"Routing: {decision.task_id} → {decision.agent_id}")
print(f"  H¹ before: {decision.h1_before}, H¹ after: {decision.h1_after}")
print(f"  Emergence risk: {decision.emergence_risk:.1%}")

# Check fleet constraint status
status = router.get_fleet_status()
print(f"Fleet H¹: {status['h1_dimension']}, {status['description']}")
print(f"Emergence alert: {status['emergence_detected']}")
```

### Run as Service

```bash
# Start H1 router service
fleet-h1-router serve --port 8902

# Route a task via HTTP
curl -X POST http://localhost:8902/route \
  -H "Content-Type: application/json" \
  -d '{"task_id": "plato-sync", "required_capabilities": ["coordination", "plato"]}'

# Get fleet constraint status
curl http://localhost:8902/status

# Get all agents
curl http://localhost:8902/agents
```

---

## Architecture

### The Routing Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                      H1 ROUTER                               │
│                                                               │
│   Route Request                                              │
│        │                                                     │
│        ▼                                                     │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐ │
│   │ Capability  │───▶│ H¹ Compute  │───▶│  Agent Selector  │ │
│   │   Filter    │    │   (E-V+H0)   │    │  (minimize H¹)   │ │
│   └─────────────┘    └─────────────┘    └─────────────────┘ │
│        │                   │                      │            │
│        ▼                   ▼                      ▼            │
│   Eligible          Emergence               Selected           │
│   Agents           Check                   Agent              │
│                                                               │
│   ┌─────────────────────────────────────────────────────────┐│
│   │              Routing Decision Output                     ││
│   │  {agent_id, task_id, h1_before, h1_after, confidence}   ││
│   └─────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### H¹ Computation

```python
def compute_h1(n_vertices: int, n_edges: int, n_components: int = 1) -> int:
    """
    H¹ cohomology dimension for a constraint graph.
    
    H¹ = E - V + H0
    
    Where:
    - E = number of edges (routing relationships)
    - V = number of vertices (agents + tasks)
    - H0 = number of connected components
    
    Emergence threshold: H¹ > V - 2
    """
    return n_edges - n_vertices + n_components

def is_emergence(h1: int, n_vertices: int) -> bool:
    """Check if graph is in emergence regime."""
    return h1 > (n_vertices - 2) if n_vertices >= 2 else False
```

### Emergence Detection

The router continuously monitors fleet H¹:
- **β₁ ≤ V-2**: Graph is rigid, coordination succeeds
- **β₁ > V-2**: Graph is under-constrained, coordination fails → **EMERGENCE**
- Router actively routes to reduce H¹ and prevent emergence

---

## Complete Example: Holodeck Integration

```python
#!/usr/bin/env python3
"""
H1Router with holodeck integration.
Routes agent tasks based on constraint graph structure.
"""
from fleet_h1_router import H1Router, RoutingDecision, EmergenceAlert
from datetime import datetime
import json

class HolodeckH1Router(H1Router):
    """
    H1 router with PLATO integration for holodeck sessions.
    Posts emergence alerts to PLATO when β₁ exceeds threshold.
    """
    
    def __init__(self, plato_url: str = "http://localhost:8848", **kwargs):
        super().__init__(**kwargs)
        self.plato_url = plato_url
        
        # Pre-populate with known holodeck agents
        self.register_agent("oracle1", ["coordination", "plato", "research", "publishing", "crates"])
        self.register_agent("ccc", ["telegram", "messaging", "ai"])
        self.register_agent("forgemaster", ["compilation", "llvm", "constraint-theory"])
        
    def on_emergence_detected(self, alert: EmergenceAlert):
        """Called when emergence threshold is crossed."""
        print(f"⚠️ EMERGENCE ALERT: β₁={alert.h1} exceeds V-2={alert.threshold}")
        
        # Post to PLATO
        self._post_alert_to_plato(alert)
        
    def _post_alert_to_plato(self, alert: EmergenceAlert):
        """Post emergence alert to PLATO."""
        import urllib.request
        
        payload = json.dumps({
            "domain": "gc/research/h1-routing-experiment",
            "question": f"[EMERGENCE ALERT] β₁={alert.h1} > V-2={alert.threshold}",
            "answer": json.dumps({
                "timestamp": alert.timestamp,
                "h1_dimension": alert.h1,
                "v_threshold": alert.threshold,
                "n_vertices": alert.n_vertices,
                "n_edges": alert.n_edges,
                "routing_decision": alert.routing_decision,
                "recommendation": "Route agents to resolve under-constrained regions"
            }, indent=2),
            "tags": ["emergency", "h1", "emergence", "routing"],
            "confidence": 0.95,
            "source": "fleet-h1-router"
        }).encode()
        
        try:
            req = urllib.request.Request(
                f"{self.plato_url}/submit",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"  PLATO alert posted: {resp.read()[:100]}")
        except Exception as e:
            print(f"  PLATO alert failed: {e}")
    
    def route_session_task(self, session_id: str, task_type: str, required_caps: list) -> RoutingDecision:
        """
        Route a session task with H1 awareness.
        
        Uses both capability matching AND H1 minimization.
        """
        # Get decision
        decision = self.route_task(
            task_id=f"{session_id}:{task_type}",
            required_capabilities=required_caps
        )
        
        # Emit routing tile
        self._emit_routing_tile(decision, session_id, task_type)
        
        return decision
    
    def _emit_routing_tile(self, decision: RoutingDecision, session_id: str, task_type: str):
        """Emit routing decision to PLATO."""
        import urllib.request
        
        payload = json.dumps({
            "domain": "gc/research/h1-routing-experiment",
            "question": f"[H1_ROUTE] {decision.agent_id} → {decision.task_id}",
            "answer": json.dumps({
                "session_id": session_id,
                "task_type": task_type,
                "agent_id": decision.agent_id,
                "h1_before": decision.h1_before,
                "h1_after": decision.h1_after,
                "emergence_risk": decision.emergence_risk,
                "capability_match_score": decision.capability_match_score
            }, indent=2),
            "tags": ["routing", "h1", decision.agent_id],
            "confidence": decision.confidence,
            "source": "fleet-h1-router"
        }).encode()
        
        try:
            req = urllib.request.Request(
                f"{self.plato_url}/submit",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5):
                pass  # Fire and forget
        except:
            pass


if __name__ == "__main__":
    router = HolodeckH1Router()
    
    # Route a few tasks
    for task_name, caps in [
        ("plato-sync", ["coordination", "plato"]),
        ("model-benchmark", ["compilation"]),
        ("fleet-health-check", ["coordination"]),
    ]:
        decision = router.route_task(task_name, required_capabilities=caps)
        print(f"Route: {task_name} → {decision.agent_id} (H¹: {decision.h1_before}→{decision.h1_after})")
    
    # Check fleet status
    status = router.get_fleet_status()
    print(f"\nFleet Status:")
    print(f"  H¹ dimension: {status['h1_dimension']}")
    print(f"  Description: {status['description']}")
    print(f"  Emergence: {status['emergence_detected']}")
```

---

## API Reference

### H1Router

```python
from fleet_h1_router import H1Router

router = H1Router(
    emergence_threshold_offset=-2,  # β₁ > V + offset triggers alert
    min_confidence=0.5,             # Minimum routing confidence
    lookahead_steps=3                # How far to project H1 changes
)
```

#### Methods

| Method | Description |
|--------|-------------|
| `register_agent(id, capabilities)` | Register an agent with capabilities |
| `unregister_agent(id)` | Remove an agent |
| `register_task(task_id, required_caps)` | Register a task with requirements |
| `route_task(task_id, required_capabilities)` | Route a task (H1-aware) |
| `get_fleet_status()` | Get current fleet constraint status |
| `get_h1_snapshot()` | Get H¹ computation details |
| `reset_graph()` | Clear all edges and recompute |

### RoutingDecision

```python
@dataclass
class RoutingDecision:
    agent_id: str           # Selected agent
    task_id: str            # Task being routed
    h1_before: int          # H¹ before routing
    h1_after: int           # H¹ after routing (projected)
    confidence: float       # Decision confidence (0.0-1.0)
    emergence_risk: float  # Probability of emergence
    capability_match_score: float  # How well agent matches requirements
    reasoning: str         # Why this agent was chosen
```

### FleetStatus

```python
@dataclass
class FleetStatus:
    n_agents: int           # Number of registered agents
    n_tasks: int            # Number of registered tasks
    n_edges: int            # Number of routing edges
    h1_dimension: int       # Current H¹
    description: str        # "under-constrained" | "rigid" | "over-constrained"
    emergence_detected: bool  # Is H¹ > V-2?
    margin: int             # H¹ - (V-2) — how close to emergence
```

---

## H¹ Mathematics

### Definition

For a constraint graph G = (V, E) with H₀ connected components:

```
H¹(G) = ker(∂₁) / im(∂₂)
dim(H¹) = E - V + H₀
```

### Laman Rigidity

A graph is **minimally rigid** (just enough constraints) when:
- E = 2V - 3 (exactly enough edges)
- H¹ = V - 2 (exactly at the emergence boundary)

### Emergence Threshold

```
β₁ = H¹_dim
Emergence occurs when: β₁ > V - 2

This means:
- More independent cycles than vertices can support
- The graph has more degrees of freedom than constraints
- Coordination fails because positions can't be determined
```

### Routing Interpretation

| H¹ Value | Graph State | Routing Action |
|----------|------------|---------------|
| H¹ > V-2 | Under-constrained | Route agents to ADD constraints |
| H¹ = V-2 | Exactly rigid | Optimal routing, maintain status quo |
| H¹ < V-2 | Over-constrained | Route agents to SIMPLIFY graph |

---

## Configuration

### Environment Variables

```bash
H1_ROUTER_PORT=8902          # Service port (default: 8902)
PLATO_URL=http://localhost:8848  # PLATO server
EMERGENCE_THRESHOLD=-2       # H¹ offset from V to trigger alert
LOG_LEVEL=INFO               # Logging level
```

### YAML Configuration

```yaml
# fleet-h1-router.yaml
router:
  emergence_threshold_offset: -2  # β₁ > V-2 triggers alert
  min_confidence: 0.5
  lookahead_steps: 3
  
agents:
  - id: oracle1
    capabilities: [coordination, plato, research]
  - id: ccc
    capabilities: [telegram, messaging]

tasks:
  - id: plato-sync
    required_capabilities: [coordination, plato]

plato:
  url: http://localhost:8848
  alert_room: gc/research/h1-routing-experiment
```

---

## Metrics

Prometheus metrics for monitoring:

```
fleet_h1_router_h1_dimension{state="current"}
fleet_h1_router_emergence_alerts_total
fleet_h1_router_routing_decisions_total{agent_id, outcome}
fleet_h1_router_emergence_risk{agent_id}
fleet_h1_router_route_duration_seconds
```

---

## Design Principles

1. **H¹ is the primary signal.** Capabilities are a filter, not the decision.
2. **Stay below the emergence threshold.** Every routing decision projects forward.
3. **Emergence is not failure.** It's a signal that constraints need rebalancing.
4. **H¹-guided routing > capability-guided routing** when graph structure matters.
5. **Marginal routing is optimal.** Route to keep H¹ as close to V-2 as possible.

---

## Comparison: H1 Routing vs Capability Routing

| Scenario | Capability Routing | H¹ Routing |
|----------|-------------------|-----------|
| All agents capable | Picks random agent | Picks agent that minimizes H¹ |
| Emergence threshold approaching | Ignores | Warns + adjusts |
| Under-constrained graph | No awareness | Routes to add constraints |
| Over-constrained graph | No awareness | Routes to simplify |
| Graph with cycles | Ignores | Detects via H¹ > V-2 |

---

## Testing

```bash
# Run tests
pytest tests/ -v

# Test H1 computation
pytest tests/test_h1.py -v

# Test routing decisions
pytest tests/test_routing.py -v

# Test emergence detection
pytest tests/test_emergence.py -v
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup.

## License

Apache 2.0 — See [LICENSE](LICENSE).