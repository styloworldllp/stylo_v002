import frappe


@frappe.whitelist()
def request_app(product_key: str, product_title: str, message: str = ""):
	"""Client requests installation of a Stylo module. Notifies Stylo team."""
	user = frappe.get_doc("User", frappe.session.user)
	site = frappe.local.site

	frappe.sendmail(
		recipients=["hello@stylo.io"],
		subject=f"App Request: {product_title} — {site}",
		message=f"""
<p>A client has requested installation of a Stylo module.</p>
<table style="border-collapse:collapse;width:100%">
<tr><td style="padding:6px 12px;font-weight:600;background:#f4f5f7">Site</td>
    <td style="padding:6px 12px">{site}</td></tr>
<tr><td style="padding:6px 12px;font-weight:600;background:#f4f5f7">Module</td>
    <td style="padding:6px 12px">{product_title}</td></tr>
<tr><td style="padding:6px 12px;font-weight:600;background:#f4f5f7">Requested by</td>
    <td style="padding:6px 12px">{user.full_name} &lt;{user.email}&gt;</td></tr>
<tr><td style="padding:6px 12px;font-weight:600;background:#f4f5f7">Message</td>
    <td style="padding:6px 12px">{message or "—"}</td></tr>
</table>
<p style="margin-top:16px">Please reach out within 24 hours to discuss implementation.</p>
""",
		now=True,
	)
	return {"success": True}
