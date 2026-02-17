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
        assert "addi" in content or "lui" in content or "add" in content


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
