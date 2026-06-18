import frappe
from frappe.model.document import Document


class BrainSettings(Document):
	def onload(self):
		provider = self.provider or ""
		if _is_local(provider):
			# Prevent Frappe from trying to decrypt a non-existent API key
			# when the form loads — set to None so Document.get_password() skips the decrypt path
			self.api_key = None

		# Expose context status for the form
		self.set_onload("context_file_exists", _context_file_exists())

	def validate(self):
		provider = self.provider or ""

		if not _is_local(provider):
			try:
				has_key = bool(self.get_password("api_key"))
			except Exception:
				has_key = False
			if not has_key:
				frappe.msgprint("API Key is required for cloud providers (Anthropic / OpenAI).", alert=True)

		if self.temperature is None:
			self.temperature = 0.1
		if not self.max_iterations:
			self.max_iterations = 10

	def after_save(self):
		# Auto-build context if it hasn't been built yet
		if _is_local(self.provider or "") and not _context_file_exists():
			frappe.enqueue(
				"brain.ai.context_builder.build_and_save",
				queue="short",
				enqueue_after_commit=True,
			)


def _is_local(provider: str) -> bool:
	return "Neurix" in provider or "Ollama" in provider


def _context_file_exists() -> bool:
	import os
	path = frappe.get_site_path("private", "files", "brain_context.json")
	return os.path.exists(path)
