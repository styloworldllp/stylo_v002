import frappe
from stylo_fleet.api.shift import start_shift
from stylo_fleet.api.call import attend_call, complete_call
from stylo_fleet.api.issue import report_issue


def _as(user, fn, *args, **kwargs):
	frappe.set_user(user)
	try:
		return fn(*args, **kwargs)
	finally:
		frappe.set_user("Administrator")


def run():
	# AMB-001 / Ravi Kumar: normal shift, light call, stays healthy and Available.
	if not frappe.db.get_value("Ambulance", "AMB-001", "current_shift"):
		_as("ravi.kumar@nhs.stylo.io", start_shift, ambulance="AMB-001", paramedic="Ravi Kumar",
			latitude=12.9716, longitude=77.5946, start_check_result="Brakes, tyres, lights all OK")
		_as("ravi.kumar@nhs.stylo.io", attend_call, ambulance="AMB-001", latitude=12.9750, longitude=77.6000)
		_as("ravi.kumar@nhs.stylo.io", complete_call, ambulance="AMB-001", kits_consumed=2,
			ambulance_clean=1, mechanical_issue=0, remarks="Routine transport, no complications",
			latitude=12.9750, longitude=77.6000)
		print("AMB-001 / Ravi Kumar: shift open, call completed, expect Available/Ready")

	# AMB-002 / Anjali Sharma: heavier call, kits drop to the refill-due band ->
	# auto-triggers a Pending Ambulance Refill for the station to confirm.
	if not frappe.db.get_value("Ambulance", "AMB-002", "current_shift"):
		_as("anjali.sharma@nhs.stylo.io", start_shift, ambulance="AMB-002", paramedic="Anjali Sharma",
			latitude=12.9800, longitude=77.5900, start_check_result="All checks passed")
		_as("anjali.sharma@nhs.stylo.io", attend_call, ambulance="AMB-002", latitude=12.9850, longitude=77.5950)
		_as("anjali.sharma@nhs.stylo.io", complete_call, ambulance="AMB-002", kits_consumed=8,
			ambulance_clean=1, mechanical_issue=0, remarks="Multi-casualty call, heavy kit usage",
			latitude=12.9850, longitude=77.5950)
		print("AMB-002 / Anjali Sharma: shift open, call completed, expect Refill Due + Pending Ambulance Refill")

	# AMB-003 / Suresh Nair: reports a mechanical issue mid-shift (not tied to a call) ->
	# blocks availability, leaves an Open Ambulance Issue for Station/Operations to resolve.
	if not frappe.db.get_value("Ambulance", "AMB-003", "current_shift"):
		_as("suresh.nair@nhs.stylo.io", start_shift, ambulance="AMB-003", paramedic="Suresh Nair",
			latitude=13.0100, longitude=77.6300, start_check_result="All checks passed")
		_as("suresh.nair@nhs.stylo.io", report_issue, ambulance="AMB-003", issue_type="Mechanical",
			severity="Attention Required", description="Brake pads worn, needs inspection before next call",
			latitude=13.0120, longitude=77.6320)
		print("AMB-003 / Suresh Nair: shift open, mechanical issue reported, expect Unavailable/Maintenance Required")

	frappe.db.commit()

	# ---- verification / summary ----
	from stylo_fleet.api.dashboard import get_control_centre_summary, get_refill_queue
	frappe.set_user("karthik.ops@nhs.stylo.io")
	summary = get_control_centre_summary()
	refill_queue = get_refill_queue()
	frappe.set_user("Administrator")

	print("\n--- Control Centre Summary ---")
	for k, v in summary["summary"].items():
		print(f"  {k}: {v}")
	print("\n--- Fleet ---")
	for row in summary["fleet"]:
		print(f"  {row['ambulance_id']}: {row['operational_status']} | availability={row['availability_status']} "
			  f"({row['availability_reason']}) | kits {row['available_kits']}/{row['kit_capacity']} "
			  f"({row['kit_status']}) | clean={row['cleanliness_status']} | mech={row['mechanical_status']}")
	print("\n--- Pending Refills ---")
	for row in refill_queue["pending"]:
		print(f"  {row['name']}: {row['ambulance']} needs {row['expected_load_quantity']} "
			  f"(balance {row['balance_before_refill']})")

	print("\nDEMO DATA + WORKFLOW EXERCISE DONE")
