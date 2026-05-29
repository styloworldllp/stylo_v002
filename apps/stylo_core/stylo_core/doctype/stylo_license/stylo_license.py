import frappe
from frappe.model.document import Document
from frappe.utils import add_days, today, date_diff


class StyloLicense(Document):
	def before_insert(self):
		if not self.grace_end_date and self.end_date:
			self.grace_end_date = add_days(self.end_date, 30)

	def get_status(self):
		"""Return current computed status based on today's date."""
		today_str = today()
		if self.status == "Suspended":
			return "suspended"
		if today_str <= self.end_date:
			return "active"
		if today_str <= self.grace_end_date:
			return "grace_period"
		return "expired"

	def days_until_expiry(self):
		return date_diff(self.end_date, today())
