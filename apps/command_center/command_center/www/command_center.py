import frappe
from frappe import _
from frappe.translate import get_messages_for_boot, get_translated_doctypes
from frappe.utils import cint, get_system_timezone

no_cache = 1


def get_context():
	from command_center.api import check_app_permission

	if not check_app_permission():
		frappe.throw(_("You do not have permission to access Stylo Command Center"), frappe.PermissionError)

	frappe.db.commit()
	context = frappe._dict()
	context.boot = get_boot()
	return context


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw(_("This method is only meant for developer mode"))
	return get_boot()


def get_boot():
	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"default_route": "/command-center",
			"site_name": frappe.local.site,
			"csrf_token": frappe.sessions.get_csrf_token(),
			"setup_complete": cint(frappe.get_system_settings("setup_complete")),
			"sysdefaults": frappe.defaults.get_defaults(),
			"user_roles": frappe.get_roles(),
			"translated_doctypes": get_translated_doctypes(),
			"translated_messages": get_messages_for_boot(),
			"timezone": {
				"system": get_system_timezone(),
				"user": frappe.db.get_value("User", frappe.session.user, "time_zone")
				or get_system_timezone(),
			},
		}
	)
