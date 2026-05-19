import frappe
from frappe.model.document import Document


class BrainSettings(Document):
	def validate(self):
		try:
			has_key = bool(self.get_password("api_key"))
		except Exception:
			has_key = False
		if self.provider and "Ollama" not in self.provider and not has_key:
			frappe.msgprint("API Key is recommended for cloud providers.", alert=True)

		if self.temperature is None:
			self.temperature = 0.1
		if not self.max_iterations:
			self.max_iterations = 10
