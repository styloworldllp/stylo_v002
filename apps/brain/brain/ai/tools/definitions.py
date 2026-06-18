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

	# ── AI Interaction (browser-side) ────────────────────────────────────────
	{
		"name": "present_action_choice",
		"description": (
			"When a user wants to CREATE or EDIT a record, call this tool FIRST. "
			"It shows a card in the chat with two buttons: 'Fill Form' (AI animates filling each field) "
			"and 'Guide Me' (ghost cursor walks through the form step by step). "
			"Use this for ANY create/add/make/new intent before using fill_form or guide_user directly. "
			"Always call get_doctype_meta first to know required fields."
		),
		"parameters": {
			"type": "object",
			"properties": {
				"doctype": {"type": "string", "description": "DocType to create/edit, e.g. 'Customer'"},
				"title": {"type": "string", "description": "Action title shown on card, e.g. 'Create a New Customer'"},
				"name": {"type": "string", "description": "Existing document name to edit. Omit for new records."},
				"known_values": {
					"type": "object",
					"description": "Field values already known from the user's message, e.g. {\"customer_name\": \"Acme\"}",
				},
				"required_fields": {
					"type": "array",
					"description": "Required fields that still need user input",
					"items": {
						"type": "object",
						"properties": {
							"fieldname": {"type": "string"},
							"label": {"type": "string"},
							"fieldtype": {"type": "string"},
						},
					},
				},
			},
			"required": ["doctype", "title"],
		},
	},
	{
		"name": "fill_form",
		"description": (
			"Open a Frappe form (new or existing) and auto-fill fields with an AI animation. "
			"Use this when the user asks to CREATE or EDIT a specific record and provides field values. "
			"The browser will animate each field being filled with a typewriter + glow effect. "
			"Always call get_doctype_meta first to know the correct fieldnames."
		),
		"parameters": {
			"type": "object",
			"properties": {
				"doctype": {
					"type": "string",
					"description": "DocType to open, e.g. 'Customer', 'Sales Invoice', 'Item'",
				},
				"name": {
					"type": "string",
					"description": "Document name to edit. Omit to open a new blank form.",
				},
				"values": {
					"type": "object",
					"description": "Map of fieldname → value to fill. Use exact Frappe fieldnames.",
				},
			},
			"required": ["doctype", "values"],
		},
	},
	{
		"name": "guide_user",
		"description": (
			"Show a step-by-step AI ghost cursor that walks the user through any workflow — like Claude Computer Use or Atlas. "
			"The cursor physically moves to each element, shows a callout, then AUTO-CLICKS or AUTO-TYPES (brAIn does the action, user just watches). "
			"Use this when the user asks for HELP, GUIDANCE, or 'show me how to do X'. "
			"IMPORTANT — for navigation prefer search_navigate over desktop_icon: it uses the top search bar "
			"(type 'New Customer', click result) which is more reliable than trying to locate a desktop icon. "
			"Target types: "
			"search_navigate (PREFERRED for navigation — types in global search bar and clicks first result), "
			"desktop_icon (home screen app icon), sidebar_item (left nav), "
			"list_new_button (New button in list), form_field (a form input), "
			"form_save_button (Save/Submit button), nav_button (any toolbar button by label), "
			"search_bar (just move cursor to search bar), css_selector (raw CSS for anything else). "
			"For click/type steps brAIn auto-performs the action after 1 second — do NOT wait for the user."
		),
		"parameters": {
			"type": "object",
			"properties": {
				"title": {
					"type": "string",
					"description": "Short title shown in the guide progress bar, e.g. 'How to Add a Customer'",
				},
				"steps": {
					"type": "array",
					"description": "Ordered steps — cursor moves to each target and auto-performs the action",
					"items": {
						"type": "object",
						"properties": {
							"target_type": {
								"type": "string",
								"enum": [
									"search_navigate", "desktop_icon", "sidebar_item", "list_new_button",
									"form_field", "form_save_button", "nav_button",
									"search_bar", "css_selector"
								],
								"description": "Type of element to target. Prefer search_navigate for opening pages/forms.",
							},
							"target_name": {
								"type": "string",
								"description": (
									"For search_navigate: search query text (e.g. 'New Customer', 'Sales Invoice list'). "
									"For desktop_icon: icon label (e.g. 'Accounting'). "
									"For sidebar_item: sidebar label. "
									"For form_field: fieldname (e.g. 'customer_name'). "
									"For nav_button: button text. "
									"For css_selector: raw CSS selector. "
									"Leave empty for list_new_button, form_save_button, search_bar."
								),
							},
							"message": {
								"type": "string",
								"description": "Instruction shown in the callout bubble, e.g. 'Opening Customer form'",
							},
							"action": {
								"type": "string",
								"enum": ["click", "type", "observe"],
								"description": "click=brAIn auto-clicks after 1s, type=brAIn auto-types value or waits for user, observe=auto-advance after 1.8s",
							},
							"value": {
								"type": "string",
								"description": "For type action: the text to auto-type. Omit to wait for user input.",
							},
							"label": {
								"type": "string",
								"description": "Short step label shown in the progress bar, e.g. 'Customer Name'",
							},
						},
						"required": ["target_type", "message", "action"],
					},
				},
			},
			"required": ["title", "steps"],
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

	# ── Market Data (Public benchmarks — no company data sent) ───────────────────
	{
		"name": "get_market_data",
		"description": (
			"Fetch public market benchmarks and reference data for business comparison. "
			"IMPORTANT: This tool only fetches publicly available data — it NEVER sends any company data externally. "
			"Use for: currency exchange rates, RBI policy rates, GST rate tables, commodity prices, "
			"Nifty/Sensex indices, industry benchmark margins, Indian inflation data. "
			"Useful when user wants to compare their business performance against market standards."
		),
		"parameters": {
			"type": "object",
			"properties": {
				"category": {
					"type": "string",
					"enum": [
						"exchange_rates",
						"rbi_rates",
						"gst_rates",
						"commodity_prices",
						"market_indices",
						"industry_benchmarks",
						"inflation_data",
					],
					"description": (
						"exchange_rates: USD/EUR/GBP/etc vs INR. "
						"rbi_rates: Repo rate, reverse repo, CRR, SLR. "
						"gst_rates: GST slab reference table. "
						"commodity_prices: Gold, silver, crude oil (INR). "
						"market_indices: Nifty 50, Sensex current values. "
						"industry_benchmarks: Typical margins by sector (FMCG, IT, manufacturing, etc). "
						"inflation_data: CPI, WPI, current inflation rates."
					),
				},
				"base_currency": {
					"type": "string",
					"description": "For exchange_rates: base currency to convert from, e.g. 'USD', 'EUR'. Default: USD",
					"default": "USD",
				},
			},
			"required": ["category"],
		},
	},

	# ── Stylo Insights (Dashboard Creation) ──────────────────────────────────────
	{
		"name": "insights_get_data_sources",
		"description": (
			"List available Insights data sources the user can query. "
			"Call this first when creating an Insights dashboard to discover "
			"which data sources exist (e.g. 'Local DB', a MariaDB connection). "
			"Returns name, title, database_type, is_site_db for each source."
		),
		"parameters": {
			"type": "object",
			"properties": {},
			"required": [],
		},
	},
	{
		"name": "insights_get_tables",
		"description": (
			"List available tables in a specific Insights data source. "
			"Call after insights_get_data_sources to discover what tables "
			"can be queried (e.g. 'tabSales Invoice', 'tabCustomer'). "
			"Returns table_name, label, data_source for each table."
		),
		"parameters": {
			"type": "object",
			"properties": {
				"data_source": {
					"type": "string",
					"description": "The data source name from insights_get_data_sources, e.g. 'Local DB'",
				},
				"search_term": {
					"type": "string",
					"description": "Optional keyword to filter tables by name or label",
				},
			},
			"required": ["data_source"],
		},
	},
	{
		"name": "insights_create_dashboard",
		"description": (
			"Create a complete Insights v3 dashboard: Workbook + Queries + Charts + Dashboard. "
			"Always call insights_get_data_sources then insights_get_tables first. "
			"Each chart needs: title, chart_type, an operations array (source + summarize), and a config object. "
			"Returns workbook_name and dashboard_name and navigates to the new dashboard."
		),
		"parameters": {
			"type": "object",
			"properties": {
				"workbook_title": {
					"type": "string",
					"description": "Title for the new Insights Workbook, e.g. 'Sales Overview'",
				},
				"dashboard_title": {
					"type": "string",
					"description": "Title for the dashboard inside the workbook",
				},
				"charts": {
					"type": "array",
					"description": "List of chart specifications to create",
					"items": {
						"type": "object",
						"properties": {
							"title": {
								"type": "string",
								"description": "Chart title shown on the dashboard",
							},
							"chart_type": {
								"type": "string",
								"enum": ["Bar", "Line", "Row", "Donut", "Funnel", "Number", "Table"],
								"description": "Type of chart to render. Bar=vertical bars, Row=horizontal bars, Line=trend line, Donut=circular proportion (NOT Pie — use Donut), Number=single KPI card, Table=data grid, Funnel=funnel chart",
							},
							"operations": {
								"type": "array",
								"description": (
									"Insights Query v3 operations array. "
									"First op: {\"type\":\"source\",\"data_source\":\"<ds>\",\"table\":{\"table\":\"<tabName>\",\"label\":\"<Label>\"}}. "
									"Follow with summarize: {\"type\":\"summarize\","
									"\"measures\":[{\"column_name\":str,\"data_type\":\"Decimal\",\"aggregation\":\"sum\"|\"count\"|\"avg\",\"alias\":str}],"
									"\"dimensions\":[{\"column_name\":str,\"data_type\":\"Date\"|\"Data\",\"granularity\":\"month\"|null,\"alias\":str}]}. "
									"Column names must match real Frappe DB column names (e.g. grand_total, posting_date, customer, status). "
									"Alias values must match exactly what you use in chart config column_name fields."
								),
							},
							"config": {
								"type": "object",
								"description": (
									"Chart config object. "
									"Bar/Line/Row: {\"x_axis\":{\"column_name\":\"<alias>\"},\"y_axis\":{\"series\":[{\"column_name\":\"<alias>\"}]},\"order_by\":[],\"limit\":100}. "
									"Number: {\"number_columns\":[{\"column_name\":\"<alias>\"}],\"comparison\":false,\"order_by\":[]}. "
									"Donut (NOT Pie): {\"label_column\":{\"column_name\":\"<alias>\"},\"value_column\":{\"column_name\":\"<alias>\"},\"order_by\":[],\"limit\":10}. "
									"Table: {\"order_by\":[],\"limit\":100}. "
									"column_name values in config must match alias values from operations exactly."
								),
							},
							"layout": {
								"type": "object",
								"description": (
									"Grid layout in a 20-column grid. "
									"{\"x\":0,\"y\":0,\"w\":10,\"h\":8}. "
									"Place 2 charts per row: first at x=0,w=10 then x=10,w=10; next row y+=9. "
									"Number charts: w=10,h=3. Bar/Line/Row/Donut: w=10,h=8."
								),
							},
						},
						"required": ["title", "chart_type", "operations", "config"],
					},
				},
			},
			"required": ["workbook_title", "dashboard_title", "charts"],
		},
	},
]
