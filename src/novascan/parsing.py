"""Shared resource quantity parsers for K8s CPU, memory, and storage values."""

from __future__ import annotations

import re


def parse_cpu(val) -> float:
    """Parse CPU quantity (e.g., '500m', '2', '1.5')."""
    val = str(val).strip().strip('"').strip("'")
    if not val or val == "0":
        return 0.0
    if val.endswith("m"):
        try:
            return float(val[:-1]) / 1000
        except ValueError:
            return 0.0
    try:
        return float(val)
    except ValueError:
        return 0.0


def parse_mem_gb(val) -> float:
    """Parse memory/storage quantity to GB (e.g., '8Gi', '512Mi', '10G')."""
    val = str(val).strip().strip('"').strip("'")
    if not val or val == "0":
        return 0.0
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(Gi|Mi|Ki|G|M|K|Ti)?$", val)
    if not match:
        try:
            return float(val)
        except ValueError:
            return 0.0
    num = float(match.group(1))
    unit = match.group(2) or ""
    multipliers = {
        "Ki": 1 / 1048576,
        "Mi": 1 / 1024,
        "Gi": 1,
        "Ti": 1024,
        "K": 1 / 1000000,
        "M": 1 / 1000,
        "G": 1,
    }
    return num * multipliers.get(unit, 1)
