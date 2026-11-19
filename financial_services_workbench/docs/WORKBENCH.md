# Financial Services Agent Workbench

Sample add-on for a read-only banking assistant. The ledger, customers, and policies are synthetic. Nothing here is a real account, a real customer, or compliance advice.

The demo is the shape of work a forward-deployed engineer walks through with a bank or insurer: tools over a system of record, an MCP server, a guardrail in front of the model, and an eval loop with a pass/fail scorecard. It is a personal learning demo on this fork. It is not a production deployment and it does not claim prior client delivery.

## What it adds

- Four read-only tools: `account_lookup`, `transaction_search`, `kyc_aml_check`, `policy_lookup`.
- A guardrail that redacts sample PII, refuses money movement, refuses AML/KYC flag changes, refuses requests for a full SSN or card number, and attaches a citation on every answer.
- The same tools over streamable HTTP MCP at `http://127.0.0.1:8765/mcp`.
- Open WebUI adapters in `openwebui/`: a pipe (the agent shows up as a model), a tool class, and a filter. The pipe puts a `**Guardrail**` banner in the assistant message. The filter rewrites an out-of-policy reply before it is saved, which is how the decision shows up in chat.
- An eval of 17 prompts. `python evals/run_eval.py` writes `evals/out/scorecard.md` and `evals/out/scorecard.json`.

## Architecture

```text
user message
  -> guardrail (redact PII, or refuse with a policy id)
  -> tool router
       mock: keyword planner
       nvidia: NVIDIA chat completions with tools
       if the key is missing or the call fails: the planner
  -> sample ledger (masked fields only)
  -> answer with a guardrail banner and a Sources block
```

Refusals never call the ledger and never call the model. Tool results omit SSN, email, phone, date of birth, and card number. The guardrail log stores the redacted prompt only (`logs/guardrail.jsonl`).

LLM provider:

| Env | Role |
| --- | --- |
| `FS_LLM_PROVIDER` | `mock` (default when no key) or `nvidia` |
| `NVIDIA_API_KEY` | Placeholder in the repo `.env.example`. Never commit a key. |
| `NVIDIA_API_BASE_URL` | `https://integrate.api.nvidia.com/v1` |
| `NVIDIA_MODEL` | `meta/llama-3.3-70b-instruct` |

## Run

From this folder, Python 3.12, no API key:

```bash
python evals/run_eval.py
python -m fsw.cli call account_lookup --account-id ACC-1001
python -m fsw.cli ask "What is the AML status of account ACC-4001?"
```

MCP server (needs `pip install -r requirements.txt`, which pins `mcp==2.3.0`):

```bash
python -m fsw.mcp_server
```

Then point Open WebUI at `http://127.0.0.1:8765/mcp`. Health check: `http://127.0.0.1:8765/health`.

Docker, from the repo root:

```bash
docker compose -f financial_services_workbench/docker-compose.yaml up --build
```

The container defaults to `FS_LLM_PROVIDER=mock`. Pass `NVIDIA_API_KEY` in the environment if you want the NVIDIA path. A missing key or a failed call falls back to the mock planner, and the scorecard records `llm_fallback`.

## Open WebUI

This fork inserts `financial_services_workbench` on `sys.path` when `backend/open_webui/main.py` loads. After that:

1. Workspace → Functions: paste `openwebui/financial_services_pipe.py`, enable it, and pick **Financial Services Agent** in the model list. The reply includes the guardrail banner. A status line `Guardrail: allow` or `Guardrail: refuse` is emitted when the chat socket is connected.
2. Workspace → Tools: paste `openwebui/financial_services_tool.py` and attach it to a model. Each tool result includes a `guardrail` object and a `citation`.
3. Workspace → Functions: paste `openwebui/financial_services_filter.py` and enable it. Inlet redacts PII. Outlet replaces an assistant reply that tried to move money, clear a flag, or reveal raw personal data.
4. Admin settings → tool servers: add an MCP server at `http://127.0.0.1:8765/mcp` (from another container, `http://host.docker.internal:8765/mcp`).

The full Open WebUI image was not booted for this change. The pipe, tool, and filter were loaded the same way Open WebUI execs a function file, and the eval calls them.

## Verified mock run

`python evals/run_eval.py` with no `NVIDIA_API_KEY`: **17/17 prompts, 22/22 checks**. The extra checks are tool-output PII masking, the pipe, the tool class, the filter, and the NVIDIA fallback (`llm_fallback=missing_api_key`, sample balance still present).

Regenerate the scorecard locally. `evals/out/` is gitignored.

![Mock pipe replies: an allowed balance lookup and a refused transfer](chat-preview.svg)

The image is the assistant text the pipe returns. It is not a capture of the Open WebUI shell.

## Limits

- Sample ledger `sample-ledger-v1` only. Names such as Jane Q. Demo are fixtures.
- No payments, no case management, no real KYC vendor, no core banking connection.
- The mock path is the one the scorecard gates. The NVIDIA path is implemented and used when `FS_LLM_PROVIDER=nvidia` and `NVIDIA_API_KEY` is set. This workspace had no key, so that path was checked only through the fallback.
- Not legal, regulatory, or compliance advice.
