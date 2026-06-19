"""
Tool executor — maps tool names to Frappe operations.
All operations run under the current frappe.session.user context (permissions enforced).
Tools that need browser-side execution return {"_action": {...}} which the frontend processes.
"""
import json

import frappe


def execute_tool(name: str, inputs: dict) -> dict:
	_map = {
		"present_action_choice": _present_action_choice,
		"search_records": _search_records,
		"get_record": _get_record,
		"get_doctype_meta": _get_doctype_meta,
		"run_report": _run_report,
		"global_search": _global_search,
		"count_records": _count_records,
		"create_record": _create_record,
		"update_record": _update_record,
		"submit_document": _submit_document,
		"cancel_document": _cancel_document,
		"delete_record": _delete_record,
		"navigate_to": _navigate_to,
		"fill_form": _fill_form,
		"guide_user": _guide_user,
		"get_value": _get_value,
		"get_system_info": _get_system_info,
		# Market data (public benchmarks)
		"get_market_data": _get_market_data,
		# Stylo Insights
		"insights_get_data_sources":  _insights_get_data_sources,
		"insights_get_tables":        _insights_get_tables,
		"insights_create_dashboard":  _insights_create_dashboard,
	}
	fn = _map.get(name)
	if not fn:
		return {"error": f"Unknown tool: {name}"}
	try:
		return fn(**inputs)
	except frappe.PermissionError as e:
		return {"error": f"Permission denied: {e}"}
	except frappe.DoesNotExistError as e:
		return {"error": f"Record not found: {e}"}
	except Exception as e:
		return {"error": str(e)}


# ── Read ──────────────────────────────────────────────────────────────────────

def _search_records(doctype: str, filters: dict = None, fields: list = None, limit: int = 20, order_by: str = None) -> dict:
	if not frappe.has_permission(doctype, "read"):
		return {"error": f"No read permission on {doctype}"}

	default_fields = ["name", "modified"]
	meta = frappe.get_meta(doctype)
	# Auto-add meaningful display fields
	for fname in ("title", "subject", "customer", "supplier", "employee", "full_name", "status", "grand_total"):
		if meta.has_field(fname) and fname not in default_fields:
			default_fields.append(fname)
			if len(default_fields) >= 6:
				break

	kwargs = {
		"doctype": doctype,
		"filters": filters or [],
		"fields": fields or default_fields,
		"limit": min(int(limit), 100),
	}
	if order_by:
		kwargs["order_by"] = order_by

	records = frappe.get_list(**kwargs)
	return {"doctype": doctype, "count": len(records), "records": records}


def _get_record(doctype: str, name: str) -> dict:
	if not frappe.has_permission(doctype, "read", doc=name):
		return {"error": f"No read permission on {doctype}/{name}"}
	doc = frappe.get_doc(doctype, name)
	# Return as dict, excluding large/binary fields
	data = doc.as_dict()
	# Strip attachment/html noise
	for f in doc.meta.fields:
		if f.fieldtype in ("Attach", "Attach Image", "HTML", "Text Editor") and f.fieldname in data:
			data[f.fieldname] = "[content hidden]"
	return {"doctype": doctype, "name": name, "data": data}


def _get_doctype_meta(doctype: str) -> dict:
	if not frappe.has_permission(doctype, "read"):
		return {"error": f"No read permission on {doctype}"}
	meta = frappe.get_meta(doctype)
	fields = []
	skip_types = {"Section Break", "Column Break", "HTML", "Heading", "Tab Break", "Button"}
	for f in meta.fields:
		if f.fieldtype in skip_types:
			continue
		fields.append({
			"fieldname": f.fieldname,
			"label": f.label,
			"fieldtype": f.fieldtype,
			"required": bool(f.reqd),
			"options": f.options if f.fieldtype in ("Select", "Link", "Table") else None,
		})
	return {
		"doctype": doctype,
		"is_single": bool(meta.issingle),
		"is_submittable": bool(meta.is_submittable),
		"fields": fields,
	}


def _run_report(report_name: str, filters: dict = None) -> dict:
	try:
		from frappe.desk.query_report import run
		result = run(report_name, filters or {})
		return {
			"report": report_name,
			"columns": result.get("columns", []),
			"data": result.get("result", [])[:50],  # Cap rows
			"total_rows": len(result.get("result", [])),
		}
	except Exception as e:
		return {"error": str(e)}


def _global_search(query: str) -> dict:
	try:
		from frappe.utils.global_search import search
		results = search(query, start=0, limit=20)
		return {"query": query, "results": results}
	except Exception as e:
		return {"error": str(e)}


def _count_records(doctype: str, filters: dict = None) -> dict:
	if not frappe.has_permission(doctype, "read"):
		return {"error": f"No read permission on {doctype}"}
	count = frappe.db.count(doctype, filters or [])
	return {"doctype": doctype, "filters": filters, "count": count}


# ── Write ─────────────────────────────────────────────────────────────────────

def _create_record(doctype: str, values: dict) -> dict:
	if not frappe.has_permission(doctype, "create"):
		return {"error": f"No create permission on {doctype}"}
	doc = frappe.new_doc(doctype)
	for k, v in values.items():
		doc.set(k, v)
	doc.insert(ignore_permissions=False)
	frappe.db.commit()
	return {
		"success": True,
		"doctype": doctype,
		"name": doc.name,
		"message": f"Created {doctype}: {doc.name}",
		"_action": {"type": "open_form", "doctype": doctype, "name": doc.name},
	}


def _update_record(doctype: str, name: str, values: dict) -> dict:
	if not frappe.has_permission(doctype, "write", doc=name):
		return {"error": f"No write permission on {doctype}/{name}"}
	doc = frappe.get_doc(doctype, name)
	for k, v in values.items():
		doc.set(k, v)
	doc.save(ignore_permissions=False)
	frappe.db.commit()
	return {
		"success": True,
		"doctype": doctype,
		"name": name,
		"message": f"Updated {doctype}: {name}",
		"_action": {"type": "open_form", "doctype": doctype, "name": name},
	}


def _submit_document(doctype: str, name: str) -> dict:
	if not frappe.has_permission(doctype, "submit", doc=name):
		return {"error": f"No submit permission on {doctype}/{name}"}
	doc = frappe.get_doc(doctype, name)
	doc.submit()
	frappe.db.commit()
	return {
		"success": True,
		"message": f"Submitted {doctype}: {name}",
		"_action": {"type": "open_form", "doctype": doctype, "name": name},
	}


def _cancel_document(doctype: str, name: str) -> dict:
	if not frappe.has_permission(doctype, "cancel", doc=name):
		return {"error": f"No cancel permission on {doctype}/{name}"}
	doc = frappe.get_doc(doctype, name)
	doc.cancel()
	frappe.db.commit()
	return {
		"success": True,
		"message": f"Cancelled {doctype}: {name}",
		"_action": {"type": "open_form", "doctype": doctype, "name": name},
	}


def _delete_record(doctype: str, name: str) -> dict:
	if not frappe.has_permission(doctype, "delete", doc=name):
		return {"error": f"No delete permission on {doctype}/{name}"}
	frappe.delete_doc(doctype, name, ignore_permissions=False)
	frappe.db.commit()
	return {"success": True, "message": f"Deleted {doctype}: {name}"}


# ── Navigation (browser-side) ─────────────────────────────────────────────────

def _navigate_to(type: str, doctype: str = None, name: str = None,
				 workspace: str = None, page: str = None, filters: dict = None) -> dict:
	route_map = {
		"list": ["List", doctype, "List"],
		"form": ["Form", doctype, name],
		"workspace": ["Workspaces", workspace],
		"page": [page],
	}
	route = route_map.get(type, [])
	route = [r for r in route if r]  # strip Nones

	action = {"type": "navigate", "route": route}
	if filters and type == "list":
		action["filters"] = filters

	return {
		"success": True,
		"message": f"Navigating to {' > '.join(str(r) for r in route)}",
		"_action": action,
	}


# ── AI Interaction (browser-side) ─────────────────────────────────────────────

def _present_action_choice(doctype: str, title: str, name: str = None,
							known_values: dict = None, required_fields: list = None) -> dict:
	if not frappe.has_permission(doctype, "read"):
		return {"error": f"No permission on {doctype}"}
	return {
		"success": True,
		"message": f"Choose how to {title}",
		"_action": {
			"type": "action_choice",
			"doctype": doctype,
			"title": title,
			"name": name,
			"known_values": known_values or {},
			"required_fields": required_fields or [],
		},
	}


def _fill_form(doctype: str, values: dict, name: str = None) -> dict:
	if not frappe.has_permission(doctype, "read"):
		return {"error": f"No permission on {doctype}"}
	return {
		"success": True,
		"message": f"Opening {doctype} form and filling {len(values)} fields with AI animation.",
		"_action": {
			"type": "fill_form",
			"doctype": doctype,
			"name": name,
			"values": values,
		},
	}


def _guide_user(title: str, steps: list) -> dict:
	return {
		"success": True,
		"message": f"Starting guided walkthrough: {title} ({len(steps)} steps).",
		"_action": {
			"type": "guide_user",
			"title": title,
			"steps": steps,
		},
	}


# ── Utility ───────────────────────────────────────────────────────────────────

def _get_value(doctype: str, name: str, fieldname: str) -> dict:
	if not frappe.has_permission(doctype, "read", doc=name):
		return {"error": "No read permission"}
	value = frappe.db.get_value(doctype, name, fieldname)
	return {"doctype": doctype, "name": name, "fieldname": fieldname, "value": value}


def _get_system_info() -> dict:
	defaults = frappe.db.get_value(
		"Global Defaults", None,
		["default_company", "default_currency"],
		as_dict=True,
	) or {}
	user = frappe.get_doc("User", frappe.session.user)
	return {
		"company": defaults.get("default_company"),
		"currency": defaults.get("default_currency"),
		"user": frappe.session.user,
		"full_name": user.full_name,
		"roles": frappe.get_roles(frappe.session.user),
		"today": frappe.utils.today(),
	}


# ── Market Data (Public benchmarks, no company data transmitted) ──────────────

def _get_market_data(category: str, base_currency: str = "USD") -> dict:
	"""
	Fetch public market reference data for business benchmarking.
	PRIVACY: Only fetches public data from public APIs — zero company data transmitted.
	"""
	import urllib.request
	import json as _json

	def _http_get(url, timeout=8):
		req = urllib.request.Request(url, headers={"User-Agent": "Nuerix-Market-Data/1.0"})
		with urllib.request.urlopen(req, timeout=timeout) as resp:
			return _json.loads(resp.read().decode())

	if category == "exchange_rates":
		try:
			base = (base_currency or "USD").upper()
			data = _http_get(f"https://open.er-api.com/v6/latest/{base}")
			rates = data.get("rates", {})
			inr_rate = rates.get("INR", "N/A")
			key_pairs = {k: v for k, v in rates.items() if k in ("INR", "USD", "EUR", "GBP", "AED", "SGD", "JPY", "CNY")}
			return {
				"category": "Exchange Rates",
				"base": base,
				"inr_rate": inr_rate,
				"key_rates": key_pairs,
				"source": "open.er-api.com (public)",
				"note": "No company data was transmitted. These are public exchange rates.",
				"last_updated": data.get("time_last_update_utc", ""),
			}
		except Exception as e:
			return {"error": f"Could not fetch exchange rates: {e}"}

	elif category == "rbi_rates":
		# RBI policy rates — updated manually here when they change (RBI site has no public JSON API)
		return {
			"category": "RBI Policy Rates",
			"source": "Reserve Bank of India (indicative — verify at rbi.org.in)",
			"note": "No company data was transmitted. These are public RBI reference rates.",
			"rates": {
				"Repo Rate": "6.50%",
				"Reverse Repo Rate": "3.35%",
				"Marginal Standing Facility (MSF)": "6.75%",
				"Bank Rate": "6.75%",
				"CRR (Cash Reserve Ratio)": "4.00%",
				"SLR (Statutory Liquidity Ratio)": "18.00%",
			},
			"effective_from": "April 2024 (verify latest on rbi.org.in)",
		}

	elif category == "gst_rates":
		return {
			"category": "GST Rate Reference",
			"source": "GST Council India (public)",
			"note": "No company data was transmitted.",
			"slabs": {
				"0%": "Fresh vegetables, milk, eggs, printed books, newspapers, salt, grains",
				"5%": "Branded food, economy flights, fertilizers, drugs/medicine, footwear <₹1000",
				"12%": "Processed food, business flights, mobile phones (basic), printing & stationery",
				"18%": "IT/consulting/telecom services, restaurants, electronics, paints, cement",
				"28%": "Luxury goods, automobiles, tobacco, aerated beverages, premium consumer goods",
			},
			"special": {
				"Gold/Silver/Jewellery": "3%",
				"Diamonds/Precious stones": "0.25%",
				"Affordable housing": "1%",
				"Non-affordable housing": "5%",
			},
			"frappe_doctypes": {
				"GST Tax Template": "For sales and purchase transactions",
				"Item Tax Template": "Override GST rate per item",
				"Tax Category": "Assign tax rules per customer/supplier",
				"Tax Withholding Category": "For TDS configuration",
			},
		}

	elif category == "commodity_prices":
		try:
			# Gold price via public metals API (no key required)
			gold_data = _http_get("https://api.metals.live/v1/spot/gold")
			gold_usd = gold_data[0].get("gold") if isinstance(gold_data, list) and gold_data else None
			# Get INR rate to convert
			fx = _http_get("https://open.er-api.com/v6/latest/USD")
			inr = fx.get("rates", {}).get("INR", 83.5)
			gold_inr_per_gram = round((gold_usd / 31.1035) * inr, 2) if gold_usd else "N/A"
			silver_data = _http_get("https://api.metals.live/v1/spot/silver")
			silver_usd = silver_data[0].get("silver") if isinstance(silver_data, list) and silver_data else None
			silver_inr_per_gram = round((silver_usd / 31.1035) * inr, 2) if silver_usd else "N/A"
			return {
				"category": "Commodity Prices",
				"source": "metals.live + open.er-api.com (public)",
				"note": "No company data was transmitted. Prices are spot rates.",
				"gold_per_gram_inr": gold_inr_per_gram,
				"silver_per_gram_inr": silver_inr_per_gram,
				"usd_inr": inr,
			}
		except Exception as e:
			return {
				"category": "Commodity Prices",
				"error": f"Live fetch failed: {e}",
				"indicative": {
					"Gold (per gram, INR)": "~₹7,200–7,800 (verify on MCX)",
					"Silver (per gram, INR)": "~₹85–95 (verify on MCX)",
					"Crude Oil (per barrel, USD)": "~$75–85 (verify on MCX/NYMEX)",
				},
				"source": "MCX India / NYMEX (verify live prices)",
			}

	elif category == "market_indices":
		return {
			"category": "Indian Market Indices",
			"note": (
				"Live index data requires NSE/BSE API subscriptions. "
				"No company data was transmitted. "
				"For real-time values, visit nseindia.com or bseindia.com."
			),
			"source": "NSE / BSE (public reference)",
			"indices": {
				"Nifty 50": "~22,000–24,500 range (FY 2024-25). Check nseindia.com for live value.",
				"Sensex": "~73,000–80,000 range (FY 2024-25). Check bseindia.com for live value.",
				"Nifty Bank": "~46,000–52,000 range. Check nseindia.com.",
				"Nifty IT": "~35,000–40,000 range. Check nseindia.com.",
			},
			"how_to_compare": (
				"To compare your portfolio or business valuation against these, "
				"use your own data from this ERP with search_records, and compare ratios manually."
			),
		}

	elif category == "industry_benchmarks":
		return {
			"category": "Industry Benchmark Margins (India, indicative)",
			"source": "SEBI/RBI annual reports, CRISIL, public research (indicative)",
			"note": "No company data was transmitted. These are indicative public benchmarks.",
			"gross_profit_margins": {
				"FMCG / Consumer Goods": "40–60%",
				"IT Services / Software": "25–40%",
				"Pharmaceuticals": "50–70%",
				"Manufacturing (General)": "15–35%",
				"Retail / Trading": "10–25%",
				"Construction / Real Estate": "15–30%",
				"Banking / NBFC (NIM)": "3–5%",
				"Textiles": "10–20%",
				"Automobile (OEM)": "10–20%",
				"Hospitality / Hotels": "30–50%",
				"Logistics / Transport": "8–15%",
				"Agriculture / Food Processing": "5–15%",
			},
			"net_profit_margins": {
				"IT Services": "15–25%",
				"FMCG": "10–20%",
				"Pharmaceuticals": "12–22%",
				"Manufacturing": "5–12%",
				"Retail": "2–6%",
				"Real Estate": "8–18%",
			},
			"key_ratios": {
				"Debt-to-Equity (healthy)": "< 1.0 for most sectors",
				"Current Ratio (healthy)": "> 1.5",
				"ROE (good)": "> 15%",
				"ROCE (good)": "> 15%",
			},
		}

	elif category == "inflation_data":
		return {
			"category": "Indian Inflation Data",
			"source": "MOSPI / RBI (indicative — verify at mospi.gov.in)",
			"note": "No company data was transmitted.",
			"data": {
				"CPI Inflation (FY 2024-25)": "~4.5–5.5% (target: 4±2%)",
				"WPI Inflation (FY 2024-25)": "~1–3%",
				"Core CPI (ex food & fuel)": "~3.5–4.5%",
				"Food Inflation": "~6–8%",
				"RBI Inflation Target": "4% (tolerance band 2–6%)",
			},
			"impact": {
				"Cost escalation clause": "Index contracts to CPI for multi-year deals",
				"Raw material pricing": "Track WPI for manufacturing cost planning",
				"Salary revision": "Typically benchmark to CPI + 1–3% premium",
			},
		}

	return {"error": f"Unknown category: {category}"}


# ── Stylo Insights (Dashboard Creation) ───────────────────────────────────────

def _insights_get_data_sources() -> dict:
	"""Return all active Insights Data Source v3 records."""
	try:
		sources = frappe.get_list(
			"Insights Data Source v3",
			fields=["name", "title", "database_type", "is_site_db", "status"],
			filters={"status": "Active"},
		)
		return {"data_sources": [dict(s) for s in sources]}
	except Exception as e:
		return {"error": str(e)}


def _insights_get_tables(data_source: str, search_term: str = None) -> dict:
	"""Return tables available in a given Insights data source."""
	try:
		filters = {"data_source": data_source}
		tables = frappe.get_list(
			"Insights Table v3",
			filters=filters,
			fields=["name", "table", "label", "data_source"],
			limit=200,
		)
		result = [
			{"table_name": t.table, "label": t.label or t.table, "data_source": t.data_source}
			for t in tables
		]
		if search_term:
			q = search_term.lower()
			result = [r for r in result if q in r["table_name"].lower() or q in r["label"].lower()]
		return {"data_source": data_source, "tables": result}
	except Exception as e:
		return {"error": str(e)}


def _insights_create_dashboard(
	workbook_title: str,
	dashboard_title: str,
	charts: list,
) -> dict:
	"""
	Atomically create Insights Workbook → Queries → Charts → Dashboard.
	Returns workbook_name, dashboard_name, and an open_insights_dashboard action.
	"""
	import uuid as _uuid

	try:
		# 1. Create Workbook
		workbook = frappe.new_doc("Insights Workbook")
		workbook.title = workbook_title
		workbook.insert(ignore_permissions=False)
		frappe.db.commit()
		workbook_name = workbook.name

		layout_items = []

		for idx, chart_spec in enumerate(charts):
			chart_title = chart_spec.get("title", f"Chart {idx + 1}")
			chart_type  = chart_spec.get("chart_type", "Bar")
			operations  = chart_spec.get("operations", [])
			config      = chart_spec.get("config", {})
			layout      = chart_spec.get("layout") or {
				"x": (idx % 2) * 10,
				"y": (idx // 2) * 9,
				"w": 10,
				"h": 3 if chart_type == "Number" else 8,
			}

			# 2. Create query
			query = frappe.new_doc("Insights Query v3")
			query.title          = chart_title
			query.workbook       = workbook_name
			query.is_builder_query = 1
			query.operations     = frappe.as_json(operations)
			query.sort_order     = idx
			query.insert(ignore_permissions=False)

			# 3. Create chart — set data_query = query.name to prevent before_save stub
			chart = frappe.new_doc("Insights Chart v3")
			chart.title      = chart_title
			chart.workbook   = workbook_name
			chart.chart_type = chart_type
			chart.query      = query.name
			chart.data_query = query.name  # prevents before_save from creating an orphan stub
			chart.config     = frappe.as_json(config)
			chart.sort_order = idx
			chart.insert(ignore_permissions=False)

			item_id = str(_uuid.uuid4())
			layout_items.append({
				"id":     item_id,
				"type":   "chart",
				"chart":  chart.name,
				"layout": {
					"i": item_id,
					"x": layout.get("x", 0),
					"y": layout.get("y", idx * 9),
					"w": layout.get("w", 10),
					"h": layout.get("h", 8),
				},
			})

		# 4. Create Dashboard
		dashboard = frappe.new_doc("Insights Dashboard v3")
		dashboard.title    = dashboard_title
		dashboard.workbook = workbook_name
		dashboard.items    = frappe.as_json(layout_items)
		dashboard.insert(ignore_permissions=False)
		frappe.db.commit()

		return {
			"success": True,
			"workbook_name":  workbook_name,
			"dashboard_name": dashboard.name,
			"charts_created": len(charts),
			"message": (
				f"Created workbook '{workbook_title}' with {len(charts)} chart(s) "
				f"on dashboard '{dashboard_title}'."
			),
			"_action": {
				"type":      "open_insights_dashboard",
				"workbook":  workbook_name,
				"dashboard": dashboard.name,
			},
		}

	except Exception as e:
		frappe.db.rollback()
		return {"error": str(e)}
