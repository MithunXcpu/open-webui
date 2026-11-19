"""
title: Financial Services Workbench
author: financial-services-workbench
version: 0.1.0
description: Sample account, transaction, KYC/AML, and policy tools. Read-only demo data.
"""


class Tools:
    def account_lookup(self, account_id: str = "", customer_id: str = "") -> str:
        """
        Look up a sample bank account. Read-only demo ledger.
        :param account_id: Sample account id such as ACC-1001.
        :param customer_id: Sample customer id such as CUST-1001.
        """
        return _call("account_lookup", account_id=account_id, customer_id=customer_id)

    def transaction_search(
        self,
        account_id: str = "",
        merchant: str = "",
        txn_type: str = "",
        min_amount: str = "",
        max_amount: str = "",
        posted_on_or_after: str = "",
        query: str = "",
    ) -> str:
        """
        Search sample transactions. Does not post or transfer funds.
        :param account_id: Sample account id such as ACC-1001.
        :param merchant: Merchant name fragment, such as Northwind Market.
        :param txn_type: card, cash, ach, or wire.
        :param min_amount: Inclusive minimum amount as a decimal string.
        :param max_amount: Inclusive maximum amount as a decimal string.
        :param posted_on_or_after: Date YYYY-MM-DD.
        :param query: Extra text matched against the sample description.
        """
        return _call(
            "transaction_search",
            account_id=account_id,
            merchant=merchant,
            txn_type=txn_type,
            min_amount=min_amount,
            max_amount=max_amount,
            posted_on_or_after=posted_on_or_after,
            query=query,
        )

    def kyc_aml_check(self, customer_id: str = "", account_id: str = "") -> str:
        """
        Read a sample KYC status and AML flags. Cannot clear a flag.
        :param customer_id: Sample customer id such as CUST-1003.
        :param account_id: Sample account id such as ACC-3001.
        """
        return _call("kyc_aml_check", customer_id=customer_id, account_id=account_id)

    def policy_lookup(self, query: str = "") -> str:
        """
        Quote a sample policy excerpt. Not legal or compliance advice.
        :param query: Question about KYC, AML, payments, privacy, or fees.
        """
        return _call("policy_lookup", query=query)


def _call(name: str, **kwargs) -> str:
    try:
        from fsw.tools import dispatch
    except Exception as exc:
        return (
            "Financial Services Workbench is not importable "
            f"({exc}). Run Open WebUI from this fork so the package is on the path."
        )
    return dispatch(name, kwargs, as_json=True)
