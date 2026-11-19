"""Deterministic guardrails for the sample banking assistant.

PII is masked before a model sees it. Money movement, AML overrides, and
requests for raw personal data are refused with a policy citation. The
assistant never executes those actions because no such tool exists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from fsw.data import POLICY_TITLES

SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b\d{3}-\d{3}-\d{4}\b")
CARD_RE = re.compile(r"\b(?:\d{4}[ -]){3}\d{4}\b")

POLICY_QUESTION_RE = re.compile(
    r"("
    r"\bpolic(?:y|ies)\b"
    r"|\bfee schedule\b"
    r"|\bwhat are the fees\b"
    r"|\bwhich documents\b"
    r"|\bam i allowed\b"
    r"|\bare we allowed\b"
    r")",
    re.IGNORECASE,
)
MONEY_RE = re.compile(
    r"\b("
    r"transfers?"
    r"|wires?"
    r"|send (?:the )?money"
    r"|move (?:the )?(?:money|funds|\d)"
    r"|make a payment"
    r"|initiate (?:a |the )?(?:payment|transfer|wire)"
    r"|withdraw"
    r"|pay (?:\$|\d)"
    r")",
    re.IGNORECASE,
)
EXECUTION_RE = re.compile(
    r"("
    r"\$\s?\d"
    r"|\b\d[\d,]*(?:\.\d+)?\s*(?:usd|dollars)\b"
    r"|\bfrom\b.+\bto\b"
    r"|\bto account\b"
    r"|\brouting\b"
    r"|\bsubmit\b"
    r"|\bexecute\b"
    r"|\bgo ahead\b"
    r")",
    re.IGNORECASE,
)
BYPASS_RE = re.compile(
    r"\b(?:"
    r"(?:clear|disable|remove|override|waive|lift|bypass|ignore|delete|close)"
    r" (?:the |this |an |their )?"
    r"(?:aml|kyc|flag|flags|hold|sanction|sanctions|restriction|alert)"
    r"|turn off (?:the |this |an )?(?:aml|kyc|flag|flags|hold|alert)"
    r")\b",
    re.IGNORECASE,
)
REVEAL_RE = re.compile(
    r"\b("
    r"full ssn"
    r"|social security"
    r"|unredacted"
    r"|unmasked"
    r"|date of birth"
    r"|full card"
    r"|card number"
    r"|cvv"
    r"|show (?:me )?(?:the )?(?:full )?(?:ssn|social)"
    r")",
    re.IGNORECASE,
)

CAPABILITIES = (
    "This sample assistant can look up a sample account, search sample transactions, "
    "check a sample KYC or AML flag, and quote a sample policy excerpt. "
    "It cannot move money, clear a flag, or reveal full personal data."
)


@dataclass
class Decision:
    action: str
    reasons: list[str] = field(default_factory=list)
    policy_ids: list[str] = field(default_factory=list)
    redactions: dict[str, int] = field(default_factory=dict)
    redacted_text: str = ""

    def as_dict(self) -> dict:
        return {
            "action": self.action,
            "reasons": list(self.reasons),
            "policy_ids": list(self.policy_ids),
            "redactions": dict(self.redactions),
        }


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not local or not domain:
        return "[REDACTED-EMAIL]"
    return f"{local[0]}***@{domain}"


def mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    last4 = digits[-4:] if len(digits) >= 4 else "0000"
    return f"***-***-{last4}"


def redact_text(text: str, extra_literals: list[str] | None = None) -> tuple[str, dict[str, int]]:
    """Replace personal data with stable tokens. Counts are by pattern family."""
    counts: dict[str, int] = {}

    def _sub(pattern: re.Pattern[str], token: str, value: str) -> str:
        matches = pattern.findall(value)
        if matches:
            counts[token] = counts.get(token, 0) + len(matches)
            return pattern.sub(f"[REDACTED-{token.upper()}]", value)
        return value

    redacted = text or ""
    redacted = _sub(EMAIL_RE, "email", redacted)
    redacted = _sub(SSN_RE, "ssn", redacted)
    redacted = _sub(PHONE_RE, "phone", redacted)
    redacted = _sub(CARD_RE, "card", redacted)
    for literal in extra_literals or []:
        if literal and literal in redacted:
            redacted = redacted.replace(literal, "[REDACTED-DOB]")
            counts["dob"] = counts.get("dob", 0) + 1
    return redacted, counts


def _add_reason(decision: Decision, reason: str, policy_id: str) -> None:
    if reason not in decision.reasons:
        decision.reasons.append(reason)
    if policy_id not in decision.policy_ids:
        decision.policy_ids.append(policy_id)
    decision.action = "refuse"


def precheck(text: str) -> Decision:
    """Refuse out-of-policy requests and redact PII in the text a model may see."""
    from fsw.data import sensitive_literals

    dobs = [row for row in sensitive_literals() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", row)]
    redacted, counts = redact_text(text or "", extra_literals=dobs)
    decision = Decision(action="allow", redactions=counts, redacted_text=redacted)
    if BYPASS_RE.search(redacted):
        _add_reason(decision, "AML or KYC flag changes are out of policy", "POL-AML-001")
    if REVEAL_RE.search(redacted):
        _add_reason(decision, "revealing raw personal data is out of policy", "POL-PII-001")
    if MONEY_RE.search(redacted):
        policy_question = POLICY_QUESTION_RE.search(redacted) is not None
        execution = EXECUTION_RE.search(redacted) is not None
        if execution or not policy_question:
            _add_reason(decision, "money movement is out of policy", "POL-PAY-001")
    return decision


def redaction_phrase(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{name} {counts[name]}" for name in sorted(counts))


def banner(decision: Decision) -> str:
    redacted = redaction_phrase(decision.redactions)
    if decision.action == "refuse":
        return (
            "**Guardrail** · refuse\n"
            f"- Reason: {'; '.join(decision.reasons)}\n"
            f"- Policy: {', '.join(decision.policy_ids)}\n"
            f"- PII redacted: {redacted}\n"
            "- Ledger tools were not called"
        )
    return (
        "**Guardrail** · allow\n"
        f"- PII redacted: {redacted}\n"
        "- Scope: read-only sample servicing\n"
        "- Citations: attached"
    )


def refusal_body(decision: Decision) -> str:
    sentences = []
    if "POL-PAY-001" in decision.policy_ids:
        sentences.append(
            "I can't move money, submit a transfer, or send a wire. "
            "This sample assistant is read-only. Use the bank's official payment channel."
        )
    if "POL-AML-001" in decision.policy_ids:
        sentences.append(
            "I can't clear, disable, or override an AML or KYC flag. "
            "Open flags stay with the investigations queue."
        )
    if "POL-PII-001" in decision.policy_ids:
        sentences.append(
            "I can't reveal a full Social Security number, card number, date of birth, or other raw personal data."
        )
    if not sentences:
        sentences.append("I can't do that. It is outside this sample assistant's read-only policy.")
    cited = " ".join(decision.policy_ids)
    return " ".join(sentences) + f" {cited}."


def source_lines(decision: Decision, results: list[dict]) -> list[str]:
    if decision.action == "refuse":
        lines = []
        for policy_id in decision.policy_ids:
            title = POLICY_TITLES.get(policy_id, "sample policy")
            lines.append(f"- [policy:{policy_id}] {title}")
        return lines or ["- [workbench] refusal with no policy id"]
    if not results:
        return ["- [workbench] capability statement"]
    lines = []
    seen = set()
    for result in results:
        citations = result.get("citations") or [result.get("citation") or "[workbench] missing citation"]
        for citation in citations:
            line = f"- {citation}"
            if line not in seen:
                seen.add(line)
                lines.append(line)
    return lines


def render(decision: Decision, results: list[dict], body: str | None = None) -> str:
    """Assemble the chat message: guardrail banner, answer, required citations."""
    if body is None:
        if decision.action == "refuse":
            body = refusal_body(decision)
        elif not results:
            body = CAPABILITIES
        else:
            body = "\n\n".join(result.get("summary") or "No sample summary." for result in results)
    sources = "\n".join(source_lines(decision, results))
    return f"{banner(decision)}\n\n{body.strip()}\n\nSources:\n{sources}\n"
