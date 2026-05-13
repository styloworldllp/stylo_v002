from .base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
	def __init__(self, api_key: str, model: str, temperature: float = 0.1):
		try:
			import anthropic
		except ImportError:
			raise ImportError("anthropic package not installed. Run: pip install anthropic")

		self.client = anthropic.Anthropic(api_key=api_key)
		self.model = model or "claude-sonnet-4-6"
		self.temperature = temperature

	def _to_anthropic_tools(self, tools: list) -> list:
		return [
			{
				"name": t["name"],
				"description": t["description"],
				"input_schema": t["parameters"],
			}
			for t in tools
		]

	def chat(self, system: str, messages: list, tools: list) -> dict:
		response = self.client.messages.create(
			model=self.model,
			max_tokens=4096,
			temperature=self.temperature,
			system=system,
			messages=messages,
			tools=self._to_anthropic_tools(tools),
		)

		text = next((b.text for b in response.content if hasattr(b, "text")), "")

		if response.stop_reason == "tool_use":
			tool_calls = [
				{"id": b.id, "name": b.name, "input": b.input}
				for b in response.content
				if b.type == "tool_use"
			]
			return {
				"stop_reason": "tool_use",
				"content": text,
				"raw_content": response.content,
				"tool_calls": tool_calls,
			}

		return {
			"stop_reason": "end_turn",
			"content": text,
			"raw_content": response.content,
			"tool_calls": [],
		}
