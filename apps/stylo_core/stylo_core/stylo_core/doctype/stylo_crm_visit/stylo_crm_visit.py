import frappe
from frappe.model.document import Document


class StyloCRMVisit(Document):
	def before_insert(self):
		if not self.visited_by:
			self.visited_by = frappe.session.user
		if not self.visit_time:
			self.visit_time = frappe.utils.now()


@frappe.whitelist()
def log_visit(
	note: str,
	lead: str | None = None,
	deal: str | None = None,
	latitude: float | None = None,
	longitude: float | None = None,
):
	"""Called by the mobile app's field-visit check-in. Requires at least a note — the
	geo-location is best-effort (the app sends None if the user denied location permission
	or GPS wasn't available yet, rather than blocking the visit log on it)."""
	if not note or not note.strip():
		frappe.throw("Visit note is required")
	if not lead and not deal:
		frappe.throw("A visit must be linked to a Lead or a Deal")

	doc = frappe.get_doc(
		{
			"doctype": "Stylo CRM Visit",
			"lead": lead,
			"deal": deal,
			"note": note.strip(),
			"latitude": latitude,
			"longitude": longitude,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.as_dict()


@frappe.whitelist()
def get_visits(lead: str | None = None, deal: str | None = None, limit: int = 50):
	filters = {}
	if lead:
		filters["lead"] = lead
	if deal:
		filters["deal"] = deal
	return frappe.get_all(
		"Stylo CRM Visit",
		filters=filters,
		fields=["name", "lead", "deal", "visited_by", "visit_time", "latitude", "longitude", "note", "creation"],
		order_by="visit_time desc",
		limit_page_length=limit,
	)
