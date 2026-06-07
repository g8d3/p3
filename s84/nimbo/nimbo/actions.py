import sys


def runnable(field, timeout=None):
    """Mark a field as a shell command to be executed via @app.action."""
    frame = sys._getframe(1)
    ns = frame.f_locals
    ns.setdefault("__annotations__", {})[field] = str
    ns.setdefault("__nimbo_runnable__", {})[field] = {"timeout": timeout}
