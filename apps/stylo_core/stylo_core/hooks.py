# ─────────────────────────────────────────────────────────────────────────────
# stylo_core/hooks.py
#
# Frappe app manifest — this file is loaded by Frappe at startup to register
# everything this app provides: metadata, asset injections, and event hooks.
#
# Architecture note:
#   stylo_core is a thin overlay app installed on top of the standard Frappe
#   bench.  It owns all Styloworld branding (CSS, JS) and both tiers of the
#   license system:
#     1. Domain-level HMAC key  → license.validate_license  (before_request)
#     2. Per-user license check → user_license.check_user_license_on_login
#                                 (on_login)
# ─────────────────────────────────────────────────────────────────────────────
app_name = "stylo_core"
app_title = "Stylo Core"
app_publisher = "Styloworld"
app_description = "Styloworld — Branding and customizations layer"
app_email = "hello@styloworld.io"
app_license = "mit"
app_logo_url = "/assets/stylo_core/images/stylo-logo-light.png"

# Includes in <head>
# ------------------

# Desk (authenticated Frappe UI) — inject brand CSS and JS overrides
app_include_js = [
    "/assets/stylo_core/js/stylo_overrides.js",
    "/assets/stylo_core/js/license_lock.js",
]
app_include_css = [
    "/assets/stylo_core/css/stylo_theme.css",
    "/assets/stylo_core/css/stylo_icons.css",
]

# License enforcement — runs before every request
before_request = ["stylo_core.license.validate_license"]

# Per-user license check on login
on_login = ["stylo_core.user_license.check_user_license_on_login"]

# Re-apply Stylo icons and white-label after every migrate
after_migrate = ["stylo_core.install_icons.run"]

# include js, css files in header of web template
# web_include_css = "/assets/stylo_core/css/stylo_core.css"
# web_include_js = "/assets/stylo_core/js/stylo_core.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "stylo_core/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "stylo_core/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "stylo_core.utils.jinja_methods",
# 	"filters": "stylo_core.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "stylo_core.install.before_install"
# after_install = "stylo_core.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "stylo_core.uninstall.before_uninstall"
# after_uninstall = "stylo_core.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "stylo_core.utils.before_app_install"
# after_app_install = "stylo_core.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "stylo_core.utils.before_app_uninstall"
# after_app_uninstall = "stylo_core.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "stylo_core.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "stylo_core.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
    "all": [
        "stylo_core.user_license.refresh_licensed_users",  # polls Control Center every 5 min
    ],
    "daily": [
        "stylo_core.license_management.check_expiring_licenses",  # renewal notifications + status sync
    ],
}

# Testing
# -------

# before_tests = "stylo_core.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "stylo_core.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "stylo_core.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "stylo_core.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["stylo_core.utils.before_request"]
# after_request = ["stylo_core.utils.after_request"]

# Job Events
# ----------
# before_job = ["stylo_core.utils.before_job"]
# after_job = ["stylo_core.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"stylo_core.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

