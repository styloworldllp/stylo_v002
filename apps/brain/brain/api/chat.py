import json

import frappe
from werkzeug.wrappers import Response as WerkzeugResponse


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
def send_stream(message: str, history: str = "[]", context: str = "{}"):
	"""Streaming SSE endpoint — yields tokens as they arrive so UI updates in real time."""
	if frappe.session.user == "Guest":
		frappe.throw("brAIn requires authentication.", frappe.AuthenticationError)

	try:
		history_list = json.loads(history) if isinstance(history, str) else history
	except Exception:
		history_list = []
	try:
		page_context = json.loads(context) if isinstance(context, str) else context
	except Exception:
		page_context = {}

	from brain.ai.agent import run_stream

	def _generate():
		try:
			for event in run_stream(message, history_list, page_context):
				yield f"data: {json.dumps(event)}\n\n"
		except Exception as e:
			yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

	return WerkzeugResponse(
		_generate(),
		mimetype="text/event-stream",
		headers={
			"Cache-Control": "no-cache",
			"X-Accel-Buffering": "no",
			"Access-Control-Allow-Origin": "*",
		},
	)


def _safe_pw(settings):
	try:
		return settings.get_password("api_key") or ""
	except Exception:
		return ""


@frappe.whitelist()
def get_settings_status():
	"""Returns whether brAIn is configured and enabled (for the UI to show/hide the bubble)."""
	try:
		settings = frappe.get_single("Brain Settings")
		return {
			"enabled": bool(settings.enabled),
			"provider": settings.provider,
			"configured": bool(settings.provider and (_safe_pw(settings) or "Ollama" in (settings.provider or ""))),
		}
	except Exception:
		return {"enabled": False, "provider": None, "configured": False}
