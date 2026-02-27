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
