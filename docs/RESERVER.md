# Resource Reserver

The Reserver enables **interleaving sequences** safely by coordinating which resources (registers, etc.) each sequence may use. Without it, round-robin interleaved sequences could write to the same registers and produce undefined behaviour.

## When to Use It

- **Interleaving sequences** with `RoundRobinFunnel` — sequences that yield in round-robin must not conflict on write resources.
- **Test generation** — e.g. one sequence reserves GPR x5–x7 exclusively; another reserves FPR f0–f2; they can interleave without corrupting each other's state.

## Key Concepts

### Reservation Kinds

| Kind          | Meaning                                                                 |
| ------------- | ----------------------------------------------------------------------- |
| **EXCLUSIVE** | Only this sequence can write. No other sequence may use it.             |
| **SHARED**    | This sequence may write, but others may too (overlapping writes allowed).|

### Three Pools

| Pool           | Meaning                                                      |
| -------------- | ------------------------------------------------------------ |
| **UNASSIGNED** | Free; not allocated to any sequence.                         |
| **EXCLUSIVE**  | Held by one sequence; only that sequence may use it.         |
| **SHARED**     | Available for shared use; multiple sequences can use them.  |

**Rules:** EXCLUSIVE draws only from UNASSIGNED. SHARED draws from resources not in EXCLUSIVE. All-or-nothing: a `request()` either succeeds fully or returns `None`.

### Sequences Know What They Reserved

The funnel sets **`reservation_claim`** on the sequence before calling `gen()`. The claim is an `AllocatedClaim` with `.exclusive` and `.shared` (frozensets of `ResourceId`). Use it inside `gen()` to see which registers you got (e.g. when you asked for `ResourceSlot("FPR", count=2)`).

## Resource Identity

- **ResourceId(namespace, identifier)** — concrete resource, e.g. `ResourceId("GPR", 5)` (x5), `ResourceId("CSR", "mstatus")`.
- **ResourceSlot(namespace, count=1)** — “any N from this namespace”; the Reserver picks which ones.

## How to Use It

### 1. Create a ResourceSpace from Eumos

Eumos provides reservable resources via `reservable_resources()` (dict of namespace → list of ids). Tibbar wraps it with `DictResourceSpace`:

```python
from eumos import Eumos
from tibbar.core.resource import DictResourceSpace, Reserver

eumos = Eumos()
resource_space = DictResourceSpace(eumos.reservable_resources())
reserver = Reserver(resource_space)
```

### 2. Use RoundRobinFunnel with the Reserver

Pass the reserver into the funnel. Only **sequences** (not nested funnels) get reserve/release when the funnel starts them.

```python
from tibbar.core.funnels import RoundRobinFunnel

funnel = RoundRobinFunnel(tibbar, reserver=reserver)
funnel.add_sequence(MySequence(tibbar)).add_sequence(OtherSequence(tibbar))
for item in funnel.gen():
    ...
```

Without a reserver, `RoundRobinFunnel(tibbar, reserver=None)` still does true round-robin (one item per producer per round) but does not reserve.

### 3. Sequence Base and Declaring Requests

Use **SequenceBase** for the default `get_resource_requests()` and the `reservation_claim` attribute. Constraint-based sequences use **BaseConstraint**, which subclasses SequenceBase, so they get the stub too.

Override `get_resource_requests()` to declare what you need:

```python
from tibbar.sequences.base import SequenceBase
from tibbar.core.resource import ReservationKind, ResourceId, ResourceSlot

class MySequence(SequenceBase):
    def get_resource_requests(self):
        return {
            ReservationKind.EXCLUSIVE: [
                ResourceId("GPR", 5),
                ResourceSlot("FPR", count=1),
            ],
        }

    def gen(self):
        # Use self.reservation_claim.exclusive / .shared to see allocated regs
        ...
```

The funnel reserves on first yield and releases when the sequence is exhausted; no decorator needed. The funnel sets `seq.reservation_claim = claim` before calling `seq.gen()`.

### 4. Nested Funnels

Funnels can contain other funnels. Reservation happens only when a funnel starts iterating a **sequence** (a direct child with `.gen()`). When the producer is another funnel, no reservation at that level — the inner funnel reserves when it starts its own sequences.

## RISC-V Namespaces

From eumos: **GPR** (x1..x31 only; x0 is the zero register and is excluded), **FPR** (f0..f31), **CSR** (writable CSRs only; read-only CSRs with access "RO" are excluded). The dict from `eumos.reservable_resources()` reflects this.

## Errors

- **ReservationError** — raised when the request is invalid, e.g. **ResourceId("GPR", 0)** (x0 is the zero register and cannot be reserved). The funnel catches it and skips that producer. Callers that call `reserver.request()` directly get a clear message (e.g. "GPR 0 (x0) is the zero register and cannot be reserved.").
- **request() returns None** — the full request could not be satisfied (e.g. resources already held); funnel skips that producer or drains another then retries.
