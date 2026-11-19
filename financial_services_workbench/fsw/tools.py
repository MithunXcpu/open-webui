"""Read-only tools over the sample ledger. Raw personal data never leaves this module."""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation

from fsw.data import ACCOUNTS, CUSTOMERS, DATA_VERSION, DISCLAIMER, POLICIES, TRANSACTIONS
from fsw.guardrails import mask_email, mask_phone

READ_ONLY_GUARDRAIL = {
    "action": "allow",
    "mode": "read_only",
    "pii": "masked",
    "note": "This tool cannot move money, change a flag, or return raw personal data.",
}


def dumps(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _base(tool: str, *, ok: bool, summary: str, citation: str, matches: list, citations: list[str] | None = None) -> dict:
    return {
        "ok": ok,
        "tool": tool,
        "disclaimer": DISCLAIMER,
        "data_version": DATA_VERSION,
        "guardrail": dict(READ_ONLY_GUARDRAIL),
        "summary": summary,
        "citation": citation,
        "citations": citations or [citation],
        "matches": matches,
    }


def _amount(value: str) -> Decimal | None:
    text = (value or "").strip().replace(",", "").replace("$", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _public_customer(customer: dict) -> dict:
    return {
        "customer_id": customer["customer_id"],
        "display_name": customer["display_name"],
        "masked_email": mask_email(customer["email"]),
        "masked_phone": mask_phone(customer["phone"]),
        "kyc_status": customer["kyc_status"],
        "risk_rating": customer["risk_rating"],
        "pep": customer["pep"],
        "sanctions": customer["sanctions"],
        "aml_flags": list(customer["aml_flags"]),
    }


def _standing_sentence(account: dict) -> str:
    if account["status"] != "open" or account["restriction"]:
        return "This sample account is not in good standing."
    return "This sample account is in good standing."


def _account_sentence(account: dict) -> str:
    customer = CUSTOMERS[account["customer_id"]]
    restriction = f" ({account['restriction']})" if account["restriction"] else ""
    return (
        f"Sample account {account['account_id']} ({account['type']}) is {account['status']}{restriction}. "
        f"Available balance: {account['available_balance']} {account['currency']}. "
        f"Sample holder: {customer['display_name']} ({customer['customer_id']}). "
        f"{_standing_sentence(account)}"
    )


def _public_account(account: dict) -> dict:
    customer = CUSTOMERS[account["customer_id"]]
    return {
        "account_id": account["account_id"],
        "customer_id": account["customer_id"],
        "display_name": customer["display_name"],
        "masked_email": mask_email(customer["email"]),
        "masked_phone": mask_phone(customer["phone"]),
        "type": account["type"],
        "status": account["status"],
        "available_balance": account["available_balance"],
        "currency": account["currency"],
        "restriction": account["restriction"],
        "standing": "good" if account["status"] == "open" and not account["restriction"] else "not_good",
    }


def account_lookup(account_id: str = "", customer_id: str = "") -> dict:
    """Look up one or more sample accounts.

    Balances and statuses come from the demo ledger. Email and phone are masked.
    """
    account_id = (account_id or "").strip().upper()
    customer_id = (customer_id or "").strip().upper()
    if account_id:
        account = ACCOUNTS.get(account_id)
        if not account:
            summary = f"No sample account {account_id} is on this ledger."
            citation = f"[tool:account_lookup] {account_id} {DATA_VERSION}"
            return _base("account_lookup", ok=False, summary=summary, citation=citation, matches=[])
        summary = _account_sentence(account)
        citation = f"[tool:account_lookup] {account['account_id']} {DATA_VERSION}"
        return _base(
            "account_lookup",
            ok=True,
            summary=summary,
            citation=citation,
            matches=[{**_public_account(account)}],
        )
    if customer_id:
        rows = [row for row in ACCOUNTS.values() if row["customer_id"] == customer_id]
        if customer_id not in CUSTOMERS or not rows:
            summary = f"No sample accounts for {customer_id} are on this ledger."
            citation = f"[tool:account_lookup] {customer_id} {DATA_VERSION}"
            return _base("account_lookup", ok=False, summary=summary, citation=citation, matches=[])
        summary = " ".join(_account_sentence(row) for row in rows)
        citations = [f"[tool:account_lookup] {row['account_id']} {DATA_VERSION}" for row in rows]
        return _base(
            "account_lookup",
            ok=True,
            summary=summary,
            citation=citations[0],
            citations=citations,
            matches=[_public_account(row) for row in rows],
        )
    summary = "Provide an account_id such as ACC-1001 or a customer_id such as CUST-1001."
    citation = f"[tool:account_lookup] missing id {DATA_VERSION}"
    return _base("account_lookup", ok=False, summary=summary, citation=citation, matches=[])


def transaction_search(
    account_id: str = "",
    merchant: str = "",
    txn_type: str = "",
    min_amount: str = "",
    max_amount: str = "",
    posted_on_or_after: str = "",
    query: str = "",
) -> dict:
    """Search sample transactions. This does not post, reverse, or transfer funds."""
    account_id = (account_id or "").strip().upper()
    merchant = (merchant or "").strip().lower()
    txn_type = (txn_type or "").strip().lower()
    query = (query or "").strip().lower()
    posted_on_or_after = (posted_on_or_after or "").strip()
    floor = _amount(min_amount)
    ceiling = _amount(max_amount)
    if account_id and account_id not in ACCOUNTS:
        summary = f"No sample account {account_id} is on this ledger, so there are no transactions."
        citation = f"[tool:transaction_search] {account_id} {DATA_VERSION}"
        return _base("transaction_search", ok=False, summary=summary, citation=citation, matches=[])

    matches = []
    for row in TRANSACTIONS:
        if account_id and row["account_id"] != account_id:
            continue
        if merchant and merchant not in row["merchant"].lower():
            continue
        if txn_type and row["type"] != txn_type:
            continue
        amount = Decimal(row["amount"])
        if floor is not None and amount < floor:
            continue
        if ceiling is not None and amount > ceiling:
            continue
        if posted_on_or_after and row["posted_on"] < posted_on_or_after:
            continue
        haystack = " ".join([row["merchant"], row["description"], row["transaction_id"], row["type"]]).lower()
        if query and query not in haystack:
            continue
        matches.append(dict(row))

    filters = []
    if account_id:
        filters.append(f"account {account_id}")
    if merchant:
        filters.append(f"merchant containing {merchant}")
    if txn_type:
        filters.append(f"type {txn_type}")
    if floor is not None:
        filters.append(f"amount at or above {floor}")
    if ceiling is not None:
        filters.append(f"amount at or below {ceiling}")
    if posted_on_or_after:
        filters.append(f"posted on or after {posted_on_or_after}")
    scope = ", ".join(filters) if filters else "the sample ledger"
    if not matches:
        summary = f"No sample transactions matched ({scope})."
    else:
        lines = [
            (
                f"- {row['transaction_id']} posted {row['posted_on']} {row['direction']} "
                f"{row['amount']} USD ({row['type']}, {row['merchant']})."
            )
            for row in matches
        ]
        summary = f"Sample transactions for {scope}:\n" + "\n".join(lines)
    label = account_id or "ledger"
    citation = f"[tool:transaction_search] {label} {DATA_VERSION}"
    return _base("transaction_search", ok=bool(matches), summary=summary, citation=citation, matches=matches)


def kyc_aml_check(customer_id: str = "", account_id: str = "") -> dict:
    """Read the sample KYC status and AML flags. This cannot clear or override a flag."""
    customer_id = (customer_id or "").strip().upper()
    account_id = (account_id or "").strip().upper()
    if not customer_id and account_id:
        account = ACCOUNTS.get(account_id)
        if not account:
            summary = f"No sample account {account_id} is on this ledger."
            citation = f"[tool:kyc_aml_check] {account_id} {DATA_VERSION}"
            return _base("kyc_aml_check", ok=False, summary=summary, citation=citation, matches=[])
        customer_id = account["customer_id"]
    customer = CUSTOMERS.get(customer_id)
    if not customer:
        summary = "Provide a customer_id such as CUST-1001 or an account_id such as ACC-1001."
        citation = f"[tool:kyc_aml_check] missing id {DATA_VERSION}"
        return _base("kyc_aml_check", ok=False, summary=summary, citation=citation, matches=[])

    public = _public_customer(customer)
    linked = [row["account_id"] for row in ACCOUNTS.values() if row["customer_id"] == customer_id]
    open_flags = [flag for flag in customer["aml_flags"] if flag["status"] == "open"]
    if open_flags:
        flag_text = " ".join(
            f"Open AML flag {flag['code']} is open: {flag['summary']}" for flag in open_flags
        )
    else:
        flag_text = "Open AML flags: none."
    onboard = ""
    if customer["kyc_status"] != "clear" or open_flags:
        onboard = " This sample customer is not clear to onboard."
    summary = (
        f"Sample KYC status for {customer['display_name']} ({customer_id}) is {customer['kyc_status']}. "
        f"Risk rating: {customer['risk_rating']}. {flag_text} "
        f"Sanctions screen: {customer['sanctions']}.{onboard}"
    ).strip()
    citation = f"[tool:kyc_aml_check] {customer_id} {DATA_VERSION}"
    public["linked_accounts"] = linked
    return _base("kyc_aml_check", ok=True, summary=summary, citation=citation, matches=[public])


def policy_lookup(query: str = "") -> dict:
    """Quote a sample policy excerpt. This is not legal, regulatory, or compliance advice."""
    query_text = query or ""
    scored: list[tuple[int, dict]] = []
    for policy in POLICIES:
        score = 0
        for topic in policy["topics"]:
            if re.search(rf"\b{re.escape(topic)}\b", query_text, re.IGNORECASE):
                score += 2
        scored.append((score, policy))
    scored.sort(key=lambda item: (-item[0], item[1]["policy_id"]))
    chosen = [policy for score, policy in scored if score > 0][:2]
    if not chosen:
        summary = "No sample policy matched that question. Ask about KYC, AML, payments, privacy, or fees."
        citation = f"[tool:policy_lookup] no match {DATA_VERSION}"
        return _base("policy_lookup", ok=False, summary=summary, citation=citation, matches=[])
    matches = [
        {"policy_id": policy["policy_id"], "title": policy["title"], "excerpt": policy["excerpt"]} for policy in chosen
    ]
    summary = "\n\n".join(
        f"Sample policy {policy['policy_id']} ({policy['title']}): {policy['excerpt']}" for policy in chosen
    )
    citations = [f"[tool:policy_lookup] {policy['policy_id']}" for policy in chosen]
    return _base(
        "policy_lookup",
        ok=True,
        summary=summary,
        citation=citations[0],
        citations=citations,
        matches=matches,
    )


FUNCTIONS = {
    "account_lookup": account_lookup,
    "transaction_search": transaction_search,
    "kyc_aml_check": kyc_aml_check,
    "policy_lookup": policy_lookup,
}

SIGNATURES = {
    "account_lookup": ("account_id", "customer_id"),
    "transaction_search": (
        "account_id",
        "merchant",
        "txn_type",
        "min_amount",
        "max_amount",
        "posted_on_or_after",
        "query",
    ),
    "kyc_aml_check": ("customer_id", "account_id"),
    "policy_lookup": ("query",),
}


def coerce_arguments(name: str, arguments: dict | None) -> dict:
    allowed = SIGNATURES.get(name, ())
    incoming = arguments or {}
    cleaned = {}
    for key in allowed:
        value = incoming.get(key, "")
        if value is None:
            value = ""
        cleaned[key] = str(value)
    return cleaned


def dispatch(name: str, arguments: dict | None = None, *, as_json: bool = False):
    if name not in FUNCTIONS:
        payload = _base(
            name or "unknown",
            ok=False,
            summary="That tool is not on this workbench.",
            citation="[workbench] unknown tool",
            matches=[],
        )
    else:
        payload = FUNCTIONS[name](**coerce_arguments(name, arguments))
    if as_json:
        header = (
            "Guardrail: read-only sample ledger. Cite the citation field. "
            "Do not move money or reveal raw personal data.\n"
        )
        return header + dumps(payload)
    return payload
