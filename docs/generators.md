# Generators

A **generator** is a test suite: it defines which **sequences** run and in what order (via a funnel). When you run Tibbar, you pick one generator with `--generator` / `-g`. Each run randomises the **boot** and **exit** addresses (exit is never 0); the output file header lists them as `# Boot:` and `# Exit:`.

## Built-in generators

| Name              | Purpose |
|-------------------|---------|
| `simple`          | Random safe integer instructions and relative branching. Good default for a simple test. |
| `ldst`            | Load/store-heavy: many Load and Store sequences in sequence. |
| `rel_branching`   | Lots of relative branching with short bursts of random safe instructions. |
| `float`           | Float-oriented: RandomFloatInstrs (F-extension) and relative branching. |
| `stress_float`    | Stress float: safe integer and float stress sequences. |
| `hazard`          | Hazard-focused: SetGPRs, Hazards (GPR data-hazard pairs), Load/Store, RandomSafeInstrs. |
| `ldst_exception`  | Load/store with faults: LoadException (load from x0 to trigger fault) + Store + branching. |

## Choosing a generator

- For a **simple, general test**: use `simple`.
- For **memory stress**: use `ldst` or `ldst_exception`.
- For **branch stress**: use `rel_branching`.
- For **float and F-extension stress**: use `float` (random float instructions + branching) or `stress_float`.
- For **data hazards and GPR setup**: use `hazard` (SetGPRs, Hazards, loads/stores).
- For **load/store faults**: use `ldst_exception` (faulting loads + stores + branching).

## Example

```bash
uv run tibbar --generator simple --output test.S
uv run tibbar --generator ldst --output ldst.S --seed 1
```

See [Sequences and funnels](sequences.md) for how generators compose sequences into a test.
