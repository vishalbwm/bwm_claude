"""
Work Order overrides for BWM
Validates unreturned RM before allowing Close/Stop actions.
Provides one-click Return & Close functionality.

Logic:
- When user clicks Close or Stop on a Work Order
- Check if any required_items have excess = transferred - consumed - returned > 0
- If yes, block the action with a clear error message
- If no, proceed with the original ERPNext function
- User can call return_and_close to auto-return excess RM and close in one step
"""

import frappe
from frappe import _


def _get_excess_items(work_order_name):
    """
    Get list of excess RM items for a Work Order.
    Returns tuple of (wo_doc, excess_items_list).
    """
    wo = frappe.get_doc("Work Order", work_order_name)
    excess_items = []

    for item in wo.required_items:
        transferred = item.transferred_qty or 0
        consumed = item.consumed_qty or 0
        returned = item.returned_qty or 0
        excess = round(transferred - consumed - returned, 3)

        if excess > 0.01:
            excess_items.append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "excess_qty": excess,
                "stock_uom": item.stock_uom,
                "transferred": transferred,
                "consumed": consumed,
                "returned": returned,
                "source_warehouse": item.source_warehouse,
            })

    return wo, excess_items


def _validate_no_unreturned_rm(work_order_name, action_label):
    """
    Check if a Work Order has unreturned RM in WIP.
    Throws an error if excess RM exists, preventing Close/Stop.
    """
    wo, excess_items = _get_excess_items(work_order_name)

    if excess_items:
        items_html = "".join(
            "<li><b>{0}</b>: {1} {2} (Transferred: {3}, Consumed: {4}, Returned: {5})</li>".format(
                item["item_code"], item["excess_qty"], item["stock_uom"],
                item["transferred"], item["consumed"], item["returned"]
            )
            for item in excess_items
        )
        frappe.throw(
            _(
                "Cannot {0} Work Order <b>{1}</b> — there is unreturned RM in WIP warehouse.<br><br>"
                "<b>Excess Items:</b><ul>{2}</ul>"
                "Click <b>Return & Close</b> to auto-return excess RM and close in one step, "
                "or use <b>Return Components</b> to review quantities first."
            ).format(action_label, work_order_name, items_html),
            title=_("Unreturned RM in WIP"),
        )


@frappe.whitelist()
def close_work_order_with_rm_check(work_order, status):
    """
    Override for erpnext.manufacturing.doctype.work_order.work_order.close_work_order
    Validates no unreturned RM exists before allowing Close.
    """
    if status == "Closed":
        _validate_no_unreturned_rm(work_order, "Close")

    from erpnext.manufacturing.doctype.work_order.work_order import (
        close_work_order,
    )

    return close_work_order(work_order, status)


@frappe.whitelist()
def stop_unstop_with_rm_check(work_order, status):
    """
    Override for erpnext.manufacturing.doctype.work_order.work_order.stop_unstop
    Validates no unreturned RM exists before allowing Stop.
    """
    if status == "Stopped":
        _validate_no_unreturned_rm(work_order, "Stop")

    from erpnext.manufacturing.doctype.work_order.work_order import stop_unstop

    return stop_unstop(work_order, status)


@frappe.whitelist()
def return_and_close(work_order):
    """
    One-click: Return excess RM from WIP -> Submit -> Close WO.

    Creates a Stock Entry (Material Transfer for Manufacture, is_return=1)
    identical to ERPNext's native Return Components button,
    submits it, then closes the Work Order.
    """
    wo, excess_items = _get_excess_items(work_order)

    if not excess_items:
        # No excess - just close directly
        from erpnext.manufacturing.doctype.work_order.work_order import (
            close_work_order,
        )
        close_work_order(work_order, "Closed")
        return {"status": "closed", "message": "No excess RM. Work Order closed."}

    # Build the return Stock Entry (same as Return Components button)
    cost_center = wo.cost_center or ""

    # Fetch batch details from original Material Transfer entries for this WO
    # This gives us which batches were issued to WIP for each item, with original rates
    original_batches = frappe.db.sql("""
        SELECT sed.item_code, sed.batch_no, sed.s_warehouse,
               SUM(sed.qty) as issued_qty,
               SUM(sed.basic_amount) / NULLIF(SUM(sed.qty), 0) as original_rate
        FROM `tabStock Entry` se
        JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE se.work_order = %s
        AND se.purpose = 'Material Transfer for Manufacture'
        AND se.is_return = 0
        AND se.docstatus = 1
        AND sed.t_warehouse = %s
        GROUP BY sed.item_code, sed.batch_no, sed.s_warehouse
        ORDER BY sed.item_code, sed.batch_no
    """, (wo.name, wo.wip_warehouse), as_dict=True)

    # Also get already-returned quantities per item+batch to avoid double-returning
    already_returned = frappe.db.sql("""
        SELECT sed.item_code, sed.batch_no, SUM(sed.qty) as returned_qty
        FROM `tabStock Entry` se
        JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE se.work_order = %s
        AND se.purpose = 'Material Transfer for Manufacture'
        AND se.is_return = 1
        AND se.docstatus = 1
        AND sed.s_warehouse = %s
        GROUP BY sed.item_code, sed.batch_no
    """, (wo.name, wo.wip_warehouse), as_dict=True)

    # Build lookup: {(item_code, batch_no): returned_qty}
    returned_map = {}
    for r in already_returned:
        key = (r.item_code, r.batch_no or "")
        returned_map[key] = returned_map.get(key, 0) + (r.returned_qty or 0)

    # Build batch-wise return rows
    # For each excess item, split across batches proportionally
    batch_map = {}  # {item_code: [{batch_no, s_warehouse, available_qty}]}
    for ob in original_batches:
        ic = ob.item_code
        bn = ob.batch_no or ""
        issued = ob.issued_qty or 0
        already_ret = returned_map.get((ic, bn), 0)
        available = round(issued - already_ret, 3)
        if available > 0.01:
            if ic not in batch_map:
                batch_map[ic] = []
            batch_map[ic].append({
                "batch_no": ob.batch_no,
                "s_warehouse_orig": ob.s_warehouse,
                "available_qty": available,
                "original_rate": ob.original_rate or 0,
            })

    se = frappe.new_doc("Stock Entry")
    se.purpose = "Material Transfer for Manufacture"
    se.stock_entry_type = "Material Transfer for Manufacture"
    se.is_return = 1
    se.work_order = wo.name
    se.company = wo.company
    se.cost_center = cost_center
    se.from_warehouse = wo.wip_warehouse
    se.remarks = (
        "Auto Return & Close: Returning excess RM from WIP. "
        "WO " + str(wo.name) + ", Produced " + str(wo.produced_qty) + "/" + str(wo.qty) + "."
    )

    for item in excess_items:
        remaining = item["excess_qty"]
        batches = batch_map.get(item["item_code"], [])
        target_wh = item["source_warehouse"] or wo.source_warehouse

        if batches:
            # Add one row per batch, allocating excess across batches
            for b in batches:
                if remaining <= 0.01:
                    break
                return_qty = min(remaining, b["available_qty"])
                t_wh = b["s_warehouse_orig"] or target_wh
                row_data = {
                    "item_code": item["item_code"],
                    "item_name": item["item_name"],
                    "qty": round(return_qty, 3),
                    "uom": item["stock_uom"],
                    "stock_uom": item["stock_uom"],
                    "s_warehouse": wo.wip_warehouse,
                    "t_warehouse": t_wh,
                    "cost_center": cost_center,
                    "basic_rate": b["original_rate"],
                }
                if b["batch_no"]:
                    row_data["batch_no"] = b["batch_no"]
                se.append("items", row_data)
                remaining = round(remaining - return_qty, 3)
        else:
            # No batch info found — add without batch (non-batch items)
            if not target_wh:
                orig = frappe.db.sql("""
                    SELECT DISTINCT sed.s_warehouse
                    FROM `tabStock Entry` se
                    JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
                    WHERE se.work_order = %s
                    AND se.purpose = 'Material Transfer for Manufacture'
                    AND se.is_return = 0
                    AND se.docstatus = 1
                    AND sed.item_code = %s
                    AND sed.s_warehouse IS NOT NULL
                    AND sed.s_warehouse != %s
                    LIMIT 1
                """, (wo.name, item["item_code"], wo.wip_warehouse))
                if orig:
                    target_wh = orig[0][0]

            if not target_wh:
                frappe.throw(
                    _("Cannot determine source warehouse for {0}. "
                      "Please use Return Components manually.").format(item["item_code"])
                )

            se.append("items", {
                "item_code": item["item_code"],
                "item_name": item["item_name"],
                "qty": item["excess_qty"],
                "uom": item["stock_uom"],
                "stock_uom": item["stock_uom"],
                "s_warehouse": wo.wip_warehouse,
                "t_warehouse": target_wh,
                "cost_center": cost_center,
            })

    # Save and submit the return entry
    se.insert()
    se.submit()

    # Now close the Work Order
    from erpnext.manufacturing.doctype.work_order.work_order import (
        close_work_order,
    )
    close_work_order(work_order, "Closed")

    total_returned = sum(item["excess_qty"] for item in excess_items)
    return {
        "status": "returned_and_closed",
        "stock_entry": se.name,
        "total_returned_qty": total_returned,
        "items_count": len(excess_items),
        "message": (
            "Returned " + str(total_returned) + " Kgs via " + str(se.name)
            + " and closed WO " + str(wo.name) + "."
        ),
    }
