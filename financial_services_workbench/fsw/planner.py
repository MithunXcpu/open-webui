"""Rule-based tool router used by the mock provider and as the NVIDIA fallback."""

from __future__ import annotations

import re

from fsw.data import CUSTOMERS, MERCHANTS

CAPABILITY_RE = re.compile(
    r"\b(what can (?:this|you)|how can you help|what do you do|help a banker|what can this sample)\b",
    re.IGNORECASE,
)
POLICY_RE = re.compile(r"\b(policy|policies|fee|fees|schedule)\b", re.IGNORECASE)
KYC_RE = re.compile(r"\b(kyc|aml|sanction|sanctions|risk|flag|flags|standing|onboard|pep)\b", re.IGNORECASE)
TXN_RE = re.compile(
    r"\b(transaction|transactions|deposit|deposits|withdrawal|merchant|purchase|purchases|spent|cash|card)\b",
    re.IGNORECASE,
)
ACCOUNT_RE = re.compile(r"\b(balance|status|holder|who owns|standing)\b", re.IGNORECASE)
ACCOUNT_ID_RE = re.compile(r"\bACC-\d+\b", re.IGNORECASE)
CUSTOMER_ID_RE = re.compile(r"\bCUST-\d+\b", re.IGNORECASE)
MIN_AMOUNT_RE = re.compile(
    r"(?:over|above|at least|minimum of|>=)\s*\$?\s*(\d[\d,]*(?:\.\d+)?)"
    r"|\$?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:or more|or above|and above)",
    re.IGNORECASE,
)


def _ids(pattern: re.Pattern[str], text: str) -> list[str]:
    seen = []
    for match in pattern.findall(text):
        value = match.upper()
        if value not in seen:
            seen.append(value)
    return seen


def _customer_from_name(text: str) -> str:
    lowered = text.lower()
    for customer in CUSTOMERS.values():
        if customer["display_name"].lower() in lowered:
            return customer["customer_id"]
    return ""


def plan(prompt: str) -> list[dict]:
    """Choose read-only tools. Returns a list of {name, arguments} calls."""
    text = prompt or ""
    account_ids = _ids(ACCOUNT_ID_RE, text)
    customer_ids = _ids(CUSTOMER_ID_RE, text)
    named = _customer_from_name(text)
    if named and named not in customer_ids:
        customer_ids.append(named)
    stripped = ACCOUNT_ID_RE.sub(" ", text)
    stripped = CUSTOMER_ID_RE.sub(" ", stripped)

    if CAPABILITY_RE.search(text) and not account_ids and not customer_ids:
        return []

    wants_policy = POLICY_RE.search(text) is not None
    wants_kyc = KYC_RE.search(text) is not None
    wants_txn = TXN_RE.search(text) is not None
    asks_account = ACCOUNT_RE.search(text) is not None

    if wants_policy and not (wants_kyc or wants_txn or account_ids or customer_ids):
        return [{"name": "policy_lookup", "arguments": {"query": text}}]

    calls: list[dict] = []
    if wants_policy:
        calls.append({"name": "policy_lookup", "arguments": {"query": text}})

    if account_ids and (asks_account or (not wants_txn and not wants_kyc)):
        for account_id in account_ids:
            calls.append({"name": "account_lookup", "arguments": {"account_id": account_id}})
    elif customer_ids and asks_account and not account_ids:
        calls.append({"name": "account_lookup", "arguments": {"customer_id": customer_ids[0]}})

    if wants_kyc and (customer_ids or account_ids):
        if customer_ids and not account_ids:
            calls.append({"name": "kyc_aml_check", "arguments": {"customer_id": customer_ids[0]}})
        else:
            calls.append({"name": "kyc_aml_check", "arguments": {"account_id": account_ids[0]}})

    if wants_txn:
        arguments: dict[str, str] = {}
        if account_ids:
            arguments["account_id"] = account_ids[0]
        elif customer_ids:
            arguments["query"] = customer_ids[0]
        for merchant in MERCHANTS:
            if merchant.lower() in text.lower():
                arguments["merchant"] = merchant
                break
        if re.search(r"\bcash\b", text, re.IGNORECASE):
            arguments["txn_type"] = "cash"
        elif re.search(r"\bcard\b", text, re.IGNORECASE):
            arguments["txn_type"] = "card"
        elif re.search(r"\bach\b", text, re.IGNORECASE):
            arguments["txn_type"] = "ach"
        amount = MIN_AMOUNT_RE.search(stripped)
        if amount:
            arguments["min_amount"] = next(group for group in amount.groups() if group)
        calls.append({"name": "transaction_search", "arguments": arguments})

    deduped = []
    seen = set()
    for call in calls:
        key = (call["name"], tuple(sorted(call["arguments"].items())))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(call)
    return deduped
