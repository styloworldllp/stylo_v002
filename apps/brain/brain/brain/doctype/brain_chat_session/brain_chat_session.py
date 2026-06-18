import frappe
from frappe.model.document import Document


class BrainChatSession(Document):
	def before_insert(self):
		if not self.started_at:
			self.started_at = frappe.utils.now_datetime()
		self.last_active = self.started_at
		if not self.site_name:
			self.site_name = frappe.local.site

	def after_insert(self):
		pass

	# Sessions are never deleted — only Closed or Expired
	def on_trash(self):
		frappe.throw("Brain Chat Sessions cannot be deleted. This is required for 21 CFR Part 11 compliance.")
