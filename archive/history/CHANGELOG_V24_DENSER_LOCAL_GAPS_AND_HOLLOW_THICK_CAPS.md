# V24 — Denser local gaps, branching local cohorts, hollow thick caps, and launch spacing

V24 is built on V23 and preserves the V22/V23 hard-routing contract. The changes are local-gap and rendering refinements; main holistic routing rules are not weakened.

## 1. Verification runtime policy

Wall-clock verification timeouts scale with the number of generated samples: each geometry-heavy sample receives its own per-sample allowance, so an N-sample verification batch is budgeted approximately N times the single-sample allowance. This is a verifier/runtime policy, not a reason to multiply routing search depth by trace count.

## 2. Denser local-gap population

- Residual-space candidate grid increases from 9×9 to 12×12.
- V24 normally attempts 6–7 ordinary local bundle roots instead of V23's 3–4.
- Ordinary local roots now begin with 3–4 traces.
- Source spacing is reduced enough to use separate residual holes while the exact collision/keepout checks remain authoritative.
- Local roots receive 10–15 gesture life budgets and the local second pass uses 24 normal rounds + up to 6 persistence rounds.
- Failed local routes remain best-effort omissions; gap coverage is never a quota.

## 3. Local bundle breakup bias

V23 local children could lose their local identity after a branch. V24 propagates `local_gap`, `local_gap_special`, and the local branch profile through topology/recovery changes.

- Local-gap branch appetite receives a 1.90× multiplier.
- Local branching can begin after one local gesture.
- The local late-life threshold begins around 35% of planned life and adds another 1.35× boost.
- Mature local bundles receive strong minimum branch tendencies (about 0.90 for 3+ traces, 0.80 for 2 traces when geometry allows).
- Local normal branches first split into narrower contiguous parallel cohorts with a one-module rebase; the children then make independent normal routing decisions. This is more feasible inside constrained gaps than insisting on a wide immediate decorative fan.

All branch births remain transactional and collision checked.

## 4. Special thick local traces

- V23's 5–10% special probability is tripled to a seeded soft target of 15–30%.
- Special roots remain singleton-only.
- Thickness remains 5–8× a freshly sampled ordinary line width.
- They no longer receive separate source/termination-dot primitives.
- Their actual polyline uses round caps. A background-coloured negative circle is placed inside the visible source cap, and inside a free terminal cap when the trace terminates. Connected/component ends remain solid so the connection is not visually broken.

## 5. Main-chip emission gap

The visible source point of each main-chip trace is moved three times farther from the chip than V23:

- V23: 7.5U
- V24: 22.5U

This affects the chip-to-emitting-line gap only; the existing 24U foreign/main-chip routing keepout remains unchanged.

## 6. Capacitors

V23's capacitor tuning remains active unchanged:

- collection capacitor weight = 3.90 (3× the pre-V23 value);
- isolated capacitor occurrence saturates at 1.00;
- continuous radius range = 4.2U–12.9U (+50% size span).
