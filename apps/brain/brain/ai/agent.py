"""
brAIn agentic loop.
Runs multi-turn tool-use with the configured LLM provider until the task is complete.
"""
import json

import frappe

from .context import get_accessible_doctypes, get_page_context
from .system_prompt import build_system_prompt
from .tools.definitions import TOOL_DEFINITIONS
from .tools.executor import execute_tool


def get_settings():
	return frappe.get_single("Brain Settings")


def _safe_get_password(settings, fieldname: str) -> str:
	"""Return password value without raising if field is empty/unset."""
	try:
		return settings.get_password(fieldname) or ""
	except Exception:
		return ""


def get_provider(settings):
	provider_name = settings.provider or "Anthropic (Claude)"

	if "Anthropic" in provider_name:
		from .providers.anthropic_provider import AnthropicProvider
		return AnthropicProvider(
			api_key=_safe_get_password(settings, "api_key"),
			model=settings.model or "claude-sonnet-4-6",
			temperature=float(settings.temperature or 0.1),
		)

	if "Ollama" in provider_name:
		from .providers.openai_compat import OpenAICompatProvider
		base_url = settings.base_url or "http://localhost:11434/v1"
		return OpenAICompatProvider(
			api_key="ollama",
			model=settings.model or "llama3.1",
			base_url=base_url,
			temperature=float(settings.temperature or 0.1),
		)

	# OpenAI or any OpenAI-compatible endpoint
	from .providers.openai_compat import OpenAICompatProvider
	return OpenAICompatProvider(
		api_key=_safe_get_password(settings, "api_key"),
		model=settings.model or "gpt-4o",
		base_url=settings.base_url or None,
		temperature=float(settings.temperature or 0.1),
	)


def run(user_message: str, conversation_history: list, page_context: dict) -> dict:
	"""
	Main entry point for the brAIn agent.

	Args:
	    user_message: The current user's message
	    conversation_history: List of {role, content} from previous turns (plain text only)
	    page_context: {route, doctype, doc_name} from the browser

	Returns:
	    {message: str, actions: list}
	    actions: browser-side operations [{type: "navigate"|"open_form", ...}]
	"""
	settings = get_settings()

	if not settings.enabled:
		return {"message": "brAIn is currently disabled. Enable it in Brain Settings.", "actions": []}

	# Build full context
	full_ctx = get_page_context(
		route=page_context.get("route"),
		doctype=page_context.get("doctype"),
		doc_name=page_context.get("doc_name"),
		ui=page_context.get("ui"),
		insights_ctx=page_context.get("insights_ctx"),
	)
	accessible_doctypes = get_accessible_doctypes()
	system = build_system_prompt(full_ctx, accessible_doctypes)

	# Build initial message list for this turn
	messages = list(conversation_history)  # Plain text prior turns
	messages.append({"role": "user", "content": user_message})

	provider = get_provider(settings)
	max_iter = int(settings.max_iterations or 10)
	all_actions = []
	final_text = ""

	for iteration in range(max_iter):
		response = provider.chat(system=system, messages=messages, tools=TOOL_DEFINITIONS)

		if response["stop_reason"] == "end_turn":
			final_text = response["content"]
			break

		if response["stop_reason"] == "tool_use":
			tool_calls = response["tool_calls"]

			# Add assistant message with tool_use blocks to history
			messages.append({
				"role": "assistant",
				"content": response["raw_content"],
			})

			# Execute all tool calls in this batch
			tool_results_content = []
			for call in tool_calls:
				# Push real-time progress to browser via Socket.io
				label = _TOOL_LABELS.get(call["name"], f"⚙️ Running {call['name']}…")
				try:
					frappe.publish_realtime("brain_progress", {"label": label}, user=frappe.session.user)
				except Exception:
					pass

				result = execute_tool(call["name"], call["input"])

				# Extract browser-side action if present
				action = result.pop("_action", None)
				if action:
					all_actions.append(action)

				tool_results_content.append({
					"type": "tool_result",
					"tool_use_id": call["id"],
					"content": json.dumps(result, default=str),
				})

			# Add tool results to history
			messages.append({
				"role": "user",
				"content": tool_results_content,
			})

			# If there was also text in the assistant response, use it as interim
			if response["content"]:
				final_text = response["content"]

		else:
			# Unexpected stop reason
			final_text = response.get("content", "I encountered an unexpected issue.")
			break

	if not final_text:
		final_text = "I've completed the requested operations."

	return {"message": final_text, "actions": all_actions}


# Tool labels shown in the streaming UI while tools are running
_TOOL_LABELS = {
	"search_records":   "🔍 Searching records…",
	"get_record":       "📄 Reading document…",
	"get_doctype_meta": "📋 Checking fields…",
	"count_records":    "🔢 Counting records…",
	"run_report":       "📊 Running report…",
	"global_search":    "🔍 Searching…",
	"create_record":    "✏️ Creating record…",
	"update_record":    "✏️ Updating record…",
	"submit_document":  "✅ Submitting document…",
	"cancel_document":  "🚫 Cancelling document…",
	"delete_record":    "🗑️ Deleting record…",
	"navigate_to":      "🔗 Navigating…",
	"fill_form":        "✨ Opening form…",
	"guide_user":       "🎯 Starting guide…",
	"get_value":        "📌 Getting value…",
	"get_system_info":  "ℹ️ Getting info…",
	# Stylo Insights
	"insights_get_data_sources":  "🗄️ Fetching data sources…",
	"insights_get_tables":        "📋 Listing tables…",
	"insights_create_dashboard":  "✨ Building dashboard…",
}


def run_stream(user_message: str, conversation_history: list, page_context: dict):
	"""
	Streaming version of run(). Yields SSE-compatible event dicts:
	  {type: 'tool',  label: str}         — while a tool is running
	  {type: 'chunk', text: str}           — text token from final response
	  {type: 'done',  message: str, actions: list}  — final complete event
	"""
	settings = get_settings()
	if not settings.enabled:
		yield {"type": "done", "message": "brAIn is currently disabled. Enable it in Brain Settings.", "actions": []}
		return

	full_ctx = get_page_context(
		route=page_context.get("route"),
		doctype=page_context.get("doctype"),
		doc_name=page_context.get("doc_name"),
		ui=page_context.get("ui"),
		insights_ctx=page_context.get("insights_ctx"),
	)
	accessible_doctypes = get_accessible_doctypes()
	system = build_system_prompt(full_ctx, accessible_doctypes)

	messages = list(conversation_history)
	messages.append({"role": "user", "content": user_message})

	provider = get_provider(settings)
	max_iter = int(settings.max_iterations or 10)
	all_actions = []
	final_text = ""

	for iteration in range(max_iter):
		response = provider.chat(system=system, messages=messages, tools=TOOL_DEFINITIONS)

		if response["stop_reason"] == "end_turn":
			# Stream the final text token by token if provider supports it
			content = response["content"] or "I've completed the requested operations."
			# Emit in small chunks for streaming feel
			chunk_size = 4
			for i in range(0, len(content), chunk_size):
				yield {"type": "chunk", "text": content[i:i + chunk_size]}
			final_text = content
			break

		if response["stop_reason"] == "tool_use":
			tool_calls = response["tool_calls"]
			messages.append({"role": "assistant", "content": response["raw_content"]})

			tool_results_content = []
			for call in tool_calls:
				label = _TOOL_LABELS.get(call["name"], f"⚙️ Running {call['name']}…")
				yield {"type": "tool", "label": label}

				result = execute_tool(call["name"], call["input"])
				action = result.pop("_action", None)
				if action:
					all_actions.append(action)

				tool_results_content.append({
					"type": "tool_result",
					"tool_use_id": call["id"],
					"content": json.dumps(result, default=str),
				})

			messages.append({"role": "user", "content": tool_results_content})
			if response["content"]:
				final_text = response["content"]
		else:
			final_text = response.get("content", "I encountered an unexpected issue.")
			break

	if not final_text:
		final_text = "I've completed the requested operations."

	yield {"type": "done", "message": final_text, "actions": all_actions}
