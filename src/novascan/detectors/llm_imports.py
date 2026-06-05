"""Detect LLM framework imports in source files."""

from __future__ import annotations

import re
from pathlib import Path

FRAMEWORK_PATTERNS = {
    "openai": [r"(?:from|import)\s+openai", r"OpenAI\("],
    "litellm": [r"(?:from|import)\s+litellm", r"litellm\.completion"],
    "langchain": [r"(?:from|import)\s+langchain", r"(?:from|import)\s+langchain_"],
    "transformers": [r"(?:from|import)\s+transformers", r"AutoModelFor", r"AutoTokenizer"],
    "vllm": [r"(?:from|import)\s+vllm", r"LLM\(", r"SamplingParams"],
    "llama_index": [r"(?:from|import)\s+llama_index"],
    "torch": [r"(?:from|import)\s+torch\b"],
    "openvino": [r"(?:from|import)\s+openvino", r"optimum\.intel"],
}


def detect(source_files: list[Path]) -> list[str]:
    """Return list of detected LLM frameworks."""
    detected = set()
    for f in source_files:
        try:
            content = f.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for framework, patterns in FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content):
                    detected.add(framework)
                    break
    return sorted(detected)
