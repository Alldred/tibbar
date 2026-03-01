# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Tests for Tibbar ISG."""

import tempfile
from pathlib import Path

import pytest

from tibbar.core.generator_base import GeneratorBase
from tibbar.core.tibbar import Tibbar
from tibbar.testobj import GenData


class _NoRelocate:
    def gen(self):
        if False:
            yield None


class _EscapingJalrGenerator:
    """Small deterministic stream that performs jalr to absolute low memory."""

    def __init__(self, tibbar: Tibbar) -> None:
        self.tibbar = tibbar
        self.relocate_sequence = _NoRelocate()

    def gen(self):
        # addiw x1, x0, 0x3a0
        yield GenData(data=0x3A00009B, seq="Unit", comment="addiw x1, x0, 928")
        # jalr x0, 0(x1)  -> jumps to 0x3a0 absolute (outside high code bank)
        yield GenData(data=0x00008067, seq="Unit", comment="jalr x0, 0(x1)")


def test_tibbar_runs_and_produces_asm():
    """Tibbar creates a test and writes .asm output."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.S"
        ld = Path(tmp) / "test.ld"
        tibbar = Tibbar(
            generator_factory=lambda t: GeneratorBase(t, length=3),
            seed=12345,
            output=out,
            verbosity="warning",
        )
        tibbar.run()
        assert out.exists()
        assert ld.exists()
        content = out.read_text()
        assert "# Boot:" in content
        assert "# Exit:" in content
        assert "# Load address:" in content
        assert "# RAM size:" in content
        assert "addi" in content or "lui" in content or "add" in content
        ld_content = ld.read_text()
        assert "ENTRY(_start)" in ld_content
        assert "CODE0" in ld_content
        assert "DATA0" in ld_content
        assert "CODE0 (rwx)" in ld_content
        assert "DATA0 (rw)" in ld_content


def test_tibbar_default_memory_config():
    """Default config has separate instruction (rwx) and data (rw) banks."""
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
        assert tibbar.boot_address == 0x80000100  # default config has absolute boot address
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


def test_tibbar_multi_non_contiguous_banks_mapping():
    """Multiple code/data banks use absolute addressing consistently."""
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "mem.yaml"
        config.write_text(
            """
memory:
  banks:
    - name: CODE0
      base: 0x80000000
      size: 0x200
      code: true
      data: false
      access: rx
    - name: DATA0
      base: 0x81000000
      size: 0x100
      data: true
      code: false
      access: rw
    - name: CODE1
      base: 0x90000000
      size: 0x300
      code: true
      data: false
      access: rx
    - name: DATA1
      base: 0x91000000
      size: 0x180
      data: true
      code: false
      access: rw
"""
        )
        tibbar = Tibbar(
            generator_factory=lambda t: GeneratorBase(t, length=1),
            seed=1,
            output=Path(tmp) / "test.S",
            verbosity="error",
            memory_config=config,
        )
        assert tibbar.ram_size == 0x500
        assert tibbar._addr.require_code_addr(0x80000010) == 0x80000010
        assert tibbar._addr.require_code_addr(0x90000010) == 0x90000010
        data_internal = tibbar.mem_store.get_data_region_base()
        assert data_internal is not None
        assert data_internal == 0x81000000
        assert tibbar._addr.require_store_addr(data_internal + 0x10) == 0x81000010
        assert tibbar._addr.require_store_addr(0x91000010) == 0x91000010


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
    """Config with boot set uses that absolute address (not randomised)."""
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
  boot: 0x80000200
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
        assert tibbar.boot_address == 0x80000200
        assert "# Boot: 0x80000200" in out.read_text()


def test_tibbar_boot_at_zero():
    """Boot can be at code-base address; exit remains non-zero."""
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
  boot: 0x80000000
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
        assert tibbar.boot_address == 0x80000000
        assert tibbar.exit_address != 0
        content = out.read_text()
        assert "# Boot: 0x80000000" in content
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
    import yaml

    with tempfile.TemporaryDirectory() as tmp:
        asm_out = Path(tmp) / "test.S"
        yaml_out = Path(tmp) / "debug.yaml"
        tibbar = Tibbar(
            generator_factory=lambda t: GeneratorBase(t, length=2),
            seed=999,
            output=asm_out,
            verbosity="error",
            record_execution_trace=True,
        )
        tibbar.run()
        tibbar.write_debug_yaml(yaml_out)
        assert yaml_out.exists()
        content = yaml_out.read_text()
        assert "boot_address" in content
        assert "memory" in content
        doc = yaml.safe_load(content)
        assert "executed_instructions" in doc
        assert isinstance(doc["executed_instructions"], list)
        assert len(doc["executed_instructions"]) > 0
        first = doc["executed_instructions"][0]
        assert "pc" in first
        assert "abs_pc" in first
        assert "instr" in first
        assert "next_pc" in first


def test_tibbar_errors_when_control_flow_escapes_code_bank():
    """Tibbar raises when modelled control flow leaves configured code bank(s)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.S"
        config = Path(tmp) / "mem.yaml"
        config.write_text(
            """
memory:
  banks:
    - name: CODE
      base: 0x80000000
      size: 0x80000
      code: true
      data: true
      access: rwx
"""
        )
        tibbar = Tibbar(
            generator_factory=lambda t: _EscapingJalrGenerator(t),
            seed=0,
            output=out,
            verbosity="error",
            memory_config=config,
        )
        with pytest.raises(RuntimeError, match="escaped configured code banks"):
            tibbar.run()


def test_cli_smoke(tmp_path):
    """CLI runs without error when --generator is provided."""
    import sys

    from tibbar.__main__ import main

    # Use a memory config without fixed boot so generation completes reliably
    # (fixed boot 0x100 can cause trap handler at 0xfc to spin).
    mem_config = tmp_path / "mem.yaml"
    mem_config.write_text(
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
    old_argv = sys.argv
    try:
        sys.argv = [
            "tibbar",
            "--generator",
            "simple",
            "--output",
            str(tmp_path / "out.S"),
            "--seed",
            "1",
            "--memory-config",
            str(mem_config),
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
