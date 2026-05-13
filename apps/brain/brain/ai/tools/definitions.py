"""
Tool schema definitions — provider-agnostic internal format.
Each tool has: name, description, parameters (JSON Schema).
"""

TOOL_DEFINITIONS = [
	# ── Read ──────────────────────────────────────────────────────────────────
	{
		"name": "search_records",
		"description": (
			"Search for records in any Frappe DocType. Use this to find, list, or filter records. "
			"Returns a list of matching records."
		),
		"parameters": {
			"type": "object",
			"properties": {
				"doctype": {
					"type": "string",
					"description": "The DocType name, e.g. 'Sales Invoice', 'Customer', 'Purchase Order'",
				},
				"filters": {
					"type": "object",
					"description": "Filter object. e.g. {\"status\": \"Overdue\"} or {\"customer\": \"Acme Corp\"}",
				},
				"fields": {
					"type": "array",
					"items": {"type": "string"},
					"description": "Fields to return. Defaults to ['name', 'creation', 'modified']",
				},
				"limit": {
					"type": "integer",
					"description": "Max records to return (default 20, max 100)",
					"default": 20,
				},
				"order_by": {
					"type": "string",
					"description": "e.g. 'modified desc' or 'grand_total desc'",
				},
			},
			"required": ["doctype"],
		},
	},
	{
		"name": "get_record",
		"description": "Fetch a single record by doctype and name. Returns all fields of the document.",
		"parameters": {
			"type": "object",
			"properties": {
				"doctype": {"type": "string"},
				"name": {"type": "string", "description": "The document name/ID"},
			},
			"required": ["doctype", "name"],
		},
	},
	{
		"name": "get_doctype_meta",
		"description": (
			"Get field definitions for a DocType. Call this before creating or updating records "
			"to understand what fields exist, their types, and which are required."
		),
		"parameters": {
			"type": "object",
			"properties": {
				"doctype": {"type": "string"},
			},
			"required": ["doctype"],
		},
	},
	{
		"name": "run_report",
		"description": "Execute a named Frappe report and return its data.",
		"parameters": {
			"type": "object",
			"properties": {
				"report_name": {"type": "string", "description": "Full name of the report"},
				"filters": {
					"type": "object",
					"description": "Report filter values as key-value pairs",
				},
			},
			"required": ["report_name"],
		},
	},
	{
		"name": "global_search",
		"description": "Perform a global search across all DocTypes and return matching records.",
		"parameters": {
			"type": "object",
			"properties": {
				"query": {"type": "string", "description": "Search term"},
			},
			"required": ["query"],
		},
	},
	{
		"name": "count_records",
		"description": "Count records in a DocType matching given filters.",
		"parameters": {
			"type": "object",
			"properties": {
				"doctype": {"type": "string"},
				"filters": {"type": "object"},
			},
			"required": ["doctype"],
		},
	},

	# ── Write ─────────────────────────────────────────────────────────────────
	{
		"name": "create_record",
		"description": (
			"Create a new record in a DocType. "
			"Always call get_doctype_meta first to know required fields. "
			"Returns the created document name."
		),
		"parameters": {
			"type": "object",
			"properties": {
				"doctype": {"type": "string"},
				"values": {
					"type": "object",
					"description": "Field values for the new document",
				},
			},
			"required": ["doctype", "values"],
		},
	},
	{
		"name": "update_record",
		"description": "Update fields on an existing record.",
		"parameters": {
			"type": "object",
			"properties": {
				"doctype": {"type": "string"},
				"name": {"type": "string"},
				"values": {
					"type": "object",
					"description": "Fields to update with their new values",
				},
			},
			"required": ["doctype", "name", "values"],
		},
	},
	{
		"name": "submit_document",
		"description": "Submit a submittable document (e.g. Sales Invoice, Purchase Order). Moves it from Draft to Submitted.",
		"parameters": {
			"type": "object",
			"properties": {
				"doctype": {"type": "string"},
				"name": {"type": "string"},
			},
			"required": ["doctype", "name"],
		},
	},
	{
		"name": "cancel_document",
		"description": "Cancel a submitted document. Only possible when document is in Submitted state.",
		"parameters": {
			"type": "object",
			"properties": {
				"doctype": {"type": "string"},
				"name": {"type": "string"},
			},
			"required": ["doctype", "name"],
		},
	},
	{
		"name": "delete_record",
		"description": (
			"Permanently delete a record. "
			"IMPORTANT: Always confirm with the user before deleting. "
			"Only delete Draft or Cancelled documents."
		),
		"parameters": {
			"type": "object",
			"properties": {
				"doctype": {"type": "string"},
				"name": {"type": "string"},
			},
			"required": ["doctype", "name"],
		},
	},

	# ── Navigation (browser-side) ─────────────────────────────────────────────
	{
		"name": "navigate_to",
		"description": (
			"Navigate the user's browser to a page, list view, or form. "
			"This is executed client-side. Use to take the user directly to relevant records."
		),
		"parameters": {
			"type": "object",
			"properties": {
				"type": {
					"type": "string",
					"enum": ["list", "form", "workspace", "report", "page", "custom"],
					"description": "Type of destination",
				},
				"doctype": {
					"type": "string",
					"description": "DocType name — required for 'list' and 'form' types",
				},
				"name": {
					"type": "string",
					"description": "Document name — required for 'form' type",
				},
				"workspace": {
					"type": "string",
					"description": "Workspace name — for 'workspace' type",
				},
				"page": {
					"type": "string",
					"description": "Page name — for 'page' type",
				},
				"filters": {
					"type": "object",
					"description": "Pre-applied filters when navigating to list view",
				},
			},
			"required": ["type"],
		},
	},

	# ── Utility ───────────────────────────────────────────────────────────────
	{
		"name": "get_value",
		"description": "Get a single field value from a document.",
		"parameters": {
			"type": "object",
			"properties": {
				"doctype": {"type": "string"},
				"name": {"type": "string"},
				"fieldname": {"type": "string"},
			},
			"required": ["doctype", "name", "fieldname"],
		},
	},
	{
		"name": "get_system_info",
		"description": "Get system-level information: company name, currency, fiscal year, current user details.",
		"parameters": {
			"type": "object",
			"properties": {},
			"required": [],
		},
	},
]
