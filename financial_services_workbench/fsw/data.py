"""Synthetic bank ledger. Every row is demo data, not a customer record."""

DATA_VERSION = "sample-ledger-v1"
DISCLAIMER = "Synthetic demo data. Not a real customer, account, or bank record."

CUSTOMERS = {
    "CUST-1001": {
        "customer_id": "CUST-1001",
        "display_name": "Jane Q. Demo",
        "ssn": "900-11-0001",
        "email": "jane.demo@example.test",
        "phone": "555-010-1001",
        "dob": "1984-04-12",
        "card": "4000-0000-0000-1001",
        "kyc_status": "clear",
        "risk_rating": "low",
        "pep": False,
        "sanctions": "clear",
        "aml_flags": [],
    },
    "CUST-1002": {
        "customer_id": "CUST-1002",
        "display_name": "Marco V. Sample",
        "ssn": "900-22-0002",
        "email": "marco.sample@example.test",
        "phone": "555-010-2002",
        "dob": "1979-11-02",
        "card": "4000-0000-0000-2002",
        "kyc_status": "review",
        "risk_rating": "medium",
        "pep": False,
        "sanctions": "clear",
        "aml_flags": [
            {
                "code": "DOC-EXPIRED",
                "status": "open",
                "summary": "Sample identity document is past its review date.",
            }
        ],
    },
    "CUST-1003": {
        "customer_id": "CUST-1003",
        "display_name": "Alicia R. Fixture",
        "ssn": "900-33-0003",
        "email": "alicia.fixture@example.test",
        "phone": "555-010-3003",
        "dob": "1991-06-30",
        "card": "4000-0000-0000-3003",
        "kyc_status": "restricted",
        "risk_rating": "high",
        "pep": False,
        "sanctions": "no confirmed match",
        "aml_flags": [
            {
                "code": "STRUCTURING",
                "status": "open",
                "summary": "Sample pattern of cash deposits just under and over 10000 USD.",
            }
        ],
    },
    "CUST-1004": {
        "customer_id": "CUST-1004",
        "display_name": "Omar S. Example",
        "ssn": "900-44-0004",
        "email": "omar.example@example.test",
        "phone": "555-010-4004",
        "dob": "1988-01-19",
        "card": "4000-0000-0000-4004",
        "kyc_status": "pending",
        "risk_rating": "medium",
        "pep": False,
        "sanctions": "review",
        "aml_flags": [
            {
                "code": "SANCTIONS-REVIEW",
                "status": "open",
                "summary": "Sample sanctions screen is a possible match and is under review. Not a confirmed hit.",
            }
        ],
    },
}

ACCOUNTS = {
    "ACC-1001": {
        "account_id": "ACC-1001",
        "customer_id": "CUST-1001",
        "type": "checking",
        "status": "open",
        "available_balance": "4280.15",
        "currency": "USD",
        "restriction": "",
    },
    "ACC-1002": {
        "account_id": "ACC-1002",
        "customer_id": "CUST-1001",
        "type": "savings",
        "status": "open",
        "available_balance": "15200.00",
        "currency": "USD",
        "restriction": "",
    },
    "ACC-2001": {
        "account_id": "ACC-2001",
        "customer_id": "CUST-1002",
        "type": "checking",
        "status": "open",
        "available_balance": "890.40",
        "currency": "USD",
        "restriction": "documentation review",
    },
    "ACC-3001": {
        "account_id": "ACC-3001",
        "customer_id": "CUST-1003",
        "type": "checking",
        "status": "restricted",
        "available_balance": "22110.77",
        "currency": "USD",
        "restriction": "AML hold",
    },
    "ACC-4001": {
        "account_id": "ACC-4001",
        "customer_id": "CUST-1004",
        "type": "checking",
        "status": "pending",
        "available_balance": "3100.00",
        "currency": "USD",
        "restriction": "sanctions review",
    },
}

TRANSACTIONS = [
    {
        "transaction_id": "TX-10011",
        "account_id": "ACC-1001",
        "posted_on": "2026-10-02",
        "direction": "debit",
        "amount": "64.20",
        "type": "card",
        "merchant": "Northwind Market",
        "description": "Sample grocery purchase",
    },
    {
        "transaction_id": "TX-10012",
        "account_id": "ACC-1001",
        "posted_on": "2026-10-04",
        "direction": "credit",
        "amount": "2200.00",
        "type": "ach",
        "merchant": "Demo Payroll",
        "description": "Sample payroll credit",
    },
    {
        "transaction_id": "TX-10013",
        "account_id": "ACC-1001",
        "posted_on": "2026-10-09",
        "direction": "debit",
        "amount": "18.00",
        "type": "card",
        "merchant": "Harbor Coffee",
        "description": "Sample cafe purchase",
    },
    {
        "transaction_id": "TX-20011",
        "account_id": "ACC-2001",
        "posted_on": "2026-10-06",
        "direction": "debit",
        "amount": "42.10",
        "type": "card",
        "merchant": "Northwind Market",
        "description": "Sample grocery purchase",
    },
    {
        "transaction_id": "TX-30021",
        "account_id": "ACC-3001",
        "posted_on": "2026-09-12",
        "direction": "credit",
        "amount": "9800.00",
        "type": "cash",
        "merchant": "Branch cash",
        "description": "Sample cash deposit",
    },
    {
        "transaction_id": "TX-30022",
        "account_id": "ACC-3001",
        "posted_on": "2026-09-13",
        "direction": "credit",
        "amount": "12500.00",
        "type": "cash",
        "merchant": "Branch cash",
        "description": "Sample cash deposit at or above 10000 USD",
    },
    {
        "transaction_id": "TX-30023",
        "account_id": "ACC-3001",
        "posted_on": "2026-09-18",
        "direction": "debit",
        "amount": "400.00",
        "type": "card",
        "merchant": "Contoso Fuel",
        "description": "Sample fuel purchase",
    },
    {
        "transaction_id": "TX-40031",
        "account_id": "ACC-4001",
        "posted_on": "2026-10-01",
        "direction": "credit",
        "amount": "3100.00",
        "type": "wire",
        "merchant": "Example Incoming",
        "description": "Sample incoming wire while the account is pending review",
    },
]

POLICIES = [
    {
        "policy_id": "POL-KYC-001",
        "title": "Sample customer identification",
        "topics": ["kyc", "identity", "document", "documents", "onboarding", "government"],
        "excerpt": (
            "Sample policy. Collect a government id, a residential address, and a date of birth "
            "before opening an account. This assistant may only read the sample KYC status. "
            "It must not approve, waive, or complete onboarding."
        ),
    },
    {
        "policy_id": "POL-AML-001",
        "title": "Sample suspicious activity handling",
        "topics": ["aml", "flag", "flags", "structuring", "sar", "suspicious", "hold"],
        "excerpt": (
            "Sample policy. Open AML flags stay with the investigations queue. This assistant "
            "must not clear, disable, or override a flag, and must not tell a customer how to avoid a review."
        ),
    },
    {
        "policy_id": "POL-PAY-001",
        "title": "Sample payments and transfers",
        "topics": ["wire", "wires", "transfer", "transfers", "payment", "payments", "ach", "withdrawal"],
        "excerpt": (
            "Sample policy. The assistant is read-only. It must not submit, approve, or simulate a "
            "transfer, wire, ACH, card payment, or cash withdrawal. Direct the person to the bank's "
            "official payment channel."
        ),
    },
    {
        "policy_id": "POL-PII-001",
        "title": "Sample personal data handling",
        "topics": ["pii", "ssn", "privacy", "redact", "social", "email"],
        "excerpt": (
            "Sample policy. Social security numbers, full card numbers, dates of birth, and email "
            "addresses are masked in tool results. The assistant must not reveal or repeat a full "
            "SSN, card number, or date of birth."
        ),
    },
    {
        "policy_id": "POL-FEE-001",
        "title": "Sample fee schedule",
        "topics": ["fee", "fees", "schedule", "monthly", "tariff"],
        "excerpt": (
            "Sample fee schedule, not a real tariff. Monthly checking fee 12.00 USD. "
            "Outgoing wire fee 25.00 USD. Cash deposit fee 0.00 USD under this sample schedule."
        ),
    },
]

POLICY_TITLES = {row["policy_id"]: row["title"] for row in POLICIES}
MERCHANTS = sorted({row["merchant"] for row in TRANSACTIONS})


def sensitive_literals() -> list[str]:
    """Raw personal values that tool output must never contain."""
    values = []
    for customer in CUSTOMERS.values():
        values.extend([customer["ssn"], customer["email"], customer["phone"], customer["dob"], customer["card"]])
    return values
