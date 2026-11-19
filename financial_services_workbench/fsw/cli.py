"""Call sample tools or ask the agent from the command line."""

from __future__ import annotations

import argparse
import json

from fsw.agent import run_agent
from fsw.tools import SIGNATURES, dispatch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Financial Services Workbench CLI (sample data).")
    sub = parser.add_subparsers(dest="command", required=True)

    call = sub.add_parser("call", help="Call one read-only tool")
    call.add_argument("name", choices=sorted(SIGNATURES))
    flags = sorted({key for keys in SIGNATURES.values() for key in keys})
    for key in flags:
        call.add_argument(f"--{key.replace('_', '-')}", default="", dest=key)

    ask = sub.add_parser("ask", help="Run one prompt through the guardrailed agent")
    ask.add_argument("prompt")
    ask.add_argument("--provider", default="", help="mock, nvidia, or empty for FS_LLM_PROVIDER")

    args = parser.parse_args(argv)
    if args.command == "call":
        arguments = {key: getattr(args, key) for key in SIGNATURES[args.name]}
        print(dispatch(args.name, arguments, as_json=True))
        return 0
    result = run_agent(args.prompt, provider=args.provider or None)
    print(result.text)
    print(json.dumps({k: v for k, v in result.as_dict().items() if k != "text"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
