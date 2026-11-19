"""
title: Financial Services Guardrail
author: financial-services-workbench
version: 0.1.0
description: Redacts sample PII, refuses money movement, and shows the guardrail decision in the chat.
"""

from pydantic import BaseModel, Field


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=0, description="Lower runs first.")
        show_allow_banner: bool = Field(
            default=True,
            description="Prepend a one-line guardrail note on allowed replies.",
        )

    def __init__(self):
        self.valves = self.Valves()

    def inlet(self, body: dict, __user__: dict | None = None) -> dict:
        """Mask personal data in the user message before a model sees it."""
        from fsw.guardrails import precheck

        messages = body.get("messages") or []
        for message in reversed(messages):
            if message.get("role") != "user":
                continue
            decision = precheck(_content_text(message.get("content")))
            message["content"] = decision.redacted_text
            break
        return body

    def outlet(self, body: dict, __user__: dict | None = None) -> dict:
        """Redact the assistant reply and replace out-of-policy answers."""
        from fsw.agent import run_agent
        from fsw.data import sensitive_literals
        from fsw.guardrails import precheck, redact_text

        messages = body.get("messages") or []
        user_text = ""
        assistant = None
        for message in messages:
            if message.get("role") == "user":
                user_text = _content_text(message.get("content"))
            if message.get("role") == "assistant":
                assistant = message
        if assistant is None:
            return body

        decision = precheck(user_text)
        content = _content_text(assistant.get("content"))
        if decision.action == "refuse":
            content = run_agent(user_text).text
        else:
            content, _counts = redact_text(content, extra_literals=sensitive_literals())
            if not content.startswith("**Guardrail**") and self.valves.show_allow_banner:
                redacted = "none" if not decision.redactions else ", ".join(
                    f"{name} {decision.redactions[name]}" for name in sorted(decision.redactions)
                )
                content = f"**Guardrail** · allow · PII redacted: {redacted} · read-only sample servicing\n\n{content}"
        assistant["content"] = content
        return body


def _content_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
        return "\n".join(part for part in parts if part)
    return "" if content is None else str(content)
