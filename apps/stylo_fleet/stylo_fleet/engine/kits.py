import frappe


def compute_kit_status(available_kits, minimum_operational_kits, refill_threshold):
	"""Per spec §7.4: threshold table for kit readiness."""
	if available_kits <= 0:
		return "No Kits"
	if available_kits < minimum_operational_kits:
		return "Insufficient"
	if available_kits <= refill_threshold:
		return "Refill Due"
	return "Ready"


def consume_kits(ambulance_doc, kits_consumed):
	"""Deduct kits_consumed from ambulance_doc.available_kits, in memory only.

	Caller is responsible for saving the document alongside any other field
	changes in the same transaction. Returns (balance_before, balance_after).
	"""
	kits_consumed = frappe.utils.cint(kits_consumed)
	if kits_consumed < 0:
		frappe.throw("Kits consumed cannot be negative.")

	balance_before = ambulance_doc.available_kits or 0
	if kits_consumed > balance_before:
		frappe.throw(
			f"Kits consumed ({kits_consumed}) cannot exceed the current balance ({balance_before})."
		)

	balance_after = balance_before - kits_consumed
	ambulance_doc.available_kits = balance_after
	ambulance_doc.kit_status = compute_kit_status(
		balance_after, ambulance_doc.minimum_operational_kits or 0, ambulance_doc.refill_threshold or 0
	)
	return balance_before, balance_after


def refill_kits(ambulance_doc, actual_loaded_quantity):
	"""Increase ambulance_doc.available_kits by actual_loaded_quantity, in memory only.

	Mirrors consume_kits: caller saves. Balance may not exceed kit_capacity.
	Returns (balance_before, balance_after).
	"""
	actual_loaded_quantity = frappe.utils.cint(actual_loaded_quantity)
	if actual_loaded_quantity < 0:
		frappe.throw("Loaded quantity cannot be negative.")

	balance_before = ambulance_doc.available_kits or 0
	balance_after = balance_before + actual_loaded_quantity
	if balance_after > (ambulance_doc.kit_capacity or 0):
		frappe.throw(
			f"Refill would exceed kit capacity ({ambulance_doc.kit_capacity}): "
			f"{balance_before} + {actual_loaded_quantity} = {balance_after}."
		)

	ambulance_doc.available_kits = balance_after
	ambulance_doc.kit_status = compute_kit_status(
		balance_after, ambulance_doc.minimum_operational_kits or 0, ambulance_doc.refill_threshold or 0
	)
	return balance_before, balance_after
