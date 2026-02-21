# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""CLI entry point for Tibbar."""

import importlib
import sys
from pathlib import Path

from tibbar.core.tibbar import Tibbar

# Named test suites (tibbar.test_suites.<name>.Generator)
TEST_SUITE_NAMES = (
    "ldst",
    "rel_branching",
    "simple",
    "float",
    "stress_float",
    "hazard",
    "ldst_exception",
)


def get_generator_from_suite(name: str):
    """Load Generator class from tibbar.test_suites.<name>."""
    mod = importlib.import_module(f"tibbar.test_suites.{name}")
    return mod.Generator


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Tibbar - RISC-V Instruction Stream Generator")
    parser.add_argument("--output", "-o", type=Path, default=Path("test.S"))
    parser.add_argument("--seed", "-s", type=int, default=42)
    parser.add_argument(
        "--verbosity",
        "-v",
        default="info",
        choices=["debug", "info", "warning", "error"],
    )
    parser.add_argument(
        "--generator",
        "-g",
        type=str,
        default=None,
        choices=TEST_SUITE_NAMES,
        help="Named test suite (required). e.g. simple, ldst, rel_branching.",
    )
    parser.add_argument(
        "--debug-yaml",
        type=Path,
        default=None,
        metavar="FILE",
        help="Optional: write debug YAML to FILE",
    )
    parser.add_argument(
        "--memory-config",
        type=Path,
        default=None,
        metavar="FILE",
        help="Memory layout YAML (banks, code/data, base, size). Default: built-in config.",
    )
    args = parser.parse_args()

    if args.generator is None:
        parser.print_usage(sys.stderr)
        print(
            "tibbar: error: the following arguments are required: --generator/-g\n"
            "Example: tibbar --generator simple --output test.S",
            file=sys.stderr,
        )
        sys.exit(2)

    def make_generator(tibbar: object):
        gen_cls = get_generator_from_suite(args.generator)
        return gen_cls(tibbar=tibbar)

    tibbar = Tibbar(
        generator=None,
        generator_factory=make_generator,
        seed=args.seed,
        output=args.output,
        verbosity=args.verbosity,
        memory_config=args.memory_config,
    )
    tibbar.run()
    if args.debug_yaml is not None:
        tibbar.write_debug_yaml(args.debug_yaml)
        tibbar.info(f"Wrote debug YAML to {args.debug_yaml}")
    tibbar.info(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
