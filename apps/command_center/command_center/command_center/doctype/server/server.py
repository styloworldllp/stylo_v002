import frappe
from frappe.model.document import Document


class Server(Document):
	def validate(self):
		if self.max_sites and self.max_sites < 1:
			frappe.throw("Max Sites must be at least 1")
