import frappe


def get_context(context):
	frappe.only_for(["Fleet Station", "Fleet Operations", "Fleet Admin", "System Manager"])
