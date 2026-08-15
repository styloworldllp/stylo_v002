import frappe


def get_context(context):
	frappe.only_for(["Fleet Paramedic", "Fleet Operations", "Fleet Admin", "System Manager"])
