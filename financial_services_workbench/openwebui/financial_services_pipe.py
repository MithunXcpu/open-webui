"""
title: Financial Services Agent
author: financial-services-workbench
version: 0.1.0
description: Sample read-only banking assistant with guardrails. Demo ledger only.
"""

from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        llm_provider: str = Field(
            default="",
            description="mock, nvidia, or empty to follow FS_LLM_PROVIDER / NVIDIA_API_KEY",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def pipe(self, body: dict, __user__: dict | None = None, __event_emitter__=None) -> str:
        """Answer with the sample workbench. The guardrail banner is part of the chat message."""
        from fsw.agent import run_agent
        from fsw.textutil import last_user_text

        prompt = last_user_text(body.get("messages") or [])
        provider = (self.valves.llm_provider or "").strip() or None
        if __event_emitter__ is not None:
            emitted = __event_emitter__(
                {"type": "status", "data": {"description": "Checking the sample banking guardrail", "done": False}}
            )
            if hasattr(emitted, "__await__"):
                await emitted
        result = run_agent(prompt, provider=provider)
        if __event_emitter__ is not None:
            emitted = __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"Guardrail: {result.action}", "done": True},
                }
            )
            if hasattr(emitted, "__await__"):
                await emitted
        return result.text
