"""
"Run Command" — a deliberately non-interactive alternative to a full web terminal. A single
shell command runs on the chosen Server over the same SSH infrastructure deploy.py uses,
output returns synchronously, and every run is logged to Deploy Log for audit — same trust
model as the rest of Command Center's automation, no new attack surface (no PTY, no
websocket-relayed shell, no session hijacking risk beyond normal API auth).

Deliberately Super Admin only — arbitrary command execution is the highest-privilege action
this app can take.
"""

import frappe
from frappe.rate_limiter import rate_limit

from command_center.api.deploy import SUPER_ADMIN_ROLE, _bench_prefix, _get_ssh_client, _log


@frappe.whitelist()
@rate_limit(limit=20, seconds=60)
def run_command(server: str, command: str):
	if SUPER_ADMIN_ROLE not in frappe.get_roles():
		frappe.throw("Not permitted", frappe.PermissionError)

	if not command or not command.strip():
		frappe.throw("Command is required")

	server_doc = frappe.get_doc("Server", server)
	client = _get_ssh_client(server_doc)
	# Every exec_command() call is a fresh, non-interactive shell (no ~/.bashrc, no prior
	# `cd`, no PATH customizations) — matches deploy.py's _bench_prefix convention so a
	# bare `bench ...` command works the same way here as it does in the automated deploy
	# steps, instead of failing with "command not found" on servers (e.g. stangroup) where
	# bench isn't symlinked onto the default PATH.
	full_command = f"{_bench_prefix(server_doc.bench_path)} {command}" if server_doc.bench_path else command
	try:
		stdin, stdout, stderr = client.exec_command(full_command, timeout=60)
		exit_code = stdout.channel.recv_exit_status()
		out = stdout.read().decode(errors="replace")
		err = stderr.read().decode(errors="replace")
	finally:
		client.close()

	success = exit_code == 0
	output = f"$ {full_command}\n\n--- stdout ---\n{out}\n--- stderr ---\n{err}"
	_log(None, None, f"run_command@{server}", output, success)

	return {"exit_code": exit_code, "stdout": out, "stderr": err}
