import frappe


@frappe.whitelist(allow_guest=True)
def noop_empty_dict(**kwargs):
	return {}


@frappe.whitelist(allow_guest=True)
def noop_empty_list(**kwargs):
	return []


@frappe.whitelist(allow_guest=True)
def noop_false(**kwargs):
	return False
