app_name = "bwm_claude"
app_title = "BWM Claude"
app_publisher = "Banaraswala Wire Mesh P Limited"
app_description = "Custom overrides and automation for BWM"
app_email = "vishal@banaraswala.com"
app_license = "MIT"
required_apps = ["frappe", "erpnext"]

# --------------------------------------------------------------------------
# Override whitelisted methods
# --------------------------------------------------------------------------
# Intercept WO Close and Stop to validate unreturned RM in WIP
override_whitelisted_methods = {
    "erpnext.manufacturing.doctype.work_order.work_order.close_work_order": "bwm_claude.overrides.work_order.close_work_order_with_rm_check",
    "erpnext.manufacturing.doctype.work_order.work_order.stop_unstop": "bwm_claude.overrides.work_order.stop_unstop_with_rm_check",
}

# --------------------------------------------------------------------------
# Doc Events — Interunit Transfer GL Override (v4)
# --------------------------------------------------------------------------
# On submit: override income_account (SI) and expense_account (DN)
# from Sales/COGS to 14120 - Branch Stock Transfer
# when customer has custom_is_bwm_internal_entity = 1
doc_events = {
    "Sales Invoice": {
        "before_submit": "bwm_claude.interunit_transfer.si_before_submit",
    },
    "Delivery Note": {
        "before_submit": "bwm_claude.interunit_transfer.dn_before_submit",
    },
}

# --------------------------------------------------------------------------
# Fixtures — export custom fields with the app
# --------------------------------------------------------------------------
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                [
                    "Customer-custom_is_bwm_internal_entity",
                    "Sales Invoice-custom_is_branch_transfer",
                    "Sales Invoice Item-custom_original_income_account",
                    "Delivery Note-custom_is_branch_transfer",
                    "Delivery Note Item-custom_original_expense_account",
                ],
            ]
        ],
    },
]
