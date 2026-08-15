import frappe


@frappe.whitelist()
def get_tickets_by_site(site: str | None = None):
	if not frappe.db.exists("DocType", "HD Ticket"):
		return []

	filters = {}
	if site:
		filters["site"] = site

	# Called as the logged-in user (not ignore_permissions) so Support Staff only see
	# what Helpdesk's own role/permission model already permits them to see — this is a
	# read-only rollup, not a parallel permission system.
	return frappe.get_list(
		"HD Ticket",
		filters=filters,
		fields=["name", "subject", "status", "priority", "site", "customer", "modified"],
		order_by="modified desc",
		limit_page_length=100,
	)
