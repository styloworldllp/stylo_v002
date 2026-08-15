import frappe

from stylo_fleet.engine.location import refresh_gps_status


def refresh_all_gps_status():
	"""Scheduled sweep: recompute gps_status for every active ambulance so a
	vehicle that stops reporting location gets flagged Stale/Offline even
	without any new shift/call/refill action happening. Per spec §11.
	"""
	for ambulance_id in frappe.get_all("Ambulance", filters={"active": 1}, pluck="name"):
		amb = frappe.get_doc("Ambulance", ambulance_id)
		previous_gps_status = amb.gps_status
		refresh_gps_status(amb)
		if amb.gps_status != previous_gps_status:
			amb.save(ignore_permissions=True)
	frappe.db.commit()
