# Tibbar documentation

Tibbar is a RISC-V instruction stream generator. It produces assembly test programs (`.S` files) that you can assemble and run on a simulator or hardware to stress-test execution, memory, or control flow.

## What Tibbar generates

- **Boot address** — Where execution starts (printed as `# Boot: 0x...` in the output).
- **Exit region** — A small block of code the test eventually jumps to; the test is “done” when the PC reaches this region (see `# Exit: 0x...` in the output).
- **Instructions** — A stream of RISC-V instructions (and optional data) placed in memory. The generator fills memory until the model’s PC reaches the exit region. Traps (exceptions) are handled by relocating to a handler and continuing.

Output is a single assembly file (default `test.S`) with one instruction per line and comments. You can also dump internal state with `--debug-yaml` for debugging.

## How to run Tibbar

You **must** choose a **generator** (test suite). There is no default.

```bash
uv run tibbar --generator simple --output test.S
```

If you omit `--generator`, Tibbar prints an error and an example command. See [CLI reference](cli.md) for all options.

## Documentation index

- **[Generators](generators.md)** — What a generator is and the built-in suites (`simple`, `ldst`, `rel_branching`, etc.).
- **[Sequences and funnels](sequences.md)** — How a test is built from program start, a main funnel of sequences, program end, and relocate logic.
- **[CLI reference](cli.md)** — All command-line options and examples.
