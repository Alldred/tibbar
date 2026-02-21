# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Tests for Tibbar ISG."""

import tempfile
from pathlib import Path

import pytest

from tibbar.core.generator_base import GeneratorBase
from tibbar.core.tibbar import Tibbar


def test_tibbar_runs_and_produces_asm():
    """Tibbar creates a test and writes .asm output."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.S"
        tibbar = Tibbar(
            generator_factory=lambda t: GeneratorBase(t, length=3),
            seed=12345,
            output=out,
            verbosity="warning",
        )
        tibbar.run()
        assert out.exists()
        content = out.read_text()
        assert "# Boot:" in content
        assert "# Exit:" in content
        assert "# Load address:" in content
        assert "# RAM size:" in content
        assert "addi" in content or "lui" in content or "add" in content


def test_tibbar_default_memory_config():
    """Default config has separate instruction (rx) and data (rw) banks."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.S"
        tibbar = Tibbar(
            generator_factory=lambda t: GeneratorBase(t, length=2),
            seed=1,
            output=out,
            verbosity="error",
        )
        tibbar.run()
        assert tibbar.load_addr == 0x80000000
        assert tibbar.ram_size == 0x40000
        assert tibbar._data_region_base == 0x80040000
        assert tibbar.boot_address == 0x100  # default config has boot: 0x100
        content = out.read_text()
        assert "# Data region:" in content


def test_tibbar_single_bank_config():
    """Single-bank (code+data) config: no separate data region line, data at end of same region."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.S"
        config = Path(tmp) / "mem.yaml"
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
        tibbar = Tibbar(
            generator_factory=lambda t: GeneratorBase(t, length=2),
            seed=1,
            output=out,
            verbosity="error",
            memory_config=config,
        )
        tibbar.run()
        assert tibbar._data_region_base is None
        content = out.read_text()
        assert "# Data region:" not in content
        assert tibbar.load_addr == 0x80000000
        assert tibbar.ram_size == 0x80000


def test_tibbar_single_bank_uses_config_data_reserve():
    """Single-bank config with data_reserve in YAML: Tibbar uses it for data region size."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.S"
        config = Path(tmp) / "mem.yaml"
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
  data_reserve: 131072
"""
        )
        tibbar = Tibbar(
            generator_factory=lambda t: GeneratorBase(t, length=2),
            seed=1,
            output=out,
            verbosity="error",
            memory_config=config,
        )
        tibbar.run()
        assert tibbar.mem_store.get_data_region_size() == 131072


def test_tibbar_memory_config():
    """Tibbar uses memory config and emits load address and RAM size from it."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.S"
        config = Path(tmp) / "mem.yaml"
        config.write_text(
            """
memory:
  banks:
    - name: RAM
      base: 0x90000000
      size: 0x80000
      code: true
      data: true
      access: rwx
"""
        )
        tibbar = Tibbar(
            generator_factory=lambda t: GeneratorBase(t, length=2),
            seed=1,
            output=out,
            verbosity="error",
            memory_config=config,
        )
        tibbar.run()
        content = out.read_text()
        assert "0x90000000" in content
        assert "0x80000" in content
        assert tibbar.ram_size == 0x80000
        assert tibbar.load_addr == 0x90000000


def test_tibbar_two_banks_emits_data_region_comment():
    """With separate code and data banks, ASM contains Data region comment."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.S"
        config = Path(tmp) / "mem.yaml"
        config.write_text(
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
        tibbar = Tibbar(
            generator_factory=lambda t: GeneratorBase(t, length=2),
            seed=1,
            output=out,
            verbosity="error",
            memory_config=config,
        )
        tibbar.run()
        assert "# Data region: 0x80040000" in out.read_text()


def test_tibbar_config_boot_fixed():
    """Config with boot set uses that offset as boot address (not randomised)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.S"
        config = Path(tmp) / "mem.yaml"
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
  boot: 0x200
"""
        )
        tibbar = Tibbar(
            generator_factory=lambda t: GeneratorBase(t, length=2),
            seed=1,
            output=out,
            verbosity="error",
            memory_config=config,
        )
        tibbar.run()
        assert tibbar.boot_address == 0x200
        assert "# Boot: 0x200" in out.read_text()


def test_tibbar_boot_at_zero():
    """Boot can be at 0; exit remains non-zero."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.S"
        config = Path(tmp) / "mem.yaml"
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
  boot: 0
"""
        )
        tibbar = Tibbar(
            generator_factory=lambda t: GeneratorBase(t, length=3),
            seed=1,
            output=out,
            verbosity="error",
            memory_config=config,
        )
        tibbar.run()
        assert tibbar.boot_address == 0
        assert tibbar.exit_address != 0
        content = out.read_text()
        assert "# Boot: 0x0" in content
        assert "# Exit:" in content


def test_tibbar_readonly_code_bank_runs():
    """Tibbar runs with instruction bank access: rx (read-only; no self-modifying writes)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.S"
        config = Path(tmp) / "mem.yaml"
        config.write_text(
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
        tibbar = Tibbar(
            generator_factory=lambda t: GeneratorBase(t, length=3),
            seed=2,
            output=out,
            verbosity="error",
            memory_config=config,
        )
        tibbar.run()
        content = out.read_text()
        assert "# Load address:" in content
        assert tibbar.ram_size == 0x40000
        assert tibbar._data_region_base == 0x80040000


def test_tibbar_debug_yaml():
    """Tibbar can write debug YAML."""
    with tempfile.TemporaryDirectory() as tmp:
        asm_out = Path(tmp) / "test.S"
        yaml_out = Path(tmp) / "debug.yaml"
        tibbar = Tibbar(
            generator_factory=lambda t: GeneratorBase(t, length=2),
            seed=999,
            output=asm_out,
            verbosity="error",
        )
        tibbar.run()
        tibbar.write_debug_yaml(yaml_out)
        assert yaml_out.exists()
        content = yaml_out.read_text()
        assert "boot_address" in content
        assert "memory" in content


def test_cli_smoke(tmp_path):
    """CLI runs without error when --generator is provided."""
    import sys

    from tibbar.__main__ import main

    old_argv = sys.argv
    try:
        sys.argv = [
            "tibbar",
            "--generator",
            "simple",
            "--output",
            str(tmp_path / "out.S"),
        ]
        main()
        assert (tmp_path / "out.S").exists()
    finally:
        sys.argv = old_argv


def test_cli_requires_generator():
    """CLI exits with error and shows example when --generator is omitted."""
    import io
    import sys

    from tibbar.__main__ import main

    old_argv = sys.argv
    old_stderr = sys.stderr
    try:
        sys.argv = ["tibbar", "--output", "test.S"]
        sys.stderr = io.StringIO()
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2
        err = sys.stderr.getvalue()
        assert "required" in err and "--generator" in err
        assert "simple" in err and "test.S" in err
    finally:
        sys.argv = old_argv
        sys.stderr = old_stderr
