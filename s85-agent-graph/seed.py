#!/usr/bin/env python3
"""
seed.py — Run once to populate the graph with existing project knowledge.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph.core import Graph
from graph.explorer import scan_project_dirs, scan_readmes


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "agent-graph.db")


def main():
    print(f"Seeding graph at: {DB_PATH}")
    g = Graph(DB_PATH)
    g.set_agent("seed")

    print("\nScanning projects...")
    projects = scan_project_dirs(g)
    print(f"  Found {len(projects)} projects")

    print("Scanning README/docs...")
    scan_readmes(g, projects)
    print(f"  Total nodes: {g.count_nodes()}")

    # Register self
    g.add_node("agent", "agent-graph-core",
               {"type": "knowledge-graph", "version": "0.1.0",
                "purpose": "Shared memory for multi-agent orchestration"})
    g.add_node("agent", "seed-script",
               {"type": "bootstrap", "action": "initial scan"})

    # Register high-level goals
    g.add_node("goal", "Unified agent knowledge graph",
               properties={"status": "active", "priority": "highest",
                           "description": "All agents share a common memory of what exists, what was done, and what to do next"})
    g.add_node("goal", "Autonomous development cycle",
               properties={"status": "active", "priority": "high",
                           "description": "Agents self-direct: scan → learn → plan → execute → review → learn"})
    g.add_node("goal", "Rescue and integrate existing work",
               properties={"status": "active", "priority": "high",
                           "description": "Identify salvageable code from all p3 projects and integrate into nimbo + graph"})

    # Record this task
    g.log("seed", "seed", "graph", "initial",
          result="ok", detail=f"Seeded {len(projects)} projects into graph")

    print(f"\nFinal stats:")
    for k, v in g.stats().items():
        print(f"  {k}: {v}")
    print("\nDone. Graph ready at", DB_PATH)
    g.close()


if __name__ == "__main__":
    main()
