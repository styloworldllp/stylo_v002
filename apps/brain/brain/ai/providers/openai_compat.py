"""
OpenAI-compatible provider — handles OpenAI, Ollama, and any OpenAI-spec endpoint.
Ollama: set base_url="http://localhost:11434/v1" and api_key="ollama"
"""
import json

from .base import BaseLLMProvider


class OpenAICompatProvider(BaseLLMProvider):
	def __init__(self, api_key: str, model: str, base_url: str = None,
	             temperature: float = 0.1, is_local: bool = False):
		try:
			from openai import OpenAI
		except ImportError:
			raise ImportError("openai package not installed. Run: pip install openai")

		self.client = OpenAI(
			api_key=api_key or "ollama",
			base_url=base_url or "https://api.openai.com/v1",
		)
		self.model = model or "gpt-4o"
		self.temperature = temperature
		self.is_local = is_local  # True for Ollama/Nuerix

	def _to_openai_tools(self, tools: list) -> list:
		return [
			{
				"type": "function",
				"function": {
					"name": t["name"],
					"description": t["description"],
					"parameters": t["parameters"],
				},
			}
			for t in tools
		]

	def _normalise_messages(self, messages: list) -> list:
		"""
		Convert Anthropic-style message history to OpenAI format.
		Plain {role, content: str} messages pass through unchanged.
		Anthropic tool-use turns are converted to OpenAI tool_call / tool result turns.
		"""
		out = []
		for msg in messages:
			content = msg.get("content")

			# Plain text message — pass straight through
			if isinstance(content, str):
				out.append({"role": msg["role"], "content": content})
				continue

			# Anthropic content block list
			if isinstance(content, list):
				if msg["role"] == "assistant":
					# Assistant turn containing tool_use blocks
					text = ""
					tool_calls = []
					for block in content:
						block_type = getattr(block, "type", block.get("type") if isinstance(block, dict) else None)
						if block_type == "tool_use":
							name = getattr(block, "name", block.get("name"))
							bid = getattr(block, "id", block.get("id"))
							inp = getattr(block, "input", block.get("input", {}))
							tool_calls.append({
								"id": bid,
								"type": "function",
								"function": {"name": name, "arguments": json.dumps(inp)},
							})
						elif block_type == "text":
							text = getattr(block, "text", block.get("text", ""))

					assistant_msg = {"role": "assistant", "content": text}
					if tool_calls:
						assistant_msg["tool_calls"] = tool_calls
					out.append(assistant_msg)

				elif msg["role"] == "user":
					# User turn containing tool_result blocks
					for block in content:
						block_type = block.get("type") if isinstance(block, dict) else None
						if block_type == "tool_result":
							result_content = block.get("content", "")
							if not isinstance(result_content, str):
								result_content = json.dumps(result_content)
							out.append({
								"role": "tool",
								"tool_call_id": block.get("tool_use_id"),
								"content": result_content,
							})
						else:
							text = block.get("text", str(block)) if isinstance(block, dict) else str(block)
							if text:
								out.append({"role": "user", "content": text})

		return out

	def chat(self, system: str, messages: list, tools: list) -> dict:
		oai_messages = [{"role": "system", "content": system}] + self._normalise_messages(messages)

		kwargs = dict(
			model=self.model,
			messages=oai_messages,
			temperature=self.temperature,
			max_tokens=600,
		)

		if tools:
			kwargs["tools"] = self._to_openai_tools(tools)
			kwargs["tool_choice"] = "auto"

		# Ollama-specific speed params passed via extra_body
		if self.is_local:
			kwargs["extra_body"] = {
				"options": {
					"num_thread": 2,      # use all CPU cores
					"num_predict": 600,   # cap output tokens — don't over-generate
					"num_ctx": 2048,      # keep context window small = faster attention
				}
			}

		response = self.client.chat.completions.create(**kwargs)
		choice = response.choices[0]
		message = choice.message

		if choice.finish_reason == "tool_calls" and message.tool_calls:
			tool_calls = [
				{
					"id": tc.id,
					"name": tc.function.name,
					"input": json.loads(tc.function.arguments or "{}"),
				}
				for tc in message.tool_calls
			]
			return {
				"stop_reason": "tool_use",
				"content": message.content or "",
				"raw_content": message,
				"tool_calls": tool_calls,
			}

		return {
			"stop_reason": "end_turn",
			"content": message.content or "",
			"raw_content": message,
			"tool_calls": [],
		}
