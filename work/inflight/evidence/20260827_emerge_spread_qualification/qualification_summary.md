# 2026-08-27 emerge/spread + MAIN connection qualification

Status: PASS / promoted candidate pending documentation bookkeeping at time of evidence capture.

## Trigger

User supplied `pcb_render_error_20260827_110209_586.zip` from the prior promoted `1055IST` bundle. It fails in MAIN preflight with exactly one stalled launch side:

- root `[88,3,left]`
- front `355`
- traces `3717..3725`
- max visible side outcome `177.0224303114486`
- `4107/4107` launch traces otherwise visible
- zero short MAIN terminations, illegal turns, intersections, overlaps, clearance violations
- one causal repair reported success, but the side still remained stalled

The raw user ZIP is preserved beside this summary.

## Architectural findings corrected

1. Root fan readiness was still delayed by the old four-module egress gate after the four-module *straight* lock had been removed. A whole side bus could therefore bend before it was permitted to partition.
2. Ordinary MAIN scoring still had an explicit synthetic turn reward after two straight gestures. This produced a systematic whole-bus bend cadence rather than seeded/open-space routing variance.
3. Fan topology used a fixed preferred outward/straight pattern first; alternate permutations participated only if the preferred pattern failed.
4. Fan transaction collision used coarse cohort envelopes, falsely rejecting physically clean turning fan layouts because adjacent fan envelopes overlap near the split.
5. 9--24 line launches could be partitioned into only two large routing cohorts; production now uses several balanced contiguous cohorts.
6. Side-level >=8-module visible progress was still mainly a late audit/special-fragment rule. The last live outcome of an unsatisfied side now carries live construction debt and cannot casually terminate below that side-progress requirement.
7. Different launch sides of the same chip were excluded from multiple MAIN head-connection passes. They are now separate connection families after source egress; same-side siblings remain non-connectable.
8. Stress seed base `2026080602` / sample `1909786089031391816` exposed a stale sibling fan-rebase exemption: a child whose first rebase had been blocked could later turn across a sibling corridor while inheriting an exemption intended only for parallel straight rebase. The exemption now requires the *candidate direction itself* to remain straight. A permanent regression physically crosses the longer sibling corridor and proves rejection.

## Preserved hard rules

- ordinary per-line MAIN maturity/survival minimum remains **4 modules**;
- no restored “first four modules must be straight” rule;
- one side outcome must establish the separate >=8-module visible side-progress certificate;
- no whole-board reseed / safe-seed fallback;
- no relaxed geometry clearance;
- no late validator used as normal acceptance/rejection policy.

## Qualification

- maintained geometry stress: **1/1 PASS**; includes base seed `2026080602` -> sample seed `1909786089031391816` that exposed the sibling crossing;
- active release gate: **175/175 PASS**, zero failures/errors/skips/xfails;
- three fresh plain-production `1:1 @ 1.0` renders from base seed `20260827`: all emitted successfully;
  - sample `12565985740840879884`: 82/82 launch traces visible, 0 stalled sides, 0 MAIN short terminations, 0 unaccounted launches, 8 MAIN connections, 44 viable fan alternatives accumulated;
  - sample `15721168286875887018`: 84/84 visible, 0 stalled, 0 short, 0 unaccounted, 11 MAIN connections, 37 viable fan alternatives;
  - sample `2688448046438059489`: 84/84 visible, 0 stalled, 0 short, 0 unaccounted, 10 MAIN connections, 31 viable fan alternatives.
- fresh visual inspection of those SVGs confirms root sides now partition into multiple cohorts that can take different directions rather than a single whole-bus bend. This is a representative screen, not a claim that aesthetics are mathematically exhausted for all seeds.

## Small same-seed runtime screen

This was not an optimization qualification, only a regression sanity check:

- prior `1055IST` renderer, `1:1 @ 1.0`, base seed `20260827`, count 3: **20.54 s**, max RSS 181024 KB;
- candidate renderer, same request: **20.23 s**, max RSS 143584 KB.

No material slowdown is visible in this small screen; no broad performance claim is made from it.
