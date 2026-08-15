import frappe
from frappe.model.document import Document


class Site(Document):
	def before_insert(self):
		if not self.created_by_user:
			self.created_by_user = frappe.session.user
