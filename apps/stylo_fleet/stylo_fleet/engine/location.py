import frappe
from frappe.utils import now_datetime, time_diff_in_seconds


def update_location(ambulance_doc, latitude=None, longitude=None):
	"""Update an ambulance's last-known location, in memory only — caller saves.

	No-op if no coordinates were provided: not every action captures location
	(e.g. device GPS permission denied, spec §21 edge case) — in that case
	refresh_gps_status() below is what flags the ambulance as stale/offline
	rather than this silently writing bad data.
	"""
	if latitude is None or longitude is None:
		return
	ambulance_doc.latitude = latitude
	ambulance_doc.longitude = longitude
	ambulance_doc.last_location_at = now_datetime()
	ambulance_doc.gps_status = "Online"


def refresh_gps_status(ambulance_doc):
	"""Recompute gps_status (Online/Stale/Offline) from last_location_at against
	the configured staleness window (Ambulance Settings.location_stale_after_minutes).
	Does not save; caller persists.
	"""
	if not ambulance_doc.last_location_at:
		ambulance_doc.gps_status = "Offline"
		return

	stale_after_minutes = (
		frappe.db.get_single_value("Ambulance Settings", "location_stale_after_minutes") or 15
	)
	age_seconds = time_diff_in_seconds(now_datetime(), ambulance_doc.last_location_at)
	ambulance_doc.gps_status = "Stale" if age_seconds > stale_after_minutes * 60 else "Online"
