import frappe
from frappe.model.document import Document
from frappe.utils import date_diff, flt, today
from stylo_core.license_map import MODULE_DISPLAY_NAMES


class StyloLicenseAddonRequest(Document):
	def before_save(self):
		if not self.consultant:
			self.consultant = frappe.session.user
		self._auto_fill_from_license()
		self._recalculate_amount()

	def _auto_fill_from_license(self):
		if not self.license:
			return
		lic = frappe.get_doc("Stylo License", self.license)
		self.site = lic.site or ""
		self.client_name = lic.client_name or ""

	def _recalculate_amount(self):
		if not self.module_to_add or not self.license:
			return

		price = flt(frappe.db.get_value(
			"Stylo Module Pricing", {"module_key": self.module_to_add}, "price_per_user_per_month"
		) or 0)
		self.price_per_user = price

		if price and self.license:
			lic = frappe.get_doc("Stylo License", self.license)
			users = int(lic.user_limit or 0) + int(self.user_count_change or 0)
			# Remaining months on the license
			remaining = max(1, date_diff(lic.end_date, today()) // 30)
			self.total_addon_amount = price * users * remaining

	def on_submit(self):
		self.status = "Pending Payment"
		self._notify_admin()

	def _notify_admin(self):
		admin_email = (
			frappe.db.get_single_value("System Settings", "email_footer_address")
			or "hello@stylo.io"
		)
		module_name = MODULE_DISPLAY_NAMES.get(self.module_to_add, self.module_to_add)
		frappe.sendmail(
			recipients=[admin_email],
			subject=f"Module Addon Request: Add {module_name} to {self.site}",
			message=f"""
<p>A module add-on request has been submitted for an existing client site.</p>
<table>
<tr><td><b>Site:</b></td><td>{self.site}</td></tr>
<tr><td><b>Client:</b></td><td>{self.client_name}</td></tr>
<tr><td><b>Module to Add:</b></td><td>{module_name}</td></tr>
<tr><td><b>Additional Users:</b></td><td>{self.user_count_change or 0}</td></tr>
<tr><td><b>Total Amount:</b></td><td>{self.total_addon_amount:,.2f}</td></tr>
</table>
<p>Open Stylo Cloud to confirm payment and apply the addon.</p>
""",
			now=True,
		)
