app_name = "command_center"
app_title = "Command Center"
app_publisher = "Stylo"
app_description = "Internal ops console for client site provisioning, licensing, capacity and support"
app_email = "hello@stylo.io"
app_license = "mit"
app_icon_route = "/command-center"

# Apps
# ------------------

required_apps = ["stylo_core"]

add_to_apps_screen = [
    {
        "name": "command_center",
        "logo": "/assets/command_center/images/logo.svg",
        "title": "Command Center",
        "route": "/command-center",
        "has_permission": "command_center.api.check_app_permission",
    }
]

website_route_rules = [
    {"from_route": "/command-center", "to_route": "command_center"},
    {"from_route": "/command-center/<path:app_path>", "to_route": "command_center"},
]

# Fixtures — exported/imported with bench import-fixtures
# Note: Workspace must NOT be shipped as a fixture — Frappe's post-migrate orphan
# cleanup only protects workspaces defined at <app>/<module>/workspace/<name>/<name>.json,
# so a fixture-defined public workspace gets deleted again in the same migrate run.
fixtures = [
    {
        "dt": "Role",
        "filters": [
            [
                "role_name",
                "in",
                [
                    "Command Center Super Admin",
                    "Command Center Admin",
                    "Command Center Support Staff",
                ],
            ]
        ],
    },
    {
        "dt": "Custom Field",
        "filters": [["dt", "=", "HD Ticket"], ["fieldname", "=", "site"]],
    },
]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "command_center",
# 		"logo": "/assets/command_center/logo.png",
# 		"title": "Command Center",
# 		"route": "/command_center",
# 		"has_permission": "command_center.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/command_center/css/command_center.css"
# app_include_js = "/assets/command_center/js/command_center.js"

# include js, css files in header of web template
# web_include_css = "/assets/command_center/css/command_center.css"
# web_include_js = "/assets/command_center/js/command_center.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "command_center/public/scss/website"

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
# app_include_icons = "command_center/public/icons.svg"

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
# 	"methods": "command_center.utils.jinja_methods",
# 	"filters": "command_center.utils.jinja_filters"
# }

# Installation
# ------------

after_install = "command_center.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "command_center.uninstall.before_uninstall"
# after_uninstall = "command_center.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "command_center.utils.before_app_install"
# after_app_install = "command_center.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "command_center.utils.before_app_uninstall"
# after_app_uninstall = "command_center.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "command_center.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "command_center.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
    "Site Request": "command_center.command_center.doctype.site_request.site_request.get_permission_query_conditions",
}

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
    "daily": [
        "command_center.api.metrics.purge_old_metrics",
    ],
}

# Testing
# -------

# before_tests = "command_center.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "command_center.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "command_center.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "command_center.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["command_center.utils.before_request"]
# after_request = ["command_center.utils.after_request"]

# Job Events
# ----------
# before_job = ["command_center.utils.before_job"]
# after_job = ["command_center.utils.after_job"]

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
# 	"command_center.auth.validate"
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

