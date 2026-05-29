#!/usr/bin/env python3.12
"""Launcher del Orchestrator (entry point for subprocess)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orchestrator import Orchestrator

if __name__ == "__main__":
    o = Orchestrator()
    try:
        import asyncio
        asyncio.run(o.start())
    except KeyboardInterrupt:
        pass
