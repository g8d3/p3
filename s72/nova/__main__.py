"""NOVA — Entry point. Run with: python -m nova"""

from __future__ import annotations
import asyncio
import os
import sys

from .core import Config, VISIBILITY, log, action
from .runtime import NovaServer


async def main():
    config = Config()
    action("nova.start", "NOVA starting")

    server = NovaServer(config)
    app = server.build_app()

    # Start uvicorn
    import uvicorn
    cfg = uvicorn.Config(
        app=app,
        host=os.getenv("NOVA_HOST", "0.0.0.0"),
        port=int(os.getenv("NOVA_PORT", "8777")),
        log_level="warning",
    )
    srv = uvicorn.Server(cfg)

    action("nova.ready", f"NOVA running on http://{cfg.host}:{cfg.port}")
    await srv.serve()


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
