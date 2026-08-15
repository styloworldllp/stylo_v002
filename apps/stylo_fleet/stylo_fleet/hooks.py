app_name = "stylo_fleet"
app_title = "Stylo Fleet"
app_publisher = "Styloworld"
app_description = "Ambulance readiness and fleet operations tracking for Styloworld"
app_email = "support@stylo.io"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "stylo_fleet",
# 		"logo": "/assets/stylo_fleet/logo.png",
# 		"title": "Stylo Fleet",
# 		"route": "/stylo_fleet",
# 		"has_permission": "stylo_fleet.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/stylo_fleet/css/stylo_fleet.css"
# app_include_js = "/assets/stylo_fleet/js/stylo_fleet.js"

# include js, css files in header of web template
# web_include_css = "/assets/stylo_fleet/css/stylo_fleet.css"
# web_include_js = "/assets/stylo_fleet/js/stylo_fleet.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "stylo_fleet/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
page_js = {
    "ambulance-console":   "public/js/dashboard_widgets.js",
    "fleet-dashboard":     "public/js/dashboard_widgets.js",
    "admin-console":       "public/js/dashboard_widgets.js",
    "station-console":     "public/js/dashboard_widgets.js",
    "operations-console":  "public/js/dashboard_widgets.js",
}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "stylo_fleet/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
role_home_page = {
    "Fleet Admin": "app/admin-console",
    "Fleet Operations": "app/operations-console",
    "Fleet Station": "app/station-console",
    "Fleet Paramedic": "app/ambulance-console",
}

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
# 	"methods": "stylo_fleet.utils.jinja_methods",
# 	"filters": "stylo_fleet.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "stylo_fleet.install.before_install"
# after_install = "stylo_fleet.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "stylo_fleet.uninstall.before_uninstall"
# after_uninstall = "stylo_fleet.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "stylo_fleet.utils.before_app_install"
# after_app_install = "stylo_fleet.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "stylo_fleet.utils.before_app_uninstall"
# after_app_uninstall = "stylo_fleet.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "stylo_fleet.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "stylo_fleet.notifications.get_notification_config"

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
        "stylo_fleet.tasks.refresh_all_gps_status",
    ],
}

# scheduler_events = {
# 	"all": [
# 		"stylo_fleet.tasks.all"
# 	],
# 	"daily": [
# 		"stylo_fleet.tasks.daily"
# 	],
# 	"hourly": [
# 		"stylo_fleet.tasks.hourly"
# 	],
# 	"weekly": [
# 		"stylo_fleet.tasks.weekly"
# 	],
# 	"monthly": [
# 		"stylo_fleet.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "stylo_fleet.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "stylo_fleet.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "stylo_fleet.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "stylo_fleet.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["stylo_fleet.utils.before_request"]
# after_request = ["stylo_fleet.utils.after_request"]

# Job Events
# ----------
# before_job = ["stylo_fleet.utils.before_job"]
# after_job = ["stylo_fleet.utils.after_job"]

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
# 	"stylo_fleet.auth.validate"
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

