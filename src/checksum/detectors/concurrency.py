"""Detect concurrency patterns in source files."""

from __future__ import annotations

import re
from pathlib import Path

CONCURRENCY_PATTERNS = {
    "threadpool": r"ThreadPoolExecutor\((?:max_workers\s*=\s*)?(\d+)?\)",
    "asyncio_gather": r"asyncio\.gather\(",
    "aiohttp": r"(?:from|import)\s+aiohttp",
    "batch_size": r"batch_size\s*[:=]\s*(\d+)",
    "max_concurrent": r"max_concurrent\s*[:=]\s*(\d+)",
}


def detect(source_files: list[Path]) -> dict:
    """Return concurrency analysis."""
    max_concurrent = 1
    patterns_found = []

    for f in source_files:
        try:
            content = f.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for name, pattern in CONCURRENCY_PATTERNS.items():
            for match in re.finditer(pattern, content):
                patterns_found.append(name)
                if match.lastindex and match.group(1):
                    val = int(match.group(1))
                    max_concurrent = max(max_concurrent, val)

    return {
        "max_concurrent": max_concurrent,
        "patterns": list(set(patterns_found)),
    }
