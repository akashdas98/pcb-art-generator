# V46 Whole-Program Optimization Audit

## Governing invariant

Increasing aspect length or decreasing scale may increase **how much logical territory exists**, but must not make a local decision inspect/rebuild the entire board. Expected work is primarily proportional to logical territory, with bounded local stochastic variation and ordinary spatial-index overhead.

## Removed high-level scaling failures

1. **Large-N collection calibration:** eliminated N-dimensional quota-state growth that assumed tiny populations.
2. **Whole-population duplicate retry:** localized retry to the offending template/category.
3. **Per-chip global head state:** replaced with one shared labeled head index.
4. **Area-scaled repeated full-board local waves:** bounded waves; opportunity scales inside the work unit.
5. **Global rollback history:** route recovery owns and rewinds only the affected front's segments.
6. **Repeated global residual-region/site allocation:** replaced with stable region partitions and exact lazy priority queues.

## Removed low-level implosive wedges

- terminal-head all-pairs pairing;
- terminal-marker all-pairs conflict/cluster scans;
- repeated whole-board lane reconstruction during local joins;
- giant GeometryCollection/union distance/intersection operations where primitive-local set-equivalent checks exist;
- scalar Python→GEOS nearest-distance calls across whole residual grids;
- temporary local-bundle all-pairs affinity matching;
- per-source rescans of the full residual field;
- per-filler re-sort of every residual region;
- selected-site all-pairs spacing checks;
- per-route final audit against every static object;
- terminal repair snapshots of unrelated board history;
- reverse scans of global segment history to shorten one terminal.

## Behavior corrections discovered during audit

- Unbundled local traces were accidentally retargeted every round; V46 restores the documented “retarget only after actual temporary bundle release” rule.
- Expanding nearest-head broad phase previously risked marking square-box candidates as permanently seen before they entered the circular radius; V46 exactness guard prevents this semantic loss.
- Mixed static indexes may contain groups and primitives; scoring/access now honors the index contract rather than assuming one object type.
- Visible terminal-dot clipping can leave an otherwise mature chip side just below the hard 8-module visible-progress floor. V46 repairs only by exact legal physical extension; it does not lower the floor.

## Deliberately retained linear/global work

Some operations remain whole-population because their semantic scope genuinely is whole-population and they occur only once or once per bounded round: active-front lifecycle collection, rebuilding an authoritative spatial index after a rollback batch, deterministic sort of active fronts, final report aggregation. These are not nested inside every local candidate decision.

## Verification rule

Every optimization that replaces an exact scan/predicate is either mathematically set-equivalent or covered by old-vs-new/brute-force tests. Performance acceptance is run only after the static audit and behavior suite are complete.
