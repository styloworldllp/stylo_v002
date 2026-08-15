"""
Module → app list mapping, mirrored from stylo_modules/<module>/apps.txt.

stylo_modules/*/apps.txt remains the source of truth (read by the bash scripts and by
humans). This is a bundled copy so the deployment job (api/deploy.py), which runs on the
Command Center server rather than the target server, can resolve "install these modules"
into "install these apps" without needing filesystem access to stylo_modules/ at runtime
(the target site lives on a different, remote machine).

Keep in sync with stylo_modules/README.md when a module's app list changes.
"""

import frappe

MODULE_APPS = {
	"stylo_core": ["frappe", "stylo_core"],
	"stylo_bms": ["payments", "erpnext", "india_compliance"],
	"stylo_hr": ["hrms"],
	"stylo_crm": ["crm"],
	"stylo_brain": ["brain"],
	"stylo_analytics": ["insights"],
	"stylo_lms": ["lms"],
	"stylo_lending": ["lending"],
	"stylo_desk": ["telephony", "helpdesk"],
	"stylo_reco": ["mint"],
	"stylo_command_center": ["command_center"],
}

# stylo_core must always be installed first; order otherwise follows stylo_modules/README.md.
MODULE_ORDER = list(MODULE_APPS.keys())


def resolve_apps(module_keys: list[str]) -> list[str]:
	"""Expand a list of module keys into an ordered, deduplicated list of apps to install."""
	seen = set()
	apps = []
	ordered_keys = [m for m in MODULE_ORDER if m in module_keys] + [
		m for m in module_keys if m not in MODULE_ORDER
	]
	for module_key in ordered_keys:
		for app in MODULE_APPS.get(module_key, []):
			if app not in seen:
				seen.add(app)
				apps.append(app)
	return apps


def detect_modules(installed_apps: list[str]) -> list[str]:
	"""Reverse of resolve_apps() — given a site's actual installed app list (e.g. from
	`bench list-apps`), return which Stylo modules are present. A module counts as present
	only if ALL of its constituent apps are installed (stylo_bms needs payments+erpnext+
	india_compliance all present, not just one of them)."""
	installed = set(installed_apps)
	return [
		module_key
		for module_key in MODULE_ORDER
		if MODULE_APPS[module_key] and set(MODULE_APPS[module_key]).issubset(installed)
	]


@frappe.whitelist()
def get_module_choices():
	"""Frontend dropdown source — the 11 Stylo module keys in canonical order."""
	return MODULE_ORDER
