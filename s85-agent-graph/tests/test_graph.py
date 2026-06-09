"""Tests for agent-graph."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from graph.core import Graph


def test_basic_ops():
    db_path = "/tmp/test_graph.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    g = Graph(db_path)
    g.set_agent("test")

    # Add nodes
    n1 = g.add_node("project", "s84", {"path": "/p3/s84", "desc": "nimbo"})
    n2 = g.add_node("agent", "explorer", {"type": "scanner"})
    n3 = g.add_node("goal", "build graph", {"priority": "high"})

    assert g.count_nodes() == 3
    assert g.count_nodes("project") == 1
    assert g.count_nodes("agent") == 1

    # Query
    projects = g.query_nodes(type="project")
    assert len(projects) == 1
    assert projects[0]["name"] == "s84"

    # Edges
    g.add_edge(n1, "contains", n2)
    edges = g.get_edges(type="contains")
    assert len(edges) == 1

    # Pending tasks
    pending = g.pending_tasks()
    assert len(pending) == 1
    assert pending[0]["name"] == "build graph"

    # Search
    found = g.search_nodes("nimbo")
    assert len(found) == 1

    # Update
    g.update_node(n1, properties={"status": "scanned"})
    n = g.get_node(n1)
    assert n["properties"]["status"] == "scanned"

    # Subgraph
    sg = g.get_subgraph(n1, depth=2)
    assert sg["node"]["name"] == "s84"

    # Stats
    stats = g.stats()
    assert stats["nodes"] == 3
    assert stats["pending_tasks"] == 1

    g.close()
    os.remove("/tmp/test_graph.db")
    print("All tests passed.")


if __name__ == "__main__":
    test_basic_ops()
