# Tibbar

Python-based RISC-V instruction stream generator. Tibbar produces assembly test programs (`.S` files) with a boot address, exit region, and instruction sequences suitable for simulation or verification.

You must choose a **generator** (test suite) when running Tibbar. See [docs/](docs/) for how generators, sequences, and output work.

---

## Quick start

From the project root (with [uv](https://docs.astral.sh/uv/) or your environment with dependencies installed):

```bash
uv sync
uv run tibbar --generator simple --output test.S
```

Or run as a module:

```bash
uv run python -m tibbar --generator simple --output test.S
```

This writes `test.S` with RISC-V assembly. **Boot** and **exit** addresses are randomised (exit is never 0). The file header has `# Load address:`, `# RAM size:`, `# Boot:`, and `# Exit:`; a testbench can detect completion by that PC or by a branch-to-self at the exit address. Memory layout comes from a **config file**: the default uses separate instruction (rx) and data (rw) banks; for a single-RAM linker script use `--memory-config` with a one-bank YAML (see [Memory layout](docs/README.md#memory-layout)).

---

## Generators

You must pass `--generator` / `-g` with one of these built-in suite names:

| Generator        | Description                                              |
|------------------|----------------------------------------------------------|
| `simple`         | Random safe integer instructions and relative branching  |
| `ldst`           | Load/store-heavy sequences                               |
| `rel_branching`  | Short instruction bursts and branches                    |
| `float`          | Float-oriented: RandomFloatInstrs + relative branching     |
| `stress_float`   | Stress float: safe integer sequences (float stress in funnel) |
| `hazard`         | Hazard-focused: SetGPRs, Hazards, Load/Store, RandomSafeInstrs |
| `ldst_exception` | Load/store with faults: LoadException + Store + branching |

Example with a different generator and options:

```bash
uv run tibbar --generator ldst --output ldst.S --seed 1 --debug-yaml ldst_debug.yaml
```

---

## RISC-V toolchain and building ELF

To assemble Tibbar’s `.S` output (or any RISC-V assembly) to ELF for a RISC-V core:

1. **Install the RISC-V GNU toolchain** (one-time):

   ```bash
   ./bin/install-riscv-toolchain
   ```

   On macOS this uses Homebrew (`riscv-gnu-toolchain`); on Linux it uses the distro package where available. For a fully configured environment, use the project shell so the toolchain is on PATH:

   ```bash
   ./bin/shell
   ```

2. **Build ELF from assembly**:

   ```bash
   # Object file (default)
   ./scripts/asm2elf.sh test.S
   # -> test.o

   # Explicit output path
   ./scripts/asm2elf.sh test.S -o build/test.o

   # Linked executable ELF (entry _start, for simulators/cores)
   ./scripts/asm2elf.sh test.S --link -o test.elf

   # Different architecture
   ./scripts/asm2elf.sh test.S --march=rv32imac
   ```

   The script uses `RISCV_PREFIX` (default `riscv64-unknown-elf-`) and the linker script `scripts/riscv_bare.ld` when linking. The toolchain must be on PATH (e.g. after `./bin/shell`).

   **Typical full run:** generate, then assemble and link:

   ```bash
   uv run tibbar --generator simple --output test.S && ./scripts/asm2elf.sh test.S --link -o test.elf
   ```

---

## Documentation

- **[docs/](docs/)** — How Tibbar works: overview, generators, sequences, and full CLI reference.

---

## Credits

Tibbar was originally developed at Vypercore as 'Honister'. When the company closed, Ed Nutting generously released redacted parts of the original code for open-source use. I'm very grateful for this contribution, which made the Tibbar project possible.
