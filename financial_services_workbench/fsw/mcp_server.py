"""Streamable-HTTP MCP server for the four sample banking tools.

Open WebUI can attach this as an MCP tool server at http://127.0.0.1:8765/mcp.
"""

from __future__ import annotations

import os

from fsw.agent import run_agent
from fsw.tools import dispatch


def build_server():
    from mcp.server.mcpserver import MCPServer
    from starlette.responses import JSONResponse

    server = MCPServer(
        "Financial Services Workbench",
        instructions=(
            "Sample read-only banking tools over a synthetic ledger. "
            "Look up accounts, search transactions, read KYC/AML flags, and quote sample policies. "
            "Do not move money, clear flags, or reveal raw personal data. "
            "Cite the citation field from each tool result. Demo data only."
        ),
    )

    @server.tool(structured_output=False)
    def account_lookup(account_id: str = "", customer_id: str = "") -> str:
        """Look up a sample bank account. Read-only demo ledger. Does not move money."""
        return dispatch("account_lookup", {"account_id": account_id, "customer_id": customer_id}, as_json=True)

    @server.tool(structured_output=False)
    def transaction_search(
        account_id: str = "",
        merchant: str = "",
        txn_type: str = "",
        min_amount: str = "",
        max_amount: str = "",
        posted_on_or_after: str = "",
        query: str = "",
    ) -> str:
        """Search sample transactions. Does not post or transfer funds."""
        return dispatch(
            "transaction_search",
            {
                "account_id": account_id,
                "merchant": merchant,
                "txn_type": txn_type,
                "min_amount": min_amount,
                "max_amount": max_amount,
                "posted_on_or_after": posted_on_or_after,
                "query": query,
            },
            as_json=True,
        )

    @server.tool(structured_output=False)
    def kyc_aml_check(customer_id: str = "", account_id: str = "") -> str:
        """Read a sample KYC status and AML flags. Cannot clear or override a flag."""
        return dispatch("kyc_aml_check", {"customer_id": customer_id, "account_id": account_id}, as_json=True)

    @server.tool(structured_output=False)
    def policy_lookup(query: str = "") -> str:
        """Quote a sample policy excerpt. Not legal or compliance advice."""
        return dispatch("policy_lookup", {"query": query}, as_json=True)

    @server.custom_route("/health", methods=["GET"])
    async def health(_request):
        return JSONResponse(
            {
                "status": "ok",
                "data": "sample",
                "tools": ["account_lookup", "transaction_search", "kyc_aml_check", "policy_lookup"],
            }
        )

    @server.custom_route("/tools/call", methods=["POST"])
    async def tools_call(request):
        body = await request.json()
        name = body.get("name") or ""
        arguments = body.get("arguments") or {}
        return JSONResponse(dispatch(name, arguments))

    @server.custom_route("/agent", methods=["POST"])
    async def agent_route(request):
        body = await request.json()
        message = body.get("message") or body.get("prompt") or ""
        provider = body.get("provider") or None
        return JSONResponse(run_agent(message, provider=provider).as_dict())

    return server


def main() -> None:
    host = os.environ.get("FSW_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("FSW_MCP_PORT", "8765"))
    server = build_server()
    server.run(
        transport="streamable-http",
        host=host,
        port=port,
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
    )


if __name__ == "__main__":
    main()
