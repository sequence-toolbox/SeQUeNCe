# Unreliable-midpoint studies

In single-heralded generation the midpoint's classical success message is what
the end node acts on. On an accepted herald the end node writes the joint
Bell-diagonal state into the quantum manager and marks the memory entangled.
This is correct for an honest midpoint. To study a midpoint whose heralds may
not match its detections, the record the protocol keeps and the state the
quantum manager holds must be separable. Two additive pieces provide that.

## The BSM registry

`BSM.register(name)` and `BSM.resolve(name)` mirror the generation-protocol
registry. The built-in encodings register their own classes, so `BSMNode`
resolves the classes it resolved before. A study registers its own BSM under a
new encoding name and selects it from a `qconnection` template.

```python
from sequence.components.bsm import BSM, SingleHeraldedBSM

@BSM.register("my_bsm")
class MyBSM(SingleHeraldedBSM):
    ...
```

## The physics-ledger hook

`SingleHeraldedA.update_memory` builds the state to write in
`SingleHeraldedA._state_on_herald`. A subclass overrides that one method to
decide, per round, what state a herald produces. With the stock protocol the
method returns the usual state and nothing changes.

The example's `LedgerSingleHeraldedA` (registered `ledger_sh`) consults a
`PhysicsLedger` on the timeline: for a round the ledger marked unbacked it
returns the maximally mixed two-memory state, all Bell-diagonal elements 1/4,
because the two memories were each entangled with their own emitted photon and
those photons were not measured jointly.

## What the example measures

`example/unreliable_midpoint/run_example.py` runs the two-node tutorial config
with the unreliable midpoint. An honest run reproduces the tutorial's 105
pairs. With a false-positive rate the midpoint delivers pairs it did not
detect. Their computed fidelity, read from the quantum manager at delivery, is
0.25; their bookkeeping fidelity stays at the template value 0.9 and passes the
request threshold, because the threshold compares the bookkeeping scalar.

Means over 8 seeds, two-node config, request threshold 0.8 and 0.9 (the two
thresholds give the same counts):

| p_false_positive | delivered | delivered with computed fidelity 0.25 |
|---|---|---|
| 0.0 | 119.5 | 0.0 |
| 0.1 | 138.6 | 23.0 |
| 0.5 | 238.6 | 123.0 |

A drop rate removes honest heralds instead: at p_drop 0.3 the two-node
delivered count falls from 119.5 to 83.2.
