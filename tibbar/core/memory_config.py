# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Load memory layout from YAML config. Used by Tibbar to know where code/data go."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_DATA_RESERVE = 256 * 1024


def get_schema_path() -> Path:
    """Path to the memory config JSON Schema (for validation of user and default configs)."""
    return Path(__file__).resolve().parent.parent / "config" / "memory_config_schema.json"


def _parse_int(v: Any) -> int:
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        return int(v, 0)
    raise TypeError(f"Expected int or hex string, got {type(v)}")


def validate_memory_config(raw: dict[str, Any], path: Path | None = None) -> None:
    """Validate parsed YAML against the memory config schema. Raises ValueError on failure."""
    import jsonschema

    schema_path = get_schema_path()
    schema = json.loads(schema_path.read_text())
    try:
        jsonschema.validate(instance=raw, schema=schema)
    except jsonschema.ValidationError as e:
        loc = f" ({path})" if path else ""
        msg = getattr(e, "message", str(e))
        raise ValueError(f"Memory config schema validation failed{loc}: {msg}") from e


def load_memory_config(path: Path) -> tuple[list[dict[str, Any]], int, int | None]:
    """Load and validate memory config from YAML. Returns (banks, data_reserve, boot_offset).
    Banks have name, base, size, code, data, access. data_reserve is used when code and data
    share one bank (bytes reserved at end). boot_offset: 0-based offset into code region for
    execution start; None means randomise boot address.
    """
    import yaml

    raw = yaml.safe_load(path.read_text())
    if not raw:
        raise ValueError(f"Memory config is empty: {path}")
    validate_memory_config(raw, path)

    mem = raw["memory"]
    banks_raw = mem.get("banks", [])
    data_reserve = int(mem.get("data_reserve", DEFAULT_DATA_RESERVE))
    if data_reserve < 1:
        data_reserve = DEFAULT_DATA_RESERVE
    boot_raw = mem.get("boot")
    boot_offset: int | None = _parse_int(boot_raw) if boot_raw is not None else None
    if boot_offset is not None and boot_offset < 0:
        boot_offset = None

    out: list[dict[str, Any]] = []
    for i, b in enumerate(banks_raw):
        name = b.get("name", f"bank{i}")
        base = _parse_int(b.get("base", 0))
        size = _parse_int(b.get("size", 0))
        code = b.get("code", True)
        data = b.get("data", False)
        access = b.get("access", "rwx")
        if not isinstance(access, str):
            access = str(access)
        out.append(
            {
                "name": name,
                "base": base,
                "size": size,
                "code": bool(code),
                "data": bool(data),
                "access": access.strip().lower(),
            }
        )
    return (out, data_reserve, boot_offset)


def resolve_memory_from_config(
    banks: list[dict[str, Any]],
) -> tuple[int, int, int | None, int | None, list[dict[str, Any]]]:
    """From parsed banks, return (code_region_size, load_addr,
    separate_data_size, data_base, banks).
    - code_region_size: size of the first code bank (max_size for MemoryStore).
    - load_addr: base of the first code bank (for ASM header / linker).
    - separate_data_size: if data in different bank, its size; else None (data at end of code bank).
    - data_base: if separate data bank, its base address; else None.
    """
    code_banks = [b for b in banks if b.get("code")]
    data_banks = [b for b in banks if b.get("data")]
    if not code_banks:
        raise ValueError("At least one bank must have code: true")
    first_code = code_banks[0]
    load_addr = first_code["base"]
    size = first_code["size"]

    if not data_banks or data_banks[0] is first_code:
        return (size, load_addr, None, None, banks)

    first_data = data_banks[0]
    return (size, load_addr, first_data["size"], first_data["base"], banks)


def get_default_config_path() -> Path:
    """Path to the default memory config shipped with Tibbar."""
    return Path(__file__).resolve().parent.parent / "config" / "memory_default.yaml"
