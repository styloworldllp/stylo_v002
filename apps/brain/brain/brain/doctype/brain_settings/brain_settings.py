import frappe
from frappe.model.document import Document


class BrainSettings(Document):
	def validate(self):
		if self.provider and "Ollama" not in self.provider and not self.get_password("api_key"):
			frappe.msgprint("API Key is recommended for cloud providers.", alert=True)

		if self.temperature is None:
			self.temperature = 0.1
		if not self.max_iterations:
			self.max_iterations = 10
