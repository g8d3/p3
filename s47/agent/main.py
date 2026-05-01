"""Vibe Coding Agent — voice agent with configurable LLM provider."""

import os
import sys
import json
import asyncio
import subprocess

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    llm as llm_module,
    function_tool,
)
from livekit.plugins import silero
from livekit.plugins.openai import LLM as OpenAILLM
from livekit.plugins.deepgram import STT as DeepgramSTT
from tts import ChutesTTS


# ── LLM Provider Config ────────────────────────────────────────────────────

LLM_PROVIDERS = {
    "zai-coding-plan": {
        "base_url": "https://api.z.ai/api/coding/paas/v4",
        "api_key": os.environ.get("ZAI_API_KEY", ""),
    },
    "openai": {
        "base_url": None,
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "api_key": os.environ.get("CEREBRAS_API_KEY", ""),
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": os.environ.get("OPENROUTER_API_KEY", ""),
    },
}

DEFAULT_PROVIDER = "zai-coding-plan"
DEFAULT_MODEL = "glm-4.5-air"


def build_llm(provider: str, model: str) -> OpenAILLM:
    """Create an OpenAI-compatible LLM instance for the given provider/model."""
    cfg = LLM_PROVIDERS.get(provider, LLM_PROVIDERS[DEFAULT_PROVIDER])
    return OpenAILLM(
        model=model,
        base_url=cfg["base_url"],
        api_key=cfg["api_key"],
    )


# ── OpenCode Tool ──────────────────────────────────────────────────────────

class OpenCodeTool(llm_module.Toolset):
    """Tool that delegates code generation tasks to OpenCode CLI."""

    def __init__(self):
        super().__init__(id="opencode")

    @function_tool
    def generate_code(self, task: str) -> str:
        """
        Delegate a coding task to the OpenCode agent.

        Args:
            task: A detailed description of the coding task to perform.
        """
        os.makedirs("/tmp/opencode-workspace", exist_ok=True)
        result = subprocess.run(
            ["opencode", "--no-tui", "--non-interactive", "--execute", task],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/tmp/opencode-workspace",
        )
        return (result.stdout + "\n" + result.stderr)[:2000]


# ── Voice Agent ────────────────────────────────────────────────────────────

class VibeCodingAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a vibe coding assistant. You help users build software "
                "through natural conversation. When the user asks you to write or "
                "modify code, use the `opencode` tool to delegate the task. "
                "Keep your responses conversational and explain what you're doing. "
                "After code generation, summarize the results conversationally."
            )
        )


# ── Entrypoint ─────────────────────────────────────────────────────────────

async def entrypoint(ctx: JobContext):
    print(f"[agent] joining room {ctx.room.name}", flush=True)

    # Give the client a moment to set room metadata with LLM config
    await asyncio.sleep(0.5)

    metadata = {}
    try:
        if ctx.room.metadata:
            metadata = json.loads(ctx.room.metadata)
    except (json.JSONDecodeError, TypeError):
        pass

    provider = metadata.get("provider", DEFAULT_PROVIDER)
    model = metadata.get("model", DEFAULT_MODEL)

    # Validate provider has API key
    prov_config = LLM_PROVIDERS.get(provider, LLM_PROVIDERS[DEFAULT_PROVIDER])
    if not prov_config["api_key"]:
        print(f"[agent] WARNING: no API key for {provider}, falling back to {DEFAULT_PROVIDER}", flush=True)
        provider = DEFAULT_PROVIDER
        model = DEFAULT_MODEL
        prov_config = LLM_PROVIDERS[DEFAULT_PROVIDER]

    print(f"[agent] LLM config: provider={provider}, model={model}", flush=True)

    # Build the LLM based on the user's choice
    llm = build_llm(provider, model)

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=DeepgramSTT(model="nova-3", language="en-US"),
        llm=llm,
        tts=ChutesTTS(),
        tools=[OpenCodeTool()],
        allow_interruptions=True,
    )

    agent = VibeCodingAgent()

    await ctx.connect()
    print(f"[agent] connected to room {ctx.room.name}", flush=True)

    await session.start(agent=agent, room=ctx.room)
    # Keep alive until the room closes
    await asyncio.Future()


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
