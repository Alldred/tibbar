# Tibbar documentation

Tibbar is a RISC-V instruction stream generator. It produces assembly test programs (`.S` files) that you can assemble and run on a simulator or hardware to stress-test execution, memory, or control flow.

## What Tibbar generates

- **Boot address** — Where execution starts. Chosen at random; printed as `# Boot: 0x...` in the output.
- **Exit region** — A small block of code the test eventually jumps to; the test is “done” when the PC reaches this region. The **exit address is randomised** (and never 0, which is often reserved for reset/trap). Printed as `# Exit: 0x...`. A testbench can detect completion by that PC or by a branch-to-self (infinite loop) at the exit address.
- **Instructions** — A stream of RISC-V instructions (and optional data) placed in memory. The generator fills memory until the model’s PC reaches the exit region and executes the exit loop. Traps (exceptions) are handled by relocating to a handler and continuing.

Output is a single assembly file (default `test.S`) with one instruction per line and comments. You can also dump internal state with `--debug-yaml` for debugging.

## Memory layout

Tibbar gets memory layout from a **config file** (YAML). The **default config** uses two banks: an **instruction bank** (`access: rx`) at `0x80000000` size `0x40000`, and a **data bank** (`access: rw`) at `0x80040000` size `0x40000`. Read-only code (`rx`) means Tibbar generates instructions there but self-modifying code must not write to that region. Use **`--memory-config <path>`** to point to a different file. For a **single-RAM** setup (e.g. matching `scripts/riscv_bare.ld`), use a one-bank config such as the bundled `tibbar/config/memory_single_ram.yaml`.

Each bank has `name`, `base`, `size`, and flags `code` / `data` / `access`. The first bank with `code: true` is the instruction region (its base and size appear in the ASM header). If a different bank has `data: true`, that bank is used for load/store data (emitted as a separate `.data` section for the linker to place at the data bank base). When code and data share one bank, **`data_reserve`** (under `memory`) sets how many bytes to reserve at the end for data (default 262144). Optional **`boot`** is a 0-based offset into the code region where execution starts; if omitted, the boot address is randomised (and kept outside the exit region). Use `boot: 0` to match a typical `_start` at the image base. Configs are validated against a **JSON Schema** on load. To sanity-check a custom config, use **`scripts/check-memory-config.py <path>`**. See [CLI reference](cli.md).

## How to run Tibbar

You **must** choose a **generator** (test suite). There is no default.

```bash
uv run tibbar --generator simple --output test.S
```

If you omit `--generator`, Tibbar prints an error and an example command. See [CLI reference](cli.md) for all options.

## Building an ELF

To assemble and link the generated `.S` file for a RISC-V simulator or core, use the project script (see the main [README](../README.md) for toolchain install):

```bash
./scripts/asm2elf.sh test.S --link -o test.elf
```

The script uses the linker script `scripts/riscv_bare.ld` when linking. Full workflow:

```bash
uv run tibbar --generator simple --output test.S && ./scripts/asm2elf.sh test.S --link -o test.elf
```

## Documentation index

- **[Generators](generators.md)** — What a generator is and the built-in suites (`simple`, `ldst`, `rel_branching`, etc.).
- **[Sequences and funnels](sequences.md)** — How a test is built from program start, a main funnel of sequences, program end, and relocate logic.
- **[CLI reference](cli.md)** — All command-line options and examples.
