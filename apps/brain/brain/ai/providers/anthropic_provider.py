from .base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
	def __init__(self, api_key: str, model: str, temperature: float = 0.1):
		try:
			import anthropic
		except ImportError:
			raise ImportError("anthropic package not installed. Run: pip install anthropic")

		self.client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
		self.model = model or "claude-sonnet-5"
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

	def stream_text(self, system: str, messages: list, tools: list):
		"""Yield text chunks for the final response using Anthropic streaming."""
		kwargs = dict(
			model=self.model, max_tokens=4096, system=system, messages=messages,
			tools=self._to_anthropic_tools(tools),
		)
		try:
			stream_ctx = self.client.messages.stream(temperature=self.temperature, **kwargs)
			with stream_ctx as stream:
				for text in stream.text_stream:
					yield text
		except Exception as e:
			# Newer models (e.g. Claude Sonnet 5) reject the temperature param outright.
			if "temperature" not in str(e):
				raise
			with self.client.messages.stream(**kwargs) as stream:
				for text in stream.text_stream:
					yield text

	def chat(self, system: str, messages: list, tools: list) -> dict:
		kwargs = dict(
			model=self.model, max_tokens=2048, system=system, messages=messages,
			tools=self._to_anthropic_tools(tools),
		)
		try:
			response = self.client.messages.create(temperature=self.temperature, **kwargs)
		except Exception as e:
			# Newer models (e.g. Claude Sonnet 5) reject the temperature param outright.
			if "temperature" not in str(e):
				raise
			response = self.client.messages.create(**kwargs)

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
