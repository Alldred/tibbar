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
