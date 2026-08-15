BLOCKING_MECHANICAL_STATUSES = {"Maintenance Required", "Breakdown"}


def recompute_availability(ambulance_doc):
	"""Recompute availability_status/availability_reason from ambulance readiness
	conditions: active flag, assigned driver, kits, cleanliness, mechanical fitness.

	Deliberately does NOT consider operational_status — that is a separate workflow
	state set explicitly by whichever action causes the transition (Start/End Shift,
	Attend/Complete Call). Callers combine this readiness result with their own
	operational_status decision (e.g. On Call always blocks regardless of readiness).
	Does not save the document; caller persists alongside other changes.
	"""
	if not ambulance_doc.active:
		ambulance_doc.availability_status = "Unavailable"
		ambulance_doc.availability_reason = "Ambulance Inactive"
		return

	if not ambulance_doc.current_paramedic:
		ambulance_doc.availability_status = "Unavailable"
		ambulance_doc.availability_reason = "No Active Driver"
		return

	if (ambulance_doc.available_kits or 0) < (ambulance_doc.minimum_operational_kits or 0):
		ambulance_doc.availability_status = "Unavailable"
		ambulance_doc.availability_reason = "Insufficient Kits"
		return

	if ambulance_doc.cleanliness_status != "Clean":
		ambulance_doc.availability_status = "Unavailable"
		ambulance_doc.availability_reason = "Cleaning Required"
		return

	if ambulance_doc.mechanical_status in BLOCKING_MECHANICAL_STATUSES:
		ambulance_doc.availability_status = "Unavailable"
		ambulance_doc.availability_reason = "Mechanical Issue"
		return

	if ambulance_doc.kit_status == "Refill Due":
		ambulance_doc.availability_status = "Warning"
		ambulance_doc.availability_reason = "Refill Due"
		return

	ambulance_doc.availability_status = "Available"
	ambulance_doc.availability_reason = ""
