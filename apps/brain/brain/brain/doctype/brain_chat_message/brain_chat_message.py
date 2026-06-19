import hashlib

import frappe
from frappe.model.document import Document


class BrainChatMessage(Document):
	def before_insert(self):
		if not self.timestamp:
			self.timestamp = frappe.utils.now_datetime()
		self._compute_hash()

	def _compute_hash(self):
		raw = f"{self.content or ''}{self.timestamp}{self.session}"
		self.content_hash = hashlib.sha256(raw.encode()).hexdigest()

	def on_trash(self):
		frappe.throw(
			"Brain Chat Messages cannot be deleted. This is required for 21 CFR Part 11 compliance."
		)
