#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Validate a Tibbar memory config YAML against the schema and full load/resolve pipeline.
Use this when authoring a custom memory config to sanity-check before running Tibbar.
Exit 0 if valid; non-zero and message on failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root so we can import tibbar
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: check-memory-config.py <path-to-memory.yaml>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 1
    try:
        from tibbar.core.memory_config import load_memory_config, resolve_memory_from_config

        banks, data_reserve, boot = load_memory_config(path)
        code_size, load_addr, sep_data, data_base, _ = resolve_memory_from_config(banks)
        print(f"OK: {path}")
        print(f"  code bank: base=0x{load_addr:x} size=0x{code_size:x}")
        if sep_data is not None and data_base is not None:
            print(f"  data bank: base=0x{data_base:x} size=0x{sep_data:x}")
        else:
            print(f"  data reserve (same bank): {data_reserve} bytes")
        if boot is not None:
            print(f"  boot (offset): 0x{boot:x}")
        else:
            print("  boot: random")
        return 0
    except ValueError as e:
        print(f"Invalid config: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
