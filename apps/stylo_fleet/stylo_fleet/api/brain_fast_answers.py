"""
Fast-path, non-AI answers for common Stylo Fleet questions.

Rationale: an LLM round trip (network + inference, plus a tool-call round trip
for anything needing live data) cannot realistically go under a few seconds —
that's a hardware/network floor, not something prompt-tuning fixes. For the
small set of high-frequency fleet questions (matching the brAIn welcome-screen
suggestions), we already have a direct, indexed database answer available in
tens of milliseconds via stylo_fleet.api.analytics. This module pattern-matches
the incoming message against those known questions and answers instantly,
bypassing the AI agent entirely. Anything that doesn't match falls through to
the normal (several-second) LLM path — this is not a general NLU replacement,
just an instant lane for the exact questions this app's UI already suggests.
"""
import re

import frappe


def _fmt_table(headers, rows):
	lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
	for row in rows:
		lines.append("| " + " | ".join("" if c is None else str(c) for c in row) + " |")
	return "\n".join(lines)


def _answer_fleet_status():
	from stylo_fleet.api.analytics import get_dashboard_data
	data = get_dashboard_data()
	k = data["kpis"]
	rows = sorted(data["status_breakdown"].items(), key=lambda x: -x[1])
	table = _fmt_table(["Status", "Count"], rows)
	return (
		f"**Fleet Status** — {k['total_active']} active ambulances: "
		f"**{k['available_now']} Available**, **{k['on_call']} On Call**, "
		f"**{k['refill_due_or_insufficient']} need a refill**, "
		f"**{k['maintenance_or_breakdown']} in maintenance**.\n\n{table}"
	)


def _answer_refills_needed():
	from stylo_fleet.api.analytics import get_dashboard_data
	pending = get_dashboard_data()["pending_refills"]
	if not pending:
		return "No ambulances currently need a refill — fleet is clear."
	rows = [[r["ambulance"], r["station"], r["expected_load_quantity"], r["balance_before_refill"]] for r in pending]
	table = _fmt_table(["Ambulance", "Station", "Kits Needed", "Current Balance"], rows)
	return f"**{len(pending)} ambulance(s) need a refill:**\n\n{table}"


def _answer_open_issues():
	from stylo_fleet.api.analytics import get_dashboard_data
	issues = get_dashboard_data()["open_issues"]
	if not issues:
		return "No open Ambulance Issues right now — fleet is clear."
	rows = [[i["ambulance"], i["issue_type"], i.get("severity") or "-", i.get("description") or ""] for i in issues]
	table = _fmt_table(["Ambulance", "Type", "Severity", "Description"], rows)
	return f"**{len(issues)} open issue(s):**\n\n{table}"


def _answer_open_tickets():
	from stylo_fleet.api.ticketing import get_open_tickets
	tickets = get_open_tickets()
	if not tickets:
		return "No open tickets right now."
	rows = [[t["name"], t["subject"], t["category"], t["priority"]] for t in tickets]
	table = _fmt_table(["Ticket", "Subject", "Category", "Priority"], rows)
	return f"**{len(tickets)} open ticket(s):**\n\n{table}"


def _answer_shifts_today():
	from stylo_fleet.api.analytics import get_dashboard_data
	k = get_dashboard_data()["kpis"]
	return (
		f"**{k['shifts_today']} shift(s) started today**, "
		f"**{k['kits_consumed_today']} kits consumed today** across the fleet."
	)


# Ordered: more specific patterns first, since the first match wins.
_PATTERNS = [
	(re.compile(r"\bopen\b.*\bticket", re.I), _answer_open_tickets),
	(re.compile(r"\bopen\b.*\b(ambulance )?issues?\b|\bissues?\b.*\bopen\b", re.I), _answer_open_issues),
	(re.compile(r"\brefill(s|ing)?\b.*\b(need|needs|needed|pending|due)\b|\bwhich ambulances need a refill\b", re.I), _answer_refills_needed),
	(re.compile(r"\bshifts?\b.*\btoday\b|\bkits? consumed\b.*\btoday\b", re.I), _answer_shifts_today),
	(re.compile(r"\bfleet status\b|\bstatus of\b.*\bfleet\b|\bhow many ambulances\b.*\b(available|status)\b|\bwhat.?s our fleet\b", re.I), _answer_fleet_status),
]


def try_fast_answer(message: str):
	"""Return an instant, non-AI markdown answer for a known common fleet
	question, or None if the message doesn't match — callers should fall
	through to the normal AI agent in that case. Silently returns None on
	any error (e.g. permission denied) so the AI agent's own handling takes
	over rather than surfacing a raw exception on the fast path.
	"""
	if not message or "stylo_fleet" not in frappe.get_installed_apps():
		return None
	for pattern, handler in _PATTERNS:
		if pattern.search(message):
			try:
				return handler()
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Brain Fast Answer Failed")
				return None
	return None
