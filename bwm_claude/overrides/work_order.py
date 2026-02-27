"""
Work Order overrides for BWM
Validates unreturned RM before allowing Close/Stop actions.

Logic:
- When user clicks Close or Stop on a Work Order
- Check if any required_items have excess = transferred - consumed - returned > 0
- If yes, block the action with a clear error message
- If no, proceed with the original ERPNext function
"""

import frappe
from frappe import _


def _validate_no_unreturned_rm(work_order_name, action_label):
    """
    Check if a Work Order has unreturned RM in WIP.
    Throws an error if excess RM exists, preventing Close/Stop.

    Args:
        work_order_name: The Work Order name/ID
        action_label: "Close" or "Stop" for the error message
    """
    wo = frappe.get_doc("Work Order", work_order_name)

    excess_items = []
    for item in wo.required_items:
        transferred = item.transferred_qty or 0
        consumed = item.consumed_qty or 0
        returned = item.returned_qty or 0
        excess = round(transferred - consumed - returned, 3)

        if excess > 0.01:
            excess_items.append(
                f"<li><b>{item.item_code}</b>: {excess} {item.stock_uom} "
                f"(Transferred: {transferred}, Consumed: {consumed}, Returned: {returned})</li>"
            )

    if excess_items:
        items_html = "".join(excess_items)
        frappe.throw(
            _(
                "Cannot {0} Work Order <b>{1}</b> — there is unreturned RM in WIP warehouse.<br><br>"
                "<b>Excess Items:</b><ul>{2}</ul>"
                "<b>Action Required:</b> Click <b>Return Components</b> on the Work Order "
                "to return excess RM to the source warehouse, then try again."
            ).format(action_label, work_order_name, items_html),
            title=_("Unreturned RM in WIP"),
        )


@frappe.whitelist()
def close_work_order_with_rm_check(work_order, status):
    """
    Override for erpnext.manufacturing.doctype.work_order.work_order.close_work_order

    Validates no unreturned RM exists before allowing Close.
    If status is being set to "Closed", validates first.
    If re-opening (status != "Closed"), passes through directly.
    """
    if status == "Closed":
        _validate_no_unreturned_rm(work_order, "Close")

    # Call original ERPNext function
    from erpnext.manufacturing.doctype.work_order.work_order import (
        close_work_order,
    )

    return close_work_order(work_order, status)


@frappe.whitelist()
def stop_unstop_with_rm_check(work_order, status):
    """
    Override for erpnext.manufacturing.doctype.work_order.work_order.stop_unstop

    Validates no unreturned RM exists before allowing Stop.
    If status is being set to "Stopped", validates first.
    If re-starting (status != "Stopped"), passes through directly.
    """
    if status == "Stopped":
        _validate_no_unreturned_rm(work_order, "Stop")

    # Call original ERPNext function
    from erpnext.manufacturing.doctype.work_order.work_order import stop_unstop

    return stop_unstop(work_order, status)
