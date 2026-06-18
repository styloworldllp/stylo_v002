import frappe
from frappe.model.document import Document


class BrainAuditLog(Document):
	def on_trash(self):
		frappe.throw(
			"Brain Audit Logs are immutable and cannot be deleted. Required for 21 CFR Part 11 compliance."
		)

	def on_update(self):
		# Prevent modification of committed audit records
		frappe.throw(
			"Brain Audit Logs cannot be modified after creation. Required for 21 CFR Part 11 compliance."
		)
