# V23 — Local-gap pathways, source markers, and capacitor tuning

V23 is built on the frozen V22 bounded-local-holistic router. It does **not** replace or relax the V22 hard routing invariants.

## 1. Source markers

- Every visible pathway trace now has a filled or hollow circular marker at its source/emergence point.
- Source markers use the same marker radius/stroke language as terminal markers.
- Hollow source markers clip the trace at the marker's **outer stroke boundary**, so the line is never visible passing through the hollow center.
- The marker draw choice uses a dedicated deterministic per-trace RNG and therefore does not perturb route decisions.

## 2. Capacitor occurrence

- Collection-family sampling weight for `capacitor_circle` increases from **1.30 → 3.90** (exactly 3×).
- The independent isolated-capacitor occurrence path was already 0.72; multiplying by 3 saturates at probability **1.00**.
- The existing independent isolated count rule remains 1–3 and is still continuously derived rather than selected from a count menu.

## 3. Capacitor size variance

- Continuous radius formula changes from:
  - `(4.2 + 5.8 * R^0.90)U`
  - to `(4.2 + 8.7 * R^0.90)U`
- The additive size span is therefore **50% wider**.
- Resulting continuous radius range is **4.2U–12.9U**.

## 4. Sparse local-gap pathway phase

Main-chip pathways route first. Only after that network is frozen does V23 search residual free space for local pathway sources.

- Candidate sources come from a small jittered residual-space grid.
- Candidate scoring prefers high static/path clearance and low local congestion.
- The phase intentionally samples only a few useful gaps; it does **not** try to fill every empty region.
- A failed local source/path is simply omitted. Local-gap realization is a soft best-effort outcome, never a board-acceptance quota.
- Ordinary local roots contain **2–5 traces**.
- Local roots use the same V22 direction grammar, branch logic, connection logic, collision rules, keepouts, anti-loop checks, traceback/reroute, endpoint handling, and thick-stroke audits.
- Because these routes are explicitly local accents, their second-pass horizon is bounded to **20 normal rounds + up to 6 persistence rounds** rather than another full board-spanning horizon.

## 5. Extra-thick local singleton traces

- The target share is **5–10% of the planned local trace population**.
- Special traces always spawn as **single-member roots**, never as bundles.
- Their width is sampled as **5–8× a freshly sampled ordinary trace width**.
- They retain the same collision/keepout/connection/termination grammar as other local traces.

## 6. Hard-rule preservation

V23 keeps the V22 hard-vs-soft contract:

Hard invariants remain hard, including no static intersection, no unmarked thick-stroke contact, no doubled/collapsed traces, no compensating zigzags, no mid-line connection, no multiply-connected trace, no visible tiny involuntary death, and no overlapping terminal markers.

The local-gap system is never allowed to violate those rules merely to realize more filler.
