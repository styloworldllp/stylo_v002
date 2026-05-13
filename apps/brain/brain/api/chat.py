import json

import frappe


@frappe.whitelist()
def send(message: str, history: str = "[]", context: str = "{}"):
	"""
	Whitelisted endpoint — receives a chat message and returns the AI response.

	Args:
	    message: User's natural language message
	    history: JSON array of {role, content} — prior conversation turns (text only)
	    context: JSON object with {route, doctype, doc_name} from the browser

	Returns:
	    {message: str, actions: list}
	"""
	if frappe.session.user in ("Guest",):
		frappe.throw("brAIn requires authentication.", frappe.AuthenticationError)

	try:
		history_list = json.loads(history) if isinstance(history, str) else history
	except Exception:
		history_list = []

	try:
		page_context = json.loads(context) if isinstance(context, str) else context
	except Exception:
		page_context = {}

	from brain.ai.agent import run
	result = run(
		user_message=message,
		conversation_history=history_list,
		page_context=page_context,
	)
	return result


@frappe.whitelist()
def get_settings_status():
	"""Returns whether brAIn is configured and enabled (for the UI to show/hide the bubble)."""
	try:
		settings = frappe.get_single("Brain Settings")
		return {
			"enabled": bool(settings.enabled),
			"provider": settings.provider,
			"configured": bool(settings.provider and (settings.get_password("api_key") or "Ollama" in (settings.provider or ""))),
		}
	except Exception:
		return {"enabled": False, "provider": None, "configured": False}
