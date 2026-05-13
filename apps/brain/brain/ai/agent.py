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


def get_provider(settings):
	provider_name = settings.provider or "Anthropic (Claude)"

	if "Anthropic" in provider_name:
		from .providers.anthropic_provider import AnthropicProvider
		return AnthropicProvider(
			api_key=settings.get_password("api_key") or "",
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
		api_key=settings.get_password("api_key") or "",
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
