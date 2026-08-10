import frappe
from frappe.model.document import Document
from frappe.utils import add_days, today, date_diff


class StyloLicense(Document):
	def before_insert(self):
		if not self.grace_end_date and self.end_date:
			self.grace_end_date = add_days(self.end_date, 30)

	def get_status(self):
		"""Return current computed status. Demo and Terminated short-circuit the date-based
		logic entirely — a Demo license may have no meaningful end_date (unlimited access
		until manually converted to Active by a Command Center Super Admin/Admin)."""
		if self.status == "Demo":
			return "demo"
		if self.status == "Terminated":
			return "terminated"
		if self.status == "Suspended":
			return "suspended"
		if not self.end_date:
			return "active"
		today_str = today()
		if today_str <= self.end_date:
			return "active"
		if self.grace_end_date and today_str <= self.grace_end_date:
			return "grace_period"
		return "expired"

	def days_until_expiry(self):
		if not self.end_date:
			return None
		return date_diff(self.end_date, today())
