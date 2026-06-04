"""Extract model names from code and config files."""

from __future__ import annotations

import re
from pathlib import Path

MODEL_PATTERNS = [
    r'"([\w/.-]+(?:llama|granite|phi|qwen|deepseek|mistral|gemma|codellama|nomic|starcoder)[\w/.-]*)"',
    r"'([\w/.-]+(?:llama|granite|phi|qwen|deepseek|mistral|gemma|codellama|nomic|starcoder)[\w/.-]*)'",
    r'model["\']?\s*[:=]\s*["\']([^"\']+)["\']',
    r'MODEL_ID["\']?\s*[:=]\s*["\']([^"\']+)["\']',
    r'model_name["\']?\s*[:=]\s*["\']([^"\']+)["\']',
]


FALSE_POSITIVES = {
    "host-passthrough", "v-ideographic", "test-model", "model-1",
    "mock-model", "fake-model", "default-ollama-model", "ollama-model",
}

FALSE_POSITIVE_PREFIXES = ("/", "http:", "https:")


def _is_false_positive(name: str) -> bool:
    if name.lower() in FALSE_POSITIVES:
        return True
    if any(name.startswith(p) for p in FALSE_POSITIVE_PREFIXES):
        return True
    if "$" in name:
        return True
    base = name.split("/")[-1] if "/" in name else name
    if len(base) < 4:
        return True
    return False


def detect(files: list[Path]) -> list[dict]:
    """Return list of {name, files} for detected model references."""
    model_files: dict[str, list[str]] = {}

    for f in files:
        try:
            content = f.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for pattern in MODEL_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                name = match.group(1).strip()
                if len(name) > 3 and ("/" in name or "-" in name):
                    if _is_false_positive(name):
                        continue
                    rel = str(f)
                    if name not in model_files:
                        model_files[name] = []
                    model_files[name].append(f"{rel}:{match.start()}")

    return [{"name": name, "files": files[:5]} for name, files in model_files.items()]
