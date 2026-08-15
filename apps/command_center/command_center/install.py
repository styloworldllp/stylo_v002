"""
after_install hook — adds a `site` custom field to HD Ticket so support tickets can be tied
to a specific client site. Uses Frappe's standard Custom Field mechanism rather than editing
apps/helpdesk/helpdesk/helpdesk/doctype/hd_ticket/hd_ticket.json directly, since Helpdesk is a
third-party/vendored app and a direct edit would be clobbered by the next `bench update`.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


def after_install():
	if not frappe.db.exists("DocType", "HD Ticket"):
		# Helpdesk isn't installed on this site — nothing to attach to.
		return

	create_custom_field(
		"HD Ticket",
		{
			"fieldname": "site",
			"label": "Site",
			"fieldtype": "Link",
			"options": "Site",
			"insert_after": "agent_group",
			"in_standard_filter": 1,
		},
	)
