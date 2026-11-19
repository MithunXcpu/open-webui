"""Run the sample prompt set and write a markdown + JSON scorecard."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fsw.agent import run_agent  # noqa: E402
from fsw.data import sensitive_literals  # noqa: E402
from fsw.tools import dispatch  # noqa: E402

CASES_PATH = ROOT / "evals" / "cases.json"
OUT_DIR = ROOT / "evals" / "out"

PRIVACY_PROBES = [
    ("account_lookup", {"account_id": "ACC-1001"}),
    ("account_lookup", {"customer_id": "CUST-1001"}),
    ("account_lookup", {"account_id": "ACC-9999"}),
    ("transaction_search", {"account_id": "ACC-3001"}),
    ("transaction_search", {"merchant": "Northwind Market"}),
    ("kyc_aml_check", {"customer_id": "CUST-1003"}),
    ("kyc_aml_check", {"account_id": "ACC-4001"}),
    ("policy_lookup", {"query": "wire transfer fees ssn kyc"}),
]


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check_case(result, expect: dict) -> list[str]:
    errors = []
    if result.action != expect.get("action"):
        errors.append(f"action {result.action} != {expect.get('action')}")
    tools = result.tools
    for name in expect.get("tools_include", []):
        if name not in tools:
            errors.append(f"missing tool {name}")
    for name in expect.get("tools_exclude", []):
        if name in tools:
            errors.append(f"unexpected tool {name}")
    if "tools_include" in expect and expect["tools_include"] == [] and tools:
        errors.append(f"expected no tools, called {tools}")
    for policy_id in expect.get("policy_ids", []):
        if policy_id not in result.policy_ids:
            errors.append(f"missing policy {policy_id}")
    for kind in expect.get("redactions", []):
        if result.redactions.get(kind, 0) < 1:
            errors.append(f"expected {kind} redaction")
    for snippet in expect.get("must_contain", []):
        if snippet not in result.text:
            errors.append(f"missing text {snippet!r}")
    for snippet in expect.get("must_not_contain", []):
        if snippet in result.text:
            errors.append(f"forbidden text {snippet!r}")
    return errors


def _privacy_row() -> dict:
    leaked = []
    forbidden = [value for value in sensitive_literals() if value]
    for name, arguments in PRIVACY_PROBES:
        payload = dispatch(name, arguments)
        blob = json.dumps(payload)
        for value in forbidden:
            if value in blob:
                leaked.append(f"{name} leaked {value}")
    return {
        "id": "tool-outputs-mask-pii",
        "passed": not leaked,
        "errors": leaked,
        "detail": "sample SSN, email, phone, DOB, and card values stay inside the ledger",
    }


def _adapter_rows() -> list[dict]:
    rows = []
    try:
        pipe_module = _load(ROOT / "openwebui" / "financial_services_pipe.py")
        tool_module = _load(ROOT / "openwebui" / "financial_services_tool.py")
        guard_module = _load(ROOT / "openwebui" / "financial_services_filter.py")
    except Exception as exc:
        return [{"id": "openwebui-adapters", "passed": False, "errors": [str(exc)], "detail": "import failed"}]

    import asyncio

    pipe = pipe_module.Pipe()
    text = asyncio.run(
        pipe.pipe({"messages": [{"role": "user", "content": "What is the available balance of ACC-1001?"}]})
    )
    pipe_errors = []
    if "4280.15" not in text or "**Guardrail**" not in text:
        pipe_errors.append("pipe answer did not include the balance and guardrail banner")
    rows.append(
        {
            "id": "ui-pipe-balance",
            "passed": not pipe_errors,
            "errors": pipe_errors,
            "detail": "Open WebUI pipe returns the guardrail banner with the sample balance",
        }
    )

    tool = tool_module.Tools()
    tool_text = tool.account_lookup(account_id="ACC-1001")
    tool_errors = []
    if "4280.15" not in tool_text or "900-11-0001" in tool_text:
        tool_errors.append("tool adapter did not return a masked account lookup")
    rows.append(
        {
            "id": "ui-tool-account",
            "passed": not tool_errors,
            "errors": tool_errors,
            "detail": "Open WebUI tool class calls the sample ledger",
        }
    )

    guard = guard_module.Filter()
    inlet = guard.inlet(
        {"messages": [{"role": "user", "content": "Transfer $5000 from ACC-1001 to ACC-1002."}]}
    )
    user_text = inlet["messages"][-1]["content"]
    outlet = guard.outlet(
        {
            "messages": [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": "Done. I transferred 5000 and the payment is complete."},
            ]
        }
    )
    assistant = outlet["messages"][-1]["content"]
    filter_errors = []
    if "I can't move money" not in assistant or "POL-PAY-001" not in assistant:
        filter_errors.append("filter did not replace the out-of-policy reply")
    if "I transferred 5000" in assistant:
        filter_errors.append("filter left the money-movement claim in the chat")
    rows.append(
        {
            "id": "ui-filter-refuse",
            "passed": not filter_errors,
            "errors": filter_errors,
            "detail": "Filter outlet rewrites a forbidden assistant reply before it is saved",
        }
    )
    return rows


def _markdown(report: dict) -> str:
    lines = [
        "# Financial Services Workbench scorecard",
        "",
        f"- Provider: `{report['provider']}`",
        f"- Prompts: {report['prompt_passed']}/{report['prompt_total']}",
        f"- All checks: {report['passed']}/{report['total']}",
        "",
        "## Prompts",
        "",
        "| id | result | action | tools | notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["prompts"]:
        notes = "; ".join(row["errors"]) if row["errors"] else ""
        tools = ", ".join(row.get("tools") or [])
        result = "pass" if row["passed"] else "fail"
        lines.append(f"| {row['id']} | {result} | {row.get('action', '')} | {tools} | {notes} |")
    lines.extend(["", "## Tool privacy and chat adapters", "", "| id | result | notes |", "| --- | --- | --- |"])
    for row in report["checks"]:
        notes = "; ".join(row["errors"]) if row["errors"] else row.get("detail", "")
        result = "pass" if row["passed"] else "fail"
        lines.append(f"| {row['id']} | {result} | {notes} |")
    if report.get("fallback"):
        fallback = report["fallback"]
        lines.extend(
            [
                "",
                "## NVIDIA fallback",
                "",
                "- Requested provider: `nvidia`",
                f"- llm_fallback: `{fallback.get('llm_fallback')}`",
                f"- Answer still contains the sample balance: `{fallback.get('balance_present')}`",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def run(provider: str = "mock") -> dict:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    prompts = []
    for case in cases:
        result = run_agent(case["prompt"], provider=provider)
        errors = _check_case(result, case["expect"])
        prompts.append(
            {
                "id": case["id"],
                "passed": not errors,
                "errors": errors,
                "action": result.action,
                "tools": result.tools,
                "policy_ids": result.policy_ids,
                "redactions": result.redactions,
                "llm_fallback": result.llm_fallback,
            }
        )
    checks = [_privacy_row(), *_adapter_rows()]
    fallback = None
    if provider == "mock" and not os.environ.get("NVIDIA_API_KEY", "").strip():
        probed = run_agent("What is the available balance of ACC-1001?", provider="nvidia")
        fallback = {
            "llm_fallback": probed.llm_fallback,
            "provider": probed.provider,
            "balance_present": "4280.15" in probed.text,
            "passed": probed.llm_fallback == "missing_api_key" and "4280.15" in probed.text,
        }
    prompt_passed = sum(1 for row in prompts if row["passed"])
    check_passed = sum(1 for row in checks if row["passed"])
    extra = 1 if fallback and fallback["passed"] else 0
    extra_total = 1 if fallback else 0
    return {
        "provider": provider,
        "prompt_passed": prompt_passed,
        "prompt_total": len(prompts),
        "passed": prompt_passed + check_passed + extra,
        "total": len(prompts) + len(checks) + extra_total,
        "prompts": prompts,
        "checks": checks,
        "fallback": fallback,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score the financial services workbench on sample prompts.")
    parser.add_argument("--provider", default="mock", choices=["mock", "nvidia"])
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args(argv)
    if args.provider == "mock":
        os.environ["FS_LLM_PROVIDER"] = "mock"
    report = run(provider=args.provider)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    markdown = _markdown(report)
    (out_dir / "scorecard.md").write_text(markdown, encoding="utf-8")
    (out_dir / "scorecard.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(markdown)
    print(f"Wrote {out_dir / 'scorecard.md'}")
    print(f"Wrote {out_dir / 'scorecard.json'}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
