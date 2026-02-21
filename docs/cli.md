# CLI reference

Run Tibbar from the project root (after `uv sync` or with your environment activated):

```bash
uv run tibbar --generator <name> [options]
```

or:

```bash
uv run python -m tibbar --generator <name> [options]
```

## Required

| Option | Short | Description |
|--------|--------|--------------|
| `--generator` | `-g` | Test suite name. Required. One of: `ldst`, `rel_branching`, `simple`, `float`, `stress_float`, `hazard`, `ldst_exception`. |

If you omit `--generator`, Tibbar exits with an error and prints an example, e.g.:

```text
tibbar: error: the following arguments are required: --generator/-g
Example: tibbar --generator simple --output test.S
```

## Optional

| Option | Short | Default | Description |
|--------|--------|---------|-------------|
| `--output` | `-o` | `test.S` | Output assembly file path. |
| `--seed` | `-s` | `42` | Random seed for reproducible runs. |
| `--verbosity` | `-v` | `info` | Log level: `debug`, `info`, `warning`, `error`. |
| `--debug-yaml` | — | — | If set, write debug YAML to the given file (addresses, memory layout, metadata). |
| `--memory-config` | — | built-in | Path to memory layout YAML (banks, code/data, access, optional `data_reserve`). Default: separate instruction (rx) and data (rw) banks. For single RAM use e.g. `tibbar/config/memory_single_ram.yaml`. Validate user configs with `scripts/check-memory-config.py <path>`. |

## Examples

Generate a simple test with the default output path and seed:

```bash
uv run tibbar --generator simple
```

Write to a specific file and use a custom seed:

```bash
uv run tibbar --generator simple --output my_test.S --seed 123
```

Generate a load/store-heavy test and dump debug YAML:

```bash
uv run tibbar --generator ldst -o ldst.S --debug-yaml ldst_debug.yaml
```

Quieter output (only warnings and errors):

```bash
uv run tibbar --generator rel_branching -o branch.S --verbosity warning
```

Generate then assemble and link in one go (requires RISC-V toolchain on PATH and `scripts/asm2elf.sh`):

```bash
uv run tibbar --generator simple --output test.S && ./scripts/asm2elf.sh test.S --link -o test.elf
```

The output file has a header with `# Load address:`, `# RAM size:`, `# Boot:`, and `# Exit:`; boot and exit addresses are randomised (exit is never 0). Load address and size come from the memory config (default or `--memory-config`). The default config has two banks (instruction and data); the data bank is emitted as a separate 0-based `.data` section with a `# Data region:` comment so the linker can place it at the data bank base. Use **access** in the config (`rx` for read-only code, `rw` for data, `rwx` for unified RAM) to document permissions; Tibbar does not generate writes to code regions.
