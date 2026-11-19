"""NVIDIA OpenAI-compatible chat client, with an explicit mock fallback.

The API key is read from NVIDIA_API_KEY. It is never logged or written to disk.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"
TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "account_lookup",
            "description": "Look up a sample account by account_id or customer_id. Read-only demo ledger.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "Sample account id such as ACC-1001."},
                    "customer_id": {"type": "string", "description": "Sample customer id such as CUST-1001."},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transaction_search",
            "description": "Search sample transactions. Does not move money.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "merchant": {"type": "string"},
                    "txn_type": {"type": "string", "description": "card, cash, ach, or wire."},
                    "min_amount": {"type": "string"},
                    "max_amount": {"type": "string"},
                    "posted_on_or_after": {"type": "string", "description": "YYYY-MM-DD."},
                    "query": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kyc_aml_check",
            "description": "Read sample KYC status and AML flags. Cannot clear a flag.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "account_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "policy_lookup",
            "description": "Quote a sample policy excerpt about KYC, AML, payments, privacy, or fees.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "additionalProperties": False,
            },
        },
    },
]


class LLMError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def resolve_provider(requested: str | None = None) -> str:
    """Return mock or nvidia. An empty request uses FS_LLM_PROVIDER, then the key."""
    choice = (requested if requested is not None else os.environ.get("FS_LLM_PROVIDER", "")).strip().lower()
    if choice in {"mock", "nvidia"}:
        return choice
    if os.environ.get("NVIDIA_API_KEY", "").strip():
        return "nvidia"
    return "mock"


def chat(messages: list[dict], *, tools: list[dict] | None = None, timeout: float = 45) -> dict:
    """Call the NVIDIA chat completions endpoint. Raises LLMError on failure."""
    key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not key:
        raise LLMError("missing_api_key", "NVIDIA_API_KEY is not set")
    base = os.environ.get("NVIDIA_API_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    model = os.environ.get("NVIDIA_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    payload: dict = {"model": model, "messages": messages, "temperature": 0, "max_tokens": 800}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "financial-services-workbench/0.1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise LLMError(f"http_{exc.code}", f"NVIDIA request failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise LLMError("network", "NVIDIA request failed before a response") from exc
    except TimeoutError as exc:
        raise LLMError("timeout", "NVIDIA request timed out") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError("bad_response", "NVIDIA response was not JSON") from exc


def message_from_response(payload: dict) -> dict:
    try:
        return payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError("bad_response", "NVIDIA response had no assistant message") from exc


def tool_calls_from_message(message: dict) -> list[dict]:
    calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        raw = function.get("arguments") or {}
        if isinstance(raw, str):
            try:
                arguments = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError:
                arguments = {}
        elif isinstance(raw, dict):
            arguments = raw
        else:
            arguments = {}
        name = function.get("name") or ""
        if name:
            calls.append({"name": name, "arguments": arguments})
    return calls
