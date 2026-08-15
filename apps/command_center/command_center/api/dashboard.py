from collections import Counter

import frappe

from command_center.api.server import get_candidates


@frappe.whitelist()
def get_summary():
	# frappe.get_all() rejects raw SQL function strings in `fields` (e.g. "count(name)")
	# in this Frappe version — tally in Python instead of using SQL GROUP BY/COUNT.
	statuses = frappe.get_all("Site", fields=["status"], pluck="status")
	site_by_status = dict(Counter(statuses))

	pending_requests = frappe.db.count("Site Request", {"status": "Pending Approval"})
	recent_failed_deploys = frappe.get_all(
		"Deploy Log",
		filters={"success": 0},
		fields=["name", "site_request", "site", "step", "timestamp"],
		order_by="timestamp desc",
		limit_page_length=10,
	)

	candidates = get_candidates(exclude_full=False) if "Command Center Super Admin" in frappe.get_roles() else []
	fleet_avg = {"cpu": 0, "ram": 0, "disk": 0}
	fresh = [c for c in candidates if not c["stale"]]
	if fresh:
		servers = frappe.get_all(
			"Server",
			filters={"name": ["in", [c["server"] for c in fresh]]},
			fields=["last_cpu_percent", "last_ram_percent", "last_disk_percent"],
		)
		n = len(servers) or 1
		fleet_avg = {
			"cpu": round(sum(s.last_cpu_percent or 0 for s in servers) / n, 1),
			"ram": round(sum(s.last_ram_percent or 0 for s in servers) / n, 1),
			"disk": round(sum(s.last_disk_percent or 0 for s in servers) / n, 1),
		}

	return {
		"site_by_status": site_by_status,
		"pending_requests": pending_requests,
		"recent_failed_deploys": recent_failed_deploys,
		"fleet_avg": fleet_avg,
		"server_count": len(candidates),
	}
