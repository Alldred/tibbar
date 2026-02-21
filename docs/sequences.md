# Sequences and funnels

A Tibbar test is built from **sequences** combined by a **funnel**. The generator you choose defines which sequences run and in what order.

## High-level flow

1. **Program start** — Setup: choose random **boot** and **exit** addresses (exit is never 0), allocate the exit region, set trap handler. Emits the first instructions the model will execute.
2. **Main funnel** — A list of **sequences** (e.g. “random safe instructions”, “loads”, “stores”, “relative branches”). The funnel runs each sequence in turn; when one finishes, the next runs. The exact behaviour depends on the funnel type (e.g. `SimpleFunnel` runs them one after another).
3. **Program end** — When the model’s PC reaches the exit address, the engine places the **end sequence** there (e.g. load exit address into a GPR, `jalr` to it, then an infinite loop). The testbench can detect completion by the known exit PC or by branch-to-self at that address.
4. **Relocate** — When the generator runs out of free space at the current PC, it uses a **relocate** sequence to emit code that moves execution to another region so generation can continue.

The engine keeps asking the generator for the next instruction (or data) and places it at the current PC. It also runs a simple model of the machine: when the PC reaches already-placed code, it executes it and updates the PC (and handles traps). Generation stops when the PC reaches the exit region and executes the exit loop (branch-to-self). Every branch/jal target must have an instruction; otherwise the generator raises an error.

## Sequences

A **sequence** is something that yields **GenData**: instructions or data to be placed in memory. Examples:

- **RandomSafeInstrs** — Random I-extension instructions that avoid loads, stores, branches, and CSRs.
- **RandomFloatInstrs** — Random F-extension (float) instructions.
- **Load** / **Store** — Memory load and store instructions (data for loads comes from the data region).
- **LoadException** — A load with base register x0 so the access faults (for exception testing).
- **Hazards** — Two instructions that share a GPR (data hazard: first writes, second reads).
- **SetGPRs** — Set GPRs 1–31 to random, null, or sentinel values via LoadGPR.
- **SetFPRs** — Set FPRs 0–31 with float values from a data region (FloatGen + FLD).
- **RelativeBranching** — Relative branches (e.g. conditional branches, jumps).
- **AbsoluteBranching** — JALR (or similar) to a suitable code address.
- **DefaultProgramStart** / **DefaultProgramEnd** — Emit the program prologue and exit block.
- **DefaultRelocate** — Emit code to relocate execution when space runs out.
- **StressSingleFPRSourceFloatInstrs** / **StressMultiFPRSourceFloatInstrs** — Stress float instructions with systematic or random float inputs (FloatGen + FLD from data region).
- **FloatDivSqrt** — FPRs set via SetFPRs, then fdiv.s/d and fsqrt.s/d over source combinations.

**Data placement:** Sequences that add loadable data (e.g. SetFPRs, Load/Store with `ldst_data`, stress float sequences) use the **data region** (`allocate_data_region`). The generated `.asm` emits code in `.section .text` and data in `.section .data` so instruction and data are not mixed. See `tibbar.core.memory_store` and `write_asm` in `tibbar.core.tibbar`.

Each built-in generator wires these (and possibly others) into a **start_sequence**, a **main_funnel** (with multiple sequences added), an **end_sequence**, and a **relocate_sequence**.

## Funnels

A **funnel** combines several sequences into one stream:

- **SimpleFunnel** — Runs the first sequence to completion, then the second, then the third, and so on.
- **RoundRobinFunnel** — Round-robins between sequences (one item per producer per round) until they are all exhausted. Optional **resource reservation** lets sequences declare which registers they use so interleaving is safe; see [RESERVER.md](RESERVER.md).

The base generator used internally (e.g. `GeneratorBase` in `tibbar.core.generator_base`) uses a `SimpleFunnel` for the main body; the named test suites (e.g. `simple`, `ldst`) subclass it and add different sequences to that funnel. See the `tibbar.test_suites` and `tibbar.sequences` packages for the actual definitions.
