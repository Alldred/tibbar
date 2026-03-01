# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Tests for memory config loading and resolution (code/data/access combinations)."""

import sys
import tempfile
from pathlib import Path

import pytest

from tibbar.core.memory_config import (
    DEFAULT_DATA_RESERVE,
    get_default_config_path,
    get_schema_path,
    load_memory_config,
    resolve_memory_from_config,
)


def test_load_one_bank_code_and_data():
    """One bank with code and data: no separate data region."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
memory:
  banks:
    - name: RAM
      base: 0x80000000
      size: 0x80000
      code: true
      data: true
      access: rwx
"""
        )
        path = Path(f.name)
    try:
        banks, data_reserve, boot = load_memory_config(path)
        assert len(banks) == 1
        assert data_reserve == DEFAULT_DATA_RESERVE
        assert boot is None  # omitted => random
        assert banks[0]["name"] == "RAM"
        assert banks[0]["base"] == 0x80000000
        assert banks[0]["size"] == 0x80000
        assert banks[0]["code"] is True
        assert banks[0]["data"] is True
        assert banks[0]["access"] == "rwx"

        code_size, load_addr, sep_data, data_base, _ = resolve_memory_from_config(banks)
        assert code_size == 0x80000
        assert load_addr == 0x80000000
        assert sep_data is None
        assert data_base is None
    finally:
        path.unlink(missing_ok=True)


def test_load_two_banks_code_and_data():
    """Two banks: first code-only, second data-only -> separate data region."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
memory:
  banks:
    - name: CODE
      base: 0x80000000
      size: 0x40000
      code: true
      data: false
      access: rx
    - name: DATA
      base: 0x80040000
      size: 0x40000
      data: true
      access: rw
"""
        )
        path = Path(f.name)
    try:
        banks, _, _ = load_memory_config(path)
        assert len(banks) == 2
        assert banks[0]["access"] == "rx"
        assert banks[1]["access"] == "rw"

        code_size, load_addr, sep_data, data_base, _ = resolve_memory_from_config(banks)
        assert code_size == 0x40000
        assert load_addr == 0x80000000
        assert sep_data == 0x40000
        assert data_base == 0x80040000
    finally:
        path.unlink(missing_ok=True)


def test_load_access_rx_rw_rwx():
    """Access strings rx, rw, rwx parse and are preserved."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
memory:
  banks:
    - name: CODE
      base: 0
      size: 0x10000
      code: true
      data: false
      access: rx
    - name: DATA
      base: 0x10000
      size: 0x1000
      data: true
      access: rw
    - name: RAM
      base: 0x20000
      size: 0x8000
      code: true
      data: true
      access: rwx
"""
        )
        path = Path(f.name)
    try:
        banks, _, _ = load_memory_config(path)
        assert banks[0]["access"] == "rx"
        assert banks[1]["access"] == "rw"
        assert banks[2]["access"] == "rwx"

        # Code size is the sum of all code banks.
        # Separate data uses pure data banks (data=true, code=false).
        code_size, load_addr, sep_data, data_base, _ = resolve_memory_from_config(banks)
        assert code_size == 0x10000 + 0x8000
        assert load_addr == 0
        assert sep_data == 0x1000
        assert data_base == 0x10000
    finally:
        path.unlink(missing_ok=True)


def test_multi_non_contiguous_banks_resolve_to_absolute_spaces():
    """Multiple non-contiguous code/data banks resolve with absolute bases and summed sizes."""
    banks = [
        {
            "name": "CODE0",
            "base": 0x80000000,
            "size": 0x1000,
            "code": True,
            "data": False,
            "access": "rx",
        },
        {
            "name": "DATA0",
            "base": 0x90000000,
            "size": 0x0200,
            "code": False,
            "data": True,
            "access": "rw",
        },
        {
            "name": "CODE1",
            "base": 0xA0000000,
            "size": 0x0800,
            "code": True,
            "data": False,
            "access": "rx",
        },
        {
            "name": "DATA1",
            "base": 0xB0000000,
            "size": 0x0100,
            "code": False,
            "data": True,
            "access": "rw",
        },
    ]
    code_size, load_addr, sep_data, data_base, _ = resolve_memory_from_config(banks)
    assert code_size == 0x1800
    assert load_addr == 0x80000000
    assert sep_data == 0x300
    assert data_base == 0x90000000


def test_resolve_requires_code_bank():
    """At least one bank must have code: true."""
    banks = [
        {
            "name": "DATA",
            "base": 0x80000000,
            "size": 0x80000,
            "code": False,
            "data": True,
            "access": "rw",
        },
    ]
    with pytest.raises(ValueError, match="At least one bank must have code: true"):
        resolve_memory_from_config(banks)


def test_load_requires_memory_key():
    """Config must have top-level 'memory' key (schema validation)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("banks: []")
        path = Path(f.name)
    try:
        with pytest.raises(ValueError, match="memory|schema"):
            load_memory_config(path)
    finally:
        path.unlink(missing_ok=True)


def test_load_requires_banks_list():
    """Config must have memory.banks as a non-empty list (schema validation)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("memory: {}")
        path = Path(f.name)
    try:
        with pytest.raises(ValueError, match="banks|schema"):
            load_memory_config(path)
    finally:
        path.unlink(missing_ok=True)


def test_schema_valid_user_config_passes():
    """A user-written config that conforms to the schema loads and resolves."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
memory:
  banks:
    - name: C
      base: 0x1000
      size: 0x2000
      code: true
      data: false
      access: rx
    - name: D
      base: 0x3000
      size: 0x1000
      data: true
      access: rw
  data_reserve: 65536
"""
        )
        path = Path(f.name)
    try:
        banks, data_reserve, _ = load_memory_config(path)
        assert len(banks) == 2
        assert data_reserve == 65536
        code_size, load_addr, sep_data, data_base, _ = resolve_memory_from_config(banks)
        assert load_addr == 0x1000
        assert code_size == 0x2000
        assert sep_data == 0x1000
        assert data_base == 0x3000
    finally:
        path.unlink(missing_ok=True)


def test_schema_invalid_config_fails():
    """Invalid config (wrong type, missing required) fails schema validation."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
memory:
  banks:
    - name: R
      base: not_a_number
      size: 0x1000
      code: true
"""
        )
        path = Path(f.name)
    try:
        with pytest.raises(ValueError, match="schema|Expected int|invalid literal"):
            load_memory_config(path)
    finally:
        path.unlink(missing_ok=True)


def test_data_reserve_from_config_single_bank():
    """Single bank with code+data: data_reserve from config is used."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
memory:
  banks:
    - name: RAM
      base: 0x80000000
      size: 0x80000
      code: true
      data: true
      access: rwx
  data_reserve: 131072
"""
        )
        path = Path(f.name)
    try:
        banks, data_reserve, _ = load_memory_config(path)
        assert data_reserve == 131072
        code_size, load_addr, sep_data, data_base, _ = resolve_memory_from_config(banks)
        assert sep_data is None
        assert data_base is None
    finally:
        path.unlink(missing_ok=True)


def test_default_config_path_exists_and_loads():
    """Default config file exists and has two banks (instruction + data)."""
    path = get_default_config_path()
    assert path.exists()
    banks, _, boot = load_memory_config(path)
    assert len(banks) >= 1
    assert boot == 0x80000100  # default config has absolute boot address
    code_size, load_addr, sep_data, data_base, _ = resolve_memory_from_config(banks)
    assert load_addr == 0x80000000
    # Default is two banks: separate code and data
    assert sep_data is not None
    assert data_base is not None
    assert banks[0].get("access") == "rwx"  # instruction bank
    assert banks[1].get("access") == "rw"  # data bank


def test_load_boot_from_config():
    """Optional absolute boot address is read from config; omitted => None."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
memory:
  banks:
    - name: RAM
      base: 0x80000000
      size: 0x80000
      code: true
      data: true
  boot: 0x80000000
"""
        )
        path = Path(f.name)
    try:
        _, _, boot = load_memory_config(path)
        assert boot == 0x80000000
    finally:
        path.unlink(missing_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
memory:
  banks:
    - name: RAM
      base: 0x80000000
      size: 0x80000
      code: true
      data: true
"""
        )
        path = Path(f.name)
    try:
        _, _, boot = load_memory_config(path)
        assert boot is None
    finally:
        path.unlink(missing_ok=True)


def test_schema_path_exists():
    """Schema file exists so check-memory-config and loaders can validate user configs."""
    assert get_schema_path().exists()


def test_check_memory_config_script_valid(tmp_path):
    """Script check-memory-config.py exits 0 for a valid user config."""
    config = tmp_path / "mem.yaml"
    config.write_text(
        """
memory:
  banks:
    - name: RAM
      base: 0x80000000
      size: 0x80000
      code: true
      data: true
      access: rwx
"""
    )
    import subprocess

    script = Path(__file__).resolve().parent.parent / "scripts" / "check-memory-config.py"
    result = subprocess.run(
        [sys.executable, str(script), str(config)], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "OK:" in result.stdout


def test_check_memory_config_script_invalid(tmp_path):
    """Script check-memory-config.py exits non-zero for invalid config."""
    config = tmp_path / "mem.yaml"
    config.write_text("memory: { banks: [] }\n")
    import subprocess

    script = Path(__file__).resolve().parent.parent / "scripts" / "check-memory-config.py"
    result = subprocess.run(
        [sys.executable, str(script), str(config)], capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "Invalid" in result.stderr or "schema" in result.stderr.lower()
