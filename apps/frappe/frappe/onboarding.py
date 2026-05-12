import frappe


@frappe.whitelist()
def get_onboarding_status():
	return {}


@frappe.whitelist()
def update_user_onboarding_status(steps=None, appName=None):
	return {}
