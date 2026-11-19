"""Agent loop: guardrail, tool calls, citations, mock or NVIDIA phrasing."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from fsw import llm
from fsw.data import sensitive_literals
from fsw.guardrails import precheck, redact_text, render
from fsw.logging_utils import log_decision
from fsw.planner import plan
from fsw.tools import SIGNATURES, dispatch

PHRASE_SYSTEM = (
    "You are the phrasing layer for a sample, read-only banking workbench. "
    "Use only the ledger excerpts in the user message. Do not add balances, names, flags, "
    "or policy ids that are not in the excerpts. Do not move money. Do not reveal a social "
    "security number, card number, date of birth, email address, or phone number. "
    "Do not write a Sources section; the server adds citations."
)


@dataclass
class AgentResult:
    text: str
    action: str
    reasons: list[str]
    redactions: dict[str, int]
    tools: list[str]
    policy_ids: list[str]
    provider: str
    llm_fallback: str | None = None
    guardrail: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "action": self.action,
            "reasons": self.reasons,
            "redactions": self.redactions,
            "tools": self.tools,
            "policy_ids": self.policy_ids,
            "provider": self.provider,
            "llm_fallback": self.llm_fallback,
            "guardrail": self.guardrail,
        }


def _policy_ids(decision, results: list[dict]) -> list[str]:
    found = list(decision.policy_ids)
    for result in results:
        for match in result.get("matches") or []:
            policy_id = match.get("policy_id")
            if policy_id and policy_id not in found:
                found.append(policy_id)
    return found


def _execute(calls: list[dict]) -> tuple[list[dict], list[str]]:
    results = []
    names = []
    for call in calls:
        name = call.get("name") or ""
        if name not in SIGNATURES:
            continue
        arguments = call.get("arguments") or {}
        if not isinstance(arguments, dict):
            arguments = {}
        results.append(dispatch(name, arguments))
        names.append(name)
    return results, names


def _nvidia_calls(redacted: str) -> tuple[list[dict], str | None]:
    if not os.environ.get("NVIDIA_API_KEY", "").strip():
        return [], "missing_api_key"
    try:
        payload = llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "Choose sample banking tools for a read-only assistant. "
                        "Never request a transfer, a flag change, or raw personal data."
                    ),
                },
                {"role": "user", "content": redacted},
            ],
            tools=llm.TOOL_SPECS,
        )
        message = llm.message_from_response(payload)
    except llm.LLMError as exc:
        return [], exc.code
    calls = [call for call in llm.tool_calls_from_message(message) if call["name"] in SIGNATURES]
    if not calls:
        return [], "no_tool_call"
    return calls, None


def _phrase(redacted: str, results: list[dict]) -> str | None:
    excerpts = "\n\n".join(result.get("summary") or "" for result in results) or "No ledger excerpts."
    try:
        payload = llm.chat(
            [
                {"role": "system", "content": PHRASE_SYSTEM},
                {"role": "user", "content": f"Question:\n{redacted}\n\nLedger excerpts:\n{excerpts}"},
            ]
        )
        message = llm.message_from_response(payload)
    except llm.LLMError:
        return None
    content = (message.get("content") or "").strip()
    if not content:
        return None
    leaked, _counts = redact_text(content, extra_literals=sensitive_literals())
    if leaked != content:
        return None
    for literal in sensitive_literals():
        if literal and literal in content:
            return None
    return content


def run_agent(prompt: str, *, provider: str | None = None) -> AgentResult:
    """Answer one user turn. Refusals never call ledger tools or the model."""
    decision = precheck(prompt)
    selected = llm.resolve_provider(provider)
    fallback = None
    results: list[dict] = []
    tool_names: list[str] = []

    if decision.action != "refuse":
        if selected == "nvidia":
            calls, fallback = _nvidia_calls(decision.redacted_text)
            if fallback:
                calls = plan(decision.redacted_text)
        else:
            calls = plan(decision.redacted_text)
        results, tool_names = _execute(calls)

    body = None
    if decision.action != "refuse" and selected == "nvidia" and fallback is None and results:
        phrased = _phrase(decision.redacted_text, results)
        if phrased:
            body = phrased
        else:
            fallback = "phrase_rejected"

    text = render(decision, results, body=body)
    redacted_text, extra = redact_text(text, extra_literals=sensitive_literals())
    if extra:
        merged = dict(decision.redactions)
        for key, count in extra.items():
            merged[key] = merged.get(key, 0) + count
        decision.redactions = merged
        text = render(decision, results, body=body)
        text, _again = redact_text(text, extra_literals=sensitive_literals())
    else:
        text = redacted_text

    policy_ids = _policy_ids(decision, results)
    answered_with_mock = selected == "mock" or fallback is not None
    result = AgentResult(
        text=text,
        action=decision.action,
        reasons=list(decision.reasons),
        redactions=dict(decision.redactions),
        tools=tool_names,
        policy_ids=policy_ids,
        provider="mock" if answered_with_mock else "nvidia",
        llm_fallback=fallback,
        guardrail=decision.as_dict(),
    )
    log_decision(
        {
            "action": result.action,
            "reasons": result.reasons,
            "redactions": result.redactions,
            "tools": result.tools,
            "policy_ids": result.policy_ids,
            "provider": result.provider,
            "llm_fallback": result.llm_fallback,
            "redacted_prompt": decision.redacted_text[:500],
        }
    )
    return result
