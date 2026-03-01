"""
BWM Interunit Transfer - GL Override Logic (v4)
================================================
Overrides income_account on Sales Invoice items and expense_account on
Delivery Note items when the customer is a BWM internal entity.

Design:  SI (income 31101 → 14120)  +  DN (expense 41103 → 14120)
Account: 14120 - Branch Stock Transfer - BWM  (Liability > Division/Branch)
Flag:    Customer.custom_is_bwm_internal_entity = 1

Hooks (in hooks.py):
    Sales Invoice  → before_submit → si_before_submit
    Delivery Note  → before_submit → dn_before_submit
"""

import frappe

# ---------------------------------------------------------------------------
# Constants — account numbers (not full names, resolved per company)
# ---------------------------------------------------------------------------
INTERUNIT_ACCOUNT_NUMBER = "14120"
SALES_ACCOUNT_NUMBER = "31101"
COGS_ACCOUNT_NUMBER = "41103"


def _get_account_by_number(account_number, company):
    """Resolve an account name from its number for a given company."""
    return frappe.db.get_value(
        "Account",
        {"account_number": account_number, "company": company},
        "name",
    )


def _get_interunit_account(company):
    """Get the interunit account (14120) for the company. Throw if missing."""
    account = _get_account_by_number(INTERUNIT_ACCOUNT_NUMBER, company)
    if not account:
        frappe.throw(
            f"Interunit account {INTERUNIT_ACCOUNT_NUMBER} not found for "
            f"company {company}. Please create '14120 - Branch Stock Transfer' "
            f"under Division/Branch."
        )
    return account


def _is_bwm_internal_customer(customer):
    """Check if the customer is flagged as a BWM internal entity."""
    if not customer:
        return False
    return (
        frappe.db.get_value(
            "Customer", customer, "custom_is_bwm_internal_entity"
        )
        == 1
    )


# ---------------------------------------------------------------------------
# Sales Invoice: before_submit
# ---------------------------------------------------------------------------
def si_before_submit(doc, method=None):
    """
    If customer is BWM internal:
    1. Store each item's original income_account
    2. Override income_account → 14120 (Interunit)
    3. Set custom_is_branch_transfer = 1
    4. Validate no item still has 31101 (Sales)
    """
    if not _is_bwm_internal_customer(doc.customer):
        return

    interunit_account = _get_interunit_account(doc.company)

    for item in doc.items:
        # Store original
        item.custom_original_income_account = item.income_account or ""
        # Override
        item.income_account = interunit_account

    doc.custom_is_branch_transfer = 1

    # --- Safety validation ---
    sales_account = _get_account_by_number(SALES_ACCOUNT_NUMBER, doc.company)
    if sales_account:
        for item in doc.items:
            if item.income_account == sales_account:
                frappe.throw(
                    f"Row {item.idx}: Income account is still {sales_account} "
                    f"on Branch Transfer SI. Override failed. Contact IT."
                )

    frappe.msgprint(
        f"Branch Transfer: Income account → {interunit_account} "
        f"for {len(doc.items)} item(s).",
        indicator="blue",
        alert=True,
    )


# ---------------------------------------------------------------------------
# Delivery Note: before_submit
# ---------------------------------------------------------------------------
def dn_before_submit(doc, method=None):
    """
    If customer is BWM internal:
    1. Store each item's original expense_account
    2. Override expense_account → 14120 (Interunit)
    3. Set custom_is_branch_transfer = 1
    4. Validate no item still has 41103 (COGS)
    """
    if not _is_bwm_internal_customer(doc.customer):
        return

    interunit_account = _get_interunit_account(doc.company)

    for item in doc.items:
        # Store original
        item.custom_original_expense_account = item.expense_account or ""
        # Override
        item.expense_account = interunit_account

    doc.custom_is_branch_transfer = 1

    # --- Safety validation ---
    cogs_account = _get_account_by_number(COGS_ACCOUNT_NUMBER, doc.company)
    if cogs_account:
        for item in doc.items:
            if item.expense_account == cogs_account:
                frappe.throw(
                    f"Row {item.idx}: Expense account is still {cogs_account} "
                    f"on Branch Transfer DN. Override failed. Contact IT."
                )

    frappe.msgprint(
        f"Branch Transfer: Expense account → {interunit_account} "
        f"for {len(doc.items)} item(s).",
        indicator="blue",
        alert=True,
    )
