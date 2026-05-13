from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
	"""
	Unified interface for all LLM providers.
	All providers receive Anthropic-style message history and convert internally.
	"""

	@abstractmethod
	def chat(self, system: str, messages: list, tools: list) -> dict:
		"""
		Send a chat request to the provider.

		Args:
		    system: System prompt string
		    messages: List of {role, content} dicts (Anthropic format for tool results)
		    tools: List of internal tool spec dicts

		Returns dict with keys:
		    stop_reason: "end_turn" | "tool_use"
		    content: str — assistant's text response (may be empty during tool use)
		    raw_content: provider-native content (stored back into messages for next turn)
		    tool_calls: list of {id, name, input} — populated when stop_reason == "tool_use"
		"""
		...
