"""
query — Convenience query helpers for common agent questions.
"""
from .core import Graph


def what_do_we_know_about(graph: Graph, topic: str) -> list[dict]:
    """Search nodes by name/properties for a topic."""
    return graph.search_nodes(topic)


def what_projects_exist(graph: Graph) -> list[dict]:
    return graph.query_nodes(type="project")


def what_agents_exist(graph: Graph) -> list[dict]:
    return graph.query_nodes(type="agent")


def what_is_pending(graph: Graph) -> list[dict]:
    return graph.pending_tasks()


def what_was_the_last_error(graph: Graph) -> list[dict]:
    return graph.query_nodes(type="error")


def what_did_agent_do(graph: Graph, agent_id: str, limit: int = 20) -> list[dict]:
    return graph.get_log(agent_id=agent_id, limit=limit)


def subgraph_summary(graph: Graph, node_id: str) -> str:
    """Render a subgraph as readable text."""
    sg = graph.get_subgraph(node_id, depth=2)
    if not sg:
        return f"Node {node_id} not found"
    lines = [f"─ {sg['node']['name']}  ({sg['node']['type']})"]
    for e in sg["edges"]:
        target = graph.get_node(e["target_id"])
        tname = target["name"] if target else e["target_id"]
        lines.append(f"  └─ {e['type']} → {tname}")
        for child in sg["children"]:
            if child.get("node", {}).get("id") == e["target_id"]:
                for ce in child.get("edges", []):
                    ct = graph.get_node(ce["target_id"])
                    ctname = ct["name"] if ct else ce["target_id"]
                    lines.append(f"      └─ {ce['type']} → {ctname}")
    return "\n".join(lines)
