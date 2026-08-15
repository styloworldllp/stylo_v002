"""
Ingest endpoint for the standalone monitoring agent (command_center/agent/command_center_agent.py)
that runs via cron on every managed server. Also holds the daily purge of old Server Metric rows.

Auth model: the agent has no Frappe user session (it's a bare cron script on a remote box), so
this endpoint is allow_guest=True and instead validates a per-server API key passed in a header,
compared with hmac.compare_digest to avoid timing attacks. Rate-limited to blunt key brute-forcing.
"""

import hmac

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, now_datetime
from frappe.utils.password import get_decrypted_password


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=60)
def ingest():
	data = frappe.local.form_dict
	server_name = data.get("server")
	agent_key = frappe.get_request_header("X-Agent-Key")

	if not server_name or not agent_key:
		frappe.throw("server and X-Agent-Key are required", frappe.PermissionError)

	if not frappe.db.exists("Server", server_name):
		# Don't leak whether the server exists or not beyond a generic denial.
		frappe.throw("Invalid server or key", frappe.PermissionError)

	status = frappe.db.get_value("Server", server_name, "status")
	if status != "Active":
		frappe.throw("Invalid server or key", frappe.PermissionError)

	expected_key = get_decrypted_password("Server", server_name, "agent_api_key", raise_exception=False)
	if not expected_key or not hmac.compare_digest(str(expected_key), str(agent_key)):
		frappe.throw("Invalid server or key", frappe.PermissionError)

	metric = frappe.get_doc(
		{
			"doctype": "Server Metric",
			"server": server_name,
			"timestamp": now_datetime(),
			"cpu_percent": data.get("cpu_percent") or 0,
			"ram_percent": data.get("ram_percent") or 0,
			"disk_percent": data.get("disk_percent") or 0,
			"site_count": data.get("site_count") or 0,
			"load_avg_1m": data.get("load_avg_1m") or 0,
		}
	)
	metric.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"status": "ok"}


def purge_old_metrics():
	"""Daily scheduled task — keeps Server Metric from growing unbounded.
	Only the latest-per-server cache fields on Server matter for live selection (§3);
	history beyond 30 days has no consumer yet."""
	cutoff = add_days(now_datetime(), -30)
	frappe.db.delete("Server Metric", {"timestamp": ["<", cutoff]})
	frappe.db.commit()
