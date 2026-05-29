import frappe
from frappe.model.document import Document
from frappe.utils import flt


class StyloLicenseRequest(Document):
	def before_save(self):
		self._recalculate_amount()
		if not self.consultant:
			self.consultant = frappe.session.user

	def _recalculate_amount(self):
		if not self.module_pack or not self.num_users or not self.duration_months:
			return
		pricing = frappe.db.get_value(
			"Stylo Module Pricing", self.module_pack, "price_per_user_per_month"
		)
		if pricing:
			self.monthly_rate = flt(pricing)
			self.total_amount = flt(pricing) * flt(self.num_users) * flt(self.duration_months)

	def on_submit(self):
		self.status = "Pending Payment"
		self._notify_admin()

	def _notify_admin(self):
		admin_email = frappe.db.get_single_value("System Settings", "email_footer_address") or "admin@styloworld.io"
		frappe.sendmail(
			recipients=[admin_email],
			subject=f"New License Request: {self.client_name} ({self.module_pack}, {self.num_users} users)",
			message=f"""
<p>A new license request has been submitted.</p>
<table>
<tr><td><b>Consultant:</b></td><td>{self.consultant}</td></tr>
<tr><td><b>Client:</b></td><td>{self.client_name}</td></tr>
<tr><td><b>Site:</b></td><td>{self.site or 'TBD'}</td></tr>
<tr><td><b>Pack:</b></td><td>{self.module_pack}</td></tr>
<tr><td><b>Modules:</b></td><td>{self.modules or ''}</td></tr>
<tr><td><b>Users:</b></td><td>{self.num_users}</td></tr>
<tr><td><b>Duration:</b></td><td>{self.duration_months} months</td></tr>
<tr><td><b>Total:</b></td><td>{self.total_amount:,.2f}</td></tr>
</table>
<p>Open Stylo Cloud to confirm payment and release the license.</p>
""",
			now=True,
		)
