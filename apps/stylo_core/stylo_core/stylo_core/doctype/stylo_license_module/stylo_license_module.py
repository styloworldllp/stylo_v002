from frappe.model.document import Document

from stylo_core.license_map import MODULE_DISPLAY_NAMES


class StyloLicenseModule(Document):
	def validate(self):
		self.display_name = MODULE_DISPLAY_NAMES.get(self.module_key, self.module_key)
