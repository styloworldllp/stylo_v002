import frappe
from frappe.model.document import Document


class ServerMetric(Document):
	def after_insert(self):
		# Denormalized cache on Server for O(1) reads during server selection (§3),
		# avoiding a fresh "latest metric" query on every Site Request approval.
		frappe.db.set_value(
			"Server",
			self.server,
			{
				"last_cpu_percent": self.cpu_percent,
				"last_ram_percent": self.ram_percent,
				"last_disk_percent": self.disk_percent,
				"last_metric_at": self.timestamp,
				"last_seen": self.timestamp,
			},
			update_modified=False,
		)
