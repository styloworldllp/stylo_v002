"""
Nuerix Model Registry — maps branded engine names to Ollama technical model names.
Users see friendly brand names; Ollama receives the actual model identifier.
"""

# Branded name → Ollama model name
NUERIX_ENGINES = {
    "Falcon":      "qwen2.5:1.5b",   # Fast, lightweight — best for quick queries
    "Falcon Pro":  "qwen2.5:3b",     # Balanced — more reasoning capability
    "Kiwi":        "qwen2.5:7b",     # Accurate — complex analysis
    "Kiwi Pro":    "qwen2.5:14b",    # Advanced — deep reasoning
    "Swift":       "llama3.2:1b",    # Lightning fast — simple lookups
    "Swift Pro":   "llama3.2:3b",    # Fast + capable
    "Storm":       "mistral:7b",     # Powerful reasoning
    "Atlas":       "llama3.1:8b",    # Advanced analytics
    "Mint":        "phi3.5:mini",    # Compact & smart
}

# Reverse: Ollama model → branded name (for display)
_REVERSE = {v: k for k, v in NUERIX_ENGINES.items()}


def resolve(branded_name: str) -> str:
    """Convert branded engine name to Ollama model name. Falls back to raw value."""
    return NUERIX_ENGINES.get(branded_name, branded_name)


def display_name(model: str) -> str:
    """Convert Ollama model name to branded name for display. Falls back to raw value."""
    return _REVERSE.get(model, model)


def engine_options() -> str:
    """Return newline-separated options list for Frappe Select field."""
    return "\n".join(NUERIX_ENGINES.keys())
