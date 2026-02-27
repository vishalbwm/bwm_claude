// BWM Claude: Add "Return & Close" button to Work Order
frappe.ui.form.on("Work Order", {
    refresh: function (frm) {
        // Show "Return & Close" button on submitted WOs that are not yet Closed/Cancelled
        if (
            frm.doc.docstatus === 1 &&
            frm.doc.status !== "Closed" &&
            frm.doc.status !== "Cancelled"
        ) {
            // Check if there's excess RM
            var has_excess = false;
            (frm.doc.required_items || []).forEach(function (item) {
                var excess =
                    (item.transferred_qty || 0) -
                    (item.consumed_qty || 0) -
                    (item.returned_qty || 0);
                if (excess > 0.01) {
                    has_excess = true;
                }
            });

            if (has_excess) {
                frm.add_custom_button(
                    __("Return & Close"),
                    function () {
                        // Build summary of what will be returned
                        var summary_rows = [];
                        (frm.doc.required_items || []).forEach(function (item) {
                            var excess =
                                (item.transferred_qty || 0) -
                                (item.consumed_qty || 0) -
                                (item.returned_qty || 0);
                            if (excess > 0.01) {
                                summary_rows.push(
                                    "<tr><td>" +
                                        item.item_code +
                                        "</td><td>" +
                                        excess.toFixed(3) +
                                        " " +
                                        (item.stock_uom || "Kgs") +
                                        "</td></tr>"
                                );
                            }
                        });

                        var summary_html =
                            "<p>The following excess RM will be returned from WIP to source warehouse and the Work Order will be closed:</p>" +
                            '<table class="table table-bordered table-condensed">' +
                            "<thead><tr><th>Item</th><th>Return Qty</th></tr></thead>" +
                            "<tbody>" +
                            summary_rows.join("") +
                            "</tbody></table>" +
                            "<p><b>This will create and submit a Return Components entry automatically.</b></p>";

                        frappe.confirm(
                            summary_html,
                            function () {
                                frappe.call({
                                    method: "bwm_claude.overrides.work_order.return_and_close",
                                    args: {
                                        work_order: frm.doc.name,
                                    },
                                    freeze: true,
                                    freeze_message: __(
                                        "Returning excess RM and closing Work Order..."
                                    ),
                                    callback: function (r) {
                                        if (r.message) {
                                            var result = r.message;
                                            if (result.status === "returned_and_closed") {
                                                frappe.show_alert(
                                                    {
                                                        message: __(
                                                            "Returned {0} Kgs via {1}. Work Order closed.",
                                                            [
                                                                result.total_returned_qty,
                                                                '<a href="/app/stock-entry/' +
                                                                    result.stock_entry +
                                                                    '">' +
                                                                    result.stock_entry +
                                                                    "</a>",
                                                            ]
                                                        ),
                                                        indicator: "green",
                                                    },
                                                    10
                                                );
                                            } else if (result.status === "closed") {
                                                frappe.show_alert(
                                                    {
                                                        message: __(result.message),
                                                        indicator: "green",
                                                    },
                                                    5
                                                );
                                            }
                                            frm.reload_doc();
                                        }
                                    },
                                });
                            }
                        );
                    },
                    __("Manufacturing")
                );
            }
        }
    },
});
