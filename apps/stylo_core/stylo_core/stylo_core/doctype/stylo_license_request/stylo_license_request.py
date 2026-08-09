import frappe
from frappe.model.document import Document
from frappe.utils import flt
from stylo_core.license_map import MODULE_DISPLAY_NAMES


class StyloLicenseRequest(Document):
	def before_save(self):
		if not self.consultant:
			self.consultant = frappe.session.user
		self._fill_addon_display_names()
		self._recalculate_amount()

	def _fill_addon_display_names(self):
		for row in self.addon_modules or []:
			row.display_name = MODULE_DISPLAY_NAMES.get(row.module_key, row.module_key)

	def _recalculate_amount(self):
		if not self.base_module or not self.num_users or not self.duration_months:
			return

		# Base module price
		base_price = flt(frappe.db.get_value(
			"Stylo Module Pricing", {"module_key": self.base_module}, "price_per_user_per_month"
		) or 0)
		self.base_price_per_user = base_price

		# Add-on prices
		addon_total = 0
		for row in self.addon_modules or []:
			price = flt(frappe.db.get_value(
				"Stylo Module Pricing", {"module_key": row.module_key}, "price_per_user_per_month"
			) or 0)
			row.price_per_user = price
			addon_total += price

		total_per_user = base_price + addon_total
		self.total_amount = total_per_user * flt(self.num_users) * flt(self.duration_months)

	def get_all_module_keys(self) -> list[str]:
		"""Returns [base_module] + all addon module keys."""
		keys = [self.base_module] if self.base_module else []
		for row in self.addon_modules or []:
			if row.module_key and row.module_key not in keys:
				keys.append(row.module_key)
		return keys

	def on_submit(self):
		self.status = "Pending Payment"
		self._notify_admin()

	def _notify_admin(self):
		admin_email = frappe.db.get_single_value("System Settings", "email_footer_address") or "hello@stylo.io"
		modules = self.get_all_module_keys()
		module_names = [MODULE_DISPLAY_NAMES.get(k, k) for k in modules]

		frappe.sendmail(
			recipients=[admin_email],
			subject=f"New License Request: {self.client_name} — {', '.join(module_names)}",
			message=f"""
<p>A new license request has been submitted.</p>
<table>
<tr><td><b>Consultant:</b></td><td>{self.consultant}</td></tr>
<tr><td><b>Client:</b></td><td>{self.client_name}</td></tr>
<tr><td><b>Site:</b></td><td>{self.site or 'TBD'}</td></tr>
<tr><td><b>Base Module:</b></td><td>{MODULE_DISPLAY_NAMES.get(self.base_module, self.base_module)}</td></tr>
<tr><td><b>Add-ons:</b></td><td>{', '.join(MODULE_DISPLAY_NAMES.get(k, k) for k in modules[1:]) or '—'}</td></tr>
<tr><td><b>Users:</b></td><td>{self.num_users} (total — active + inactive)</td></tr>
<tr><td><b>Duration:</b></td><td>{self.duration_months} months</td></tr>
<tr><td><b>Total:</b></td><td>{self.total_amount:,.2f}</td></tr>
</table>
<p>Open Stylo Cloud to confirm payment and release the license.</p>
""",
			now=True,
		)
