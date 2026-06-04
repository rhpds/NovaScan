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
                    rel = str(f)
                    if name not in model_files:
                        model_files[name] = []
                    model_files[name].append(f"{rel}:{match.start()}")

    return [{"name": name, "files": files[:5]} for name, files in model_files.items()]
