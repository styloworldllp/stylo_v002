"""
Server selection algorithm (plan §3). Picks the best Active server for a new Site Request
based on live CPU/RAM/disk load (cached on Server by Server Metric's after_insert hook) plus
capacity headroom, with a configurable weighting and a manual-override escape hatch.
"""

import frappe
from frappe.utils import now_datetime, time_diff_in_seconds

SUPER_ADMIN_ROLE = "Command Center Super Admin"


class NoEligibleServerError(frappe.ValidationError):
	pass


def _get_settings():
	return frappe.get_cached_doc("Command Center Settings")


def _is_stale(last_metric_at, staleness_minutes):
	if not last_metric_at:
		return True
	return time_diff_in_seconds(now_datetime(), last_metric_at) > staleness_minutes * 60


def score_server(server_doc, settings) -> float:
	"""Lower is better."""
	site_count = frappe.db.count("Site", {"server": server_doc.name, "status": ["!=", "Failed"]})
	capacity_pct = (site_count / server_doc.max_sites * 100) if server_doc.max_sites else 100
	return (
		(settings.w_cpu or 0) * (server_doc.last_cpu_percent or 0)
		+ (settings.w_ram or 0) * (server_doc.last_ram_percent or 0)
		+ (settings.w_disk or 0) * (server_doc.last_disk_percent or 0)
		+ (settings.w_capacity or 0) * capacity_pct
	)


def get_candidates(exclude_full: bool = True) -> list[dict]:
	"""Every Active server with its eligibility, score, and staleness — used both by the
	real selection algorithm and by the frontend preview so both always agree."""
	settings = _get_settings()
	staleness_minutes = settings.metric_staleness_minutes or 15

	servers = frappe.get_all(
		"Server",
		filters={"status": "Active"},
		fields=[
			"name",
			"label",
			"max_sites",
			"last_cpu_percent",
			"last_ram_percent",
			"last_disk_percent",
			"last_metric_at",
		],
	)

	candidates = []
	for s in servers:
		server_doc = frappe._dict(s)
		site_count = frappe.db.count("Site", {"server": s.name, "status": ["!=", "Failed"]})
		stale = _is_stale(s.last_metric_at, staleness_minutes)
		full = bool(s.max_sites) and site_count >= s.max_sites
		eligible = not stale and not (full and exclude_full)

		candidates.append(
			{
				"server": s.name,
				"label": s.label,
				"score": score_server(server_doc, settings) if not stale else None,
				"site_count": site_count,
				"max_sites": s.max_sites,
				"stale": stale,
				"full": full,
				"eligible": eligible,
			}
		)

	candidates.sort(key=lambda c: (c["score"] is None, c["score"] if c["score"] is not None else 0))
	return candidates


def select_best_server(exclude_full: bool = True) -> str:
	candidates = get_candidates(exclude_full=exclude_full)
	eligible = [c for c in candidates if c["eligible"]]
	if not eligible:
		frappe.throw(
			"No healthy server with capacity is available for auto-selection — choose a server manually.",
			NoEligibleServerError,
		)
	return eligible[0]["server"]


@frappe.whitelist()
def get_server_recommendation(site_request: str | None = None):
	if SUPER_ADMIN_ROLE not in frappe.get_roles():
		frappe.throw("Not permitted", frappe.PermissionError)
	candidates = get_candidates()
	recommended = next((c["server"] for c in candidates if c["eligible"]), None)
	return {"recommended": recommended, "candidates": candidates}
