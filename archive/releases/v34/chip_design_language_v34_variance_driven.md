# PCB Graphic Design Language — v34 Deterministic Portable — Local-Space Causal Routing and Scale Rebalance

## 0. Status and normative contract

This is the **single authoritative, context-independent specification** for the active v34
route-first board language and its deterministic bundle-gesture pathway system.

It consolidates:
- cumulative m1–m17 / v17 behavior,
- the portable scale calibration,
- the later corrections for curve geometry, overlap, multi-sample reuse, perpendicular-stack density/coverage, collection-border frequency, and mini-IC terminal length.

The active generation order is normative and hierarchical:

1. generate and place main chips;
2. route the complete main-chip pathway network against main chips only;
3. route the local residual-gap pathway wave against the frozen main network;
4. freeze all pathways;
5. generate and place secondary components into the residual free field.

Secondary components never exist spatially during pathway routing and therefore can never block,
steer, terminate, or trigger recovery in the router. Final component placement adapts to the routed
board; the router is never rerun to accommodate a component.

### 0.0.1 Hard parallel-routing invariant

"Parallel" is an algorithmic invariant, not a descriptive aspiration. During every movement round:

1. all ready traceback/rollback operations complete before the movement snapshot is taken;
2. every active front proposes from the same immutable committed snapshot;
3. provisional proposals never become obstacles for another proposal in that round;
4. proposals that can interact are grouped into a bounded local conflict transaction;
5. a conflict transaction commits only if one compatible proposal can be selected for **every**
   participating front;
6. if no complete compatible assignment exists, the transaction commits **nothing** that round and
   schedules causal/local rollback instead;
7. iteration order, front id, proposal sort order, or commit order may never grant permanent spatial
   priority;
8. recent history belonging to the blocker, the blocked route, or both may be rewound;
9. a root main-chip launch may rewind all post-emergence gestures back to its emergence anchor unless
   a real physical/shared-prefix connection has explicitly raised its recovery floor;
10. young main-chip launches receive survival priority over unrelated recent route history: before a
    young launch is allowed to die against a foreign active corridor, that blocker must be considered
    for rollback/yield.

The forbidden model is: `parallel proposal -> priority-sorted winner commits -> loser reroutes`.
The required model is: `common snapshot -> joint local arbitration -> atomic commit or joint repair`.
No A*, global route search, or full-board permutation solver is implied by this invariant; conflict
transactions remain local and bounded.

### 0.0.2 V33 hard source-egress / family-survival invariant

V33 strengthens the parallel invariant at the chip source. These rules are normative and apply to
every emitted main-chip lane, including sides that produce only one routing cohort:

1. **Physical source egress is indivisible.** The complete emitted bus remains straight and
   perpendicular to its chip side until the shortest materialized lane has travelled **4 routing
   modules** from its emergence point. Fan, ordinary branch, recovery fragmentation, and any other
   structural split are forbidden before that physical boundary is cleared.
2. **Egress state is physical, not historical.** Clearing the source once does not permanently mark a
   route mature. If traceback moves a root back inside the 4-module zone, source protection and its
   temporary reservation reactivate immediately.
3. **Per-lane temporary reservations protect unclaimed emergence space.** Mature/foreign routing and
   local-gap fillers may not consume another main lane's still-active source corridor. Two still-young
   main families remain peers: reservations do not pre-award space between them; their proposals are
   resolved by the transactional conflict solver.
4. **A sibling may HOLD.** When a protected same-family transaction has no compatible all-move
   assignment, a bounded atomic solution may move only the compatible siblings while the others HOLD
   for that round. HOLD is a jointly selected no-op, never sequential winner/loser ownership.
5. **Local-gap peers may also HOLD.** Local fillers are allowed the same atomic no-op when an
   all-move local transaction would deadlock. This prevents gesture-zero local deaths and lets the
   active 40–50% residual-gap target remain meaningful without increasing global search.
6. **No foreign-head blind spot.** The start-of-gesture ownership disk may exempt only self/ancestor
   continuation. Foreign committed geometry is checked against the complete proposed corridor, even if
   it lies only a few pixels beyond the current head.
7. **Bundle corridors have a flat leading edge.** A wide bus may not claim the semicircular future
   area implied by a round-capped whole-bus envelope. Exact lane heads advance together; turn/miter
   clearance remains conservative at corners.
8. **Hard main-launch survival floor = 4 physical modules.** A main route below that floor may not be
   terminalized or silently pruned. After clearing it, one bounded soft persistence attempt toward
   **6 modules** is preferred, but failure of that soft attempt is not a reason for unbounded rerouting
   or whole-board rejection.
9. **Materialization may not undo routing survival.** Terminal backoff/marker clipping cannot reduce a
   valid main route below the hard visible floor or create a sub-0.10-module visible segment. Escaped
   traces are rendered only to their first canvas-frame crossing; invisible off-canvas continuation may
   never cause final collision cleanup to delete a visible route.
10. **Final cleanup is diagnostic, not a hidden routing policy.** An accepted main network MUST report
    equal launched/visible main-lane counts and zero main-short terminals. Materialization that would
    suppress a main lane is an acceptance failure, never an aesthetic cleanup. Intersection/zigzag cleanup
    may still diagnose soft local filler failures, but may not reduce the visible main launch population.

These requirements supersede older recovery/termination rules wherever those rules would allow a
newborn main lane to be stranded by sibling history, foreign near-head history, bookkeeping age, or
render-time cleanup. Historical changelogs remain historical and are not rewritten.

### 0.1 No free-form visual interpretation

For generation, prose adjectives are **non-normative** unless they are explicitly mapped to numbers in this document.

A renderer MUST NOT decide independently what words such as:
- small
- large
- mild
- tight
- sparse
- dense
- compact
- frequent
- rare
- near
- far
- varied
- balanced
- substantial

mean visually.

The normative system is:
1. constants,
2. probability distributions,
3. weighted permutations,
4. numeric ranges,
5. deterministic algorithms,
6. hard validation tests.

If a prose description and a numeric rule appear to conflict, the numeric rule wins.

### 0.2 Output invariant

Different seeds must produce:

> **different instances of the same grammar**

not:
- different visual languages,
- different scale systems,
- different curve families,
- different object-size interpretations,
- reusable prefab collections.


### 0.3 Exact-quota precedence clarification

Where an older weighted-selection instruction conflicts with an explicit exact batch quota or a hard acceptance condition, the exact quota/hard condition is normative. In particular, `N_ic` and `N_dense` are exact membership counts and may not be increased by filler sampling.

This clarification resolves an execution contradiction; it does not change the intended default occurrence rates or add/remove any visual family.

---

# 1. Deterministic random system

## 1.1 Required PRNG

Use **SplitMix64** for all random draws.

State and output are unsigned 64-bit integers.

```text
function splitmix64_next(state):
    state = state + 0x9E3779B97F4A7C15
    z = state
    z = (z XOR (z >> 30)) * 0xBF58476D1CE4E5B9
    z = (z XOR (z >> 27)) * 0x94D049BB133111EB
    z = z XOR (z >> 31)
    return state, z
```

All arithmetic wraps modulo `2^64`.

Convert output to a uniform real:

```text
R = ((z >> 11) & ((1<<53)-1)) / 2^53
```

so:

`0 <= R < 1`

## 1.2 Seed derivation

If the user supplies `SEED`, use it exactly.

If the user does not supply a seed:
- generate one fresh unsigned 64-bit seed from the host's cryptographic random source,
- record it in SVG metadata,
- use that value as `SEED`.

Do not use a fixed default seed across independent requests.

Given base seed `SEED`:

```text
sample_seed(i) =
    SplitMix64(SEED XOR 0xA0761D6478BD642F XOR i).output

chip_seed(sample_seed, j) =
    SplitMix64(sample_seed XOR 0xE7037ED1A0B428DB XOR j).output

collection_seed(sample_seed, k) =
    SplitMix64(sample_seed XOR 0x8EBC6AF09C88C6E3 XOR k).output

placement_seed(sample_seed) =
    SplitMix64(sample_seed XOR 0x589965CC75374CC3).output
```

Indices start at `0`.

No sample, chip, or collection may share the same PRNG state.

## 1.3 Sampling rules

Unless a distribution says otherwise:

`Uniform(a,b) = a + R*(b-a)`

For a weighted discrete choice:
- normalize listed weights,
- accumulate in listed order,
- choose the first bucket whose cumulative weight exceeds `R`.

For a shuffled list:
- use Fisher–Yates driven by the relevant PRNG stream.

---

# 2. Canvas normalization and style constants

Let:

```text
W = canvas width
H = canvas height
S_canvas = min(W,H)
MASTER_SCALE = explicit user/runtime argument, default 1.000
S = S_canvas * MASTER_SCALE * (1200 / 1600)
U = S / 1200 = S_canvas * MASTER_SCALE / 1600
```

`W` and `H` define the unchanged canvas. `S` and `U` define the physical scale of generated
geometry inside that canvas. Therefore `MASTER_SCALE < 1` makes chips, components, strokes,
clearances, pathway modules, and other design-language geometry smaller without changing canvas
dimensions; `MASTER_SCALE > 1` makes them larger.

`U` is the only absolute construction unit. A renderer MUST NOT use unscaled raw pixels for geometry.

## 2.1 Default palette

```text
BACKGROUND = #101319
FOREGROUND = #e7e1d2
```

No additional colors.
No glow.

## 2.2 Default stroke system

All values below are final rendered values before any collection-local `0.78` transform unless explicitly marked as collection-local.

| Use | Width |
|---|---:|
| main chip body | `3.2U` |
| main chip inner border | `1.9U` |
| main chip curved ornament | `1.9U` |
| main chip micro-line | `2.1U` |
| mini-IC body | `1.8U` local |
| hollow ordinary square/circle | `1.8U` local |
| collection outer border | `1.5U` local |
| dense-dot module border | `1.5U` local |
| ordinary collection dash | `2.1U` local |
| filled chip dash thickness | `3.2U` |
| exterior chip dash thickness | `2.8U` |

Curved ornaments use round line caps.
Straight technical dashes use square/rectangular geometry.

## 2.3 No automatic fit scaling

Default master scale:

`MASTER_SCALE = 1.000`

`MASTER_SCALE` is a passable renderer argument and is independent of `W` / `H`. It MUST remain
constant for the complete sample once supplied. It is **not** an automatic fit variable.

The renderer MUST NOT reduce or enlarge the design because:
- placement is difficult,
- the canvas has fewer pixels,
- a sample is crowded,
- routing is constrained,
- a local object fails collision tests.

If placement fails, reject/resample/regenerate/restart according to the bounded rules; never mutate
`MASTER_SCALE` internally. Only the explicit user/runtime argument may set it.

---

# 3. Batch composition

## 3.1 Main-chip count

Choose exactly:

| Count | Probability |
|---:|---:|
| 3 | `0.50` |
| 4 | `0.50` |

## 3.2 Isolated-collection count

| Count | Probability |
|---:|---:|
| 15 | `0.20` |
| 16 | `0.30` |
| 17 | `0.30` |
| 18 | `0.20` |

## 3.3 Layer order

Render:
1. background,
2. main chips,
3. isolated collections.

No pathways.

---

# 4. Main-chip body geometry

For each chip independently:

## 4.1 Short-side size

The chip short side is sampled continuously over the full allowed interval with a center bias.

```text
u_q = (R1 + R2) / 2
q_chip = 0.078S + (0.105S - 0.078S) * u_q
```

There are no low/medium/high size modes.

## 4.2 Aspect ratio

Sample one continuous aspect driver:

```text
u_A = R^0.82
A = 1.20 + (1.67 - 1.20) * u_A
long_side = q_chip * A
```

The exponent biases the continuous distribution mildly toward elongation without creating aspect categories.

Hard acceptance interval:

`0.110S <= long_side <= 0.151S`

If outside:
- resample only `A`.

Aspect classifications may be computed later for diversity/fingerprint diagnostics but do not participate in sampling.

## 4.3 Orientation

| Orientation | Probability |
|---|---:|
| horizontal | `0.67` |
| vertical | `0.33` |

Horizontal:
- `width = long_side`
- `height = q_chip`

Vertical:
- `width = q_chip`
- `height = long_side`

## 4.4 Corner radius

| Mode | Probability |
|---|---:|
| square | `0.15` |
| rounded | `0.85` |

Rounded:

`rx = Uniform(2.1U,2.7U)`

Square:

`rx = 0`

---

# 5. Main-chip motif selection

Allowed motif IDs:

```text
M1 = internal rectangular borders
M2 = central dotted pattern
M3 = central dash pattern
M4 = outside corner dots
M5 = corner-hugging curves
M6 = exterior parallel dash rails
M7 = central pad/micro-mark field
M8 = exterior perpendicular dash stacks
```

No other motif ID exists.

## 5.1 Motif count

Motif count is the bounded integer projection of a continuous complexity driver:

```text
c_motif = (R1 + R2) / 2
active_motifs = 1 + min(3, floor(4 * c_motif^0.90))
```

Thus motif richness varies continuously before being projected to the required integer count; there is no motif-count preset table.

## 5.2 Selection weights

Weighted sampling without replacement:

| Motif | Weight |
|---|---:|
| M1 | `1.00` |
| M2 | `0.72` |
| M3 | `0.78` |
| M4 | `0.52` |
| M5 | `0.52` |
| M6 | `0.68` |
| M7 | `0.62` |
| M8 | `0.78` |

Constraint:

`M2`, `M3`, and `M7` are mutually exclusive.

At most one central interior-pattern motif may be selected.

If the sampled set violates the constraint:
- discard the later-selected conflicting central motif,
- continue weighted sampling until the requested motif count is reached.

## 5.3 Minimum internal structure

If motif count is `>= 2`:
- at least one of `M1`, `M2`, `M3`, `M7` must be active.

If not:
- replace the lowest-weight selected exterior motif with a weighted choice among `M1`, `M2`, `M3`, `M7`.

---

# 6. Main-chip internal geometry

## 6.1 M1 — internal rectangular borders

Border count is derived conditionally rather than selected from a count menu:

```text
border_count = 1
if R1 < 0.45:
    border_count = 2
    if R2 < (0.10 / 0.45):
        border_count = 3
```

This preserves approximately the previous 55% / 35% / 10% occurrence profile while expressing the result as conditional probabilistic growth.

First inset:

`inset_1 = Uniform(12U,15U)`

Additional inset increment:

`inset_step = Uniform(8U,11U)`

Border `i` inset:

`inset_i = inset_1 + (i-1)*inset_step`

All internal borders:
- same center as chip body,
- same corner-radius fraction as the outer body,
- stroke `1.9U`.

## 6.2 Central safe rectangle

If M1 is active:

```text
safe_inset =
    inset_last + Uniform(9U,12U)
```

If M1 is inactive:

`safe_inset = Uniform(18U,22U)`

The central motif must fit completely inside:

```text
[-width/2 + safe_inset, width/2 - safe_inset]
[-height/2 + safe_inset, height/2 - safe_inset]
```

No central motif is allowed to extend outside this rectangle.

## 6.3 M2 — central dotted pattern

Pattern topology remains categorical because the operations differ:

| Type | Probability |
|---|---:|
| filled grid | `0.50` |
| dotted perimeter rectangle | `0.25` |
| compact matrix | `0.25` |

Dot radius:

`r = Uniform(1.8U,2.5U)`

Pitch for `filled grid` and `dotted perimeter rectangle`:
- horizontal: `px = Uniform(10U,14U)`
- vertical: `py = Uniform(10U,14U)`

For `compact matrix`, use the same full `10U–14U` interval but bias continuously toward the tight end:

```text
px = 10U + 4U * R^2.50
py = 10U + 4U * R^2.50
```

Grid dimensions are derived from the available safe rectangle instead of selected from rows/columns tables.

```text
max_cols = max(1, floor((safe_width  - 2r) / px) + 1)
max_rows = max(1, floor((safe_height - 2r) / py) + 1)

cols = bounded_integer(1, max_cols, R^0.85)
rows = bounded_integer(1, max_rows, R^1.25)
```

`bounded_integer(lo,hi,u)` maps continuous `0<=u<1` monotonically to every integer in `[lo,hi]`.

The sampled pattern must remain completely inside the central safe rectangle.

## 6.4 M3 — central dash pattern

Orientation:
- horizontal rows: `0.50`
- vertical columns: `0.50`

Dash length:

`dash_length = Uniform(8U,13U)`

Dash thickness:

`3.2U`

Center-to-center dash pitch:

`dash_pitch = dash_length + Uniform(5U,8U)`

Band pitch:

`band_pitch = Uniform(11U,18U)`

The safe rectangle determines the maximum feasible marks and bands.

```text
max_marks = maximum integer count fitting along the mark axis
max_bands = maximum integer count fitting along the band axis

marks = bounded_integer(1, max_marks, R^0.80)
bands = bounded_integer(1, max_bands, R^1.15)
```

If the exact stroke-expanded result does not fit, decrement marks first, then bands; otherwise reject/regenerate M3.

## 6.5 M7 — pad/micro-mark field

Type remains categorical because primitive construction differs:

| Type | Probability |
|---|---:|
| hollow pads | `0.40` |
| filled dots | `0.30` |
| short lines | `0.30` |

Horizontal pitch:

`px = Uniform(10U,13U)`

Vertical pitch:

`py = Uniform(9U,12U)`

Grid dimensions are derived from the safe rectangle:

```text
max_cols = max(1, floor(safe_width  / px) + 1)
max_rows = max(1, floor(safe_height / py) + 1)

cols = bounded_integer(1, max_cols, R^0.90)
rows = bounded_integer(1, max_rows, R^1.25)
```

Pad side:

`Uniform(4.5U,6.5U)`

Dot radius:

`Uniform(1.5U,2.0U)`

Line length:

`Uniform(6U,9U)`

Line stroke:

`2.1U`

For a `short lines` field, sample one subgroup orientation:
- horizontal: `0.50`
- vertical: `0.50`

All short lines in that subgroup use the sampled orientation.

The exact field must fit the central safe rectangle; otherwise reject/regenerate M7.


---

# 7. Main-chip exterior geometry

## 7.1 Common side-set distribution

For M6 and M8 independently:

| Side configuration | Probability |
|---|---:|
| one random side | `0.25` |
| two opposite sides | `0.50` |
| all four sides | `0.25` |

For two opposite sides:
- top+bottom and left+right each have probability `0.50`.

If M6 and M8 are both active:
- generate M6 sides first,
- generate M8 sides second,
- if any M8 side collides with M6 after exact geometry construction, resample the M8 side set,
- maximum side-set retries: `32`,
- if still invalid, resample M8 geometry,
- never move M8 farther from the chip to force coexistence.

## 7.2 M4 — outside corner dots

For each chip corner:

Dot radius:

`Uniform(2.5U,3.1U)`

Let outward signs:
- left `ox=-1`
- right `ox=+1`
- top `oy=-1`
- bottom `oy=+1`

Dot-center offset from the geometric chip corner:

```text
dx = ox * Uniform(7.8U,9.2U)
dy = oy * Uniform(7.8U,9.2U)
```

All four corners use the same sampled absolute `|dx|` and `|dy|` for that chip.

## 7.3 M5 — corner-hugging curve

This section defines the **only allowed curve family**.

No circular-arc substitution.
No bracket glyph substitution.
No hand-chosen Bézier shape.

For each corner:

```text
C = (cx,cy)
q = q_chip
ox = outward horizontal sign
oy = outward vertical sign
```

Let the chip-body area be:

`A_chip = width * height`

and the chip near-corner scale be:

`a = sqrt(A_chip)`

Sample one near-corner stand-off for the chip:

`g = Uniform(0.024a, 0.040a)`

This keeps the bracket near the corner without touching the geometric corner itself.

Sample one arm-reach distance for the chip:

`d = Uniform(0.054q, 0.070q)`

Sample one curvature parameter for the chip:

`kappa = Uniform(0.30,0.54)`

Use the same `g`, `d`, and `kappa` at all four corners.

Define the shifted corner anchor:

```text
C_star = (cx + ox*g, cy + oy*g)
```

Define endpoints:

```text
P_h = (C_star.x - ox*d, C_star.y + oy*d)
P_v = (C_star.x + ox*d, C_star.y - oy*d)
```

Define quadratic-Bézier control point:

```text
Q = (C_star.x + ox*kappa*d,
     C_star.y + oy*kappa*d)
```

Render exactly:

```text
QuadraticBezier(P_h, Q, P_v)
```

Stroke:
- `1.9U`
- round caps
- no fill

Properties produced by this construction:

```text
sagitta/chord = kappa / 4
```

Therefore the allowed curvature is exactly:

`0.075 <= sagitta/chord <= 0.135`

The curve position is tied to the chip itself:

`0.024a <= g <= 0.040a` and `0.054q <= d <= 0.070q`

No renderer may reinterpret:
- convexity,
- curvature family,
- endpoint topology,
- distance from the corner.

If the curve intersects another ornament:
- reject/resample the ornament combination,
- do not alter this construction outside its numeric ranges.

## 7.4 M6 — exterior parallel dash rails

For each active side:

Body-to-rail centerline gap:

`Uniform(8U,11U)`

Rail span fraction of the full chip side:

`Uniform(0.40,0.65)`

Dash length:

`Uniform(7U,12U)`

Dash thickness:

`2.8U`

Clear gap between adjacent dashes:

`Uniform(1.5,3.0) * dash_thickness`

Derive dash count:

```text
n = floor(
    (rail_span + clear_gap) /
    (dash_length + clear_gap)
)
```

Hard minimum:

`n >= 3`

If `n < 3`:
- resample dash length/gap.

Center the whole rail on the chip side.

## 7.5 M8 — exterior perpendicular dash stacks

For each active side:

Body-to-nearest-dash gap:

`Uniform(6U,8U)`

Dash length perpendicular to body:

`Uniform(7U,10U)`

Dash thickness:

`2.8U`

### Continuous span distribution

There is no long/short mode. Sample directly over the full allowed span range with a high-span bias:

```text
span_fraction = 0.35 + 0.55 * R^0.326
span = span_fraction * full_side_length
```

This calibration places about 75% of draws at or above the former `0.70` long-span threshold while every intermediate span remains possible.

### Continuous packing distribution

There is no tight/moderate mode. Sample the clear-gap multiplier continuously:

```text
gap_multiplier = 1.0 + 3.0 * R^3.82
clear_gap = gap_multiplier * dash_thickness
```

This calibration places about 75% of draws in the former `1.0–2.0 × thickness` tight region while preserving the complete continuous interval through `4.0 × thickness`.

Derive count:

```text
pitch = dash_thickness + clear_gap
n = floor((span - dash_thickness) / pitch) + 1
```

Hard minimum:

`n >= 4`

If `n < 4`:
- resample only the packing driver,
- do not expand span outside its sampled value.

Center the stack on the side.


---

# 8. Collection-level constants

Collection-local geometry is generated in canonical local units, then the entire finished collection uses:

`COLLECTION_SCALE = 0.780`

This scale is fixed by default.

No per-collection random scale multiplier exists.

Variation in collection footprint comes from:
- entity count,
- grid dimensions,
- family combination,
- local arrangement.

A renderer MUST NOT invent a separate collection-scale range.

## 8.1 Collection complexity

Combination richness is generated per collection from a continuous latent complexity value; there are no Tier-1/Tier-2/Tier-3/Tier-4 layout classes.

```text
c = (R1 + R2) / 2
family_count = 1 + min(4, floor(5 * c^1.50))
```

This yields a center concentrated around low-to-medium combination richness with a smaller high-complexity tail.

Conditional corrections:
- `family_count >= number_of_required_special_families`,
- if the collection has neither `ic` nor `dense`, cap `family_count` at `4` because there are four ordinary family labels,
- mixing requirements in §8.2 may promote a flagged collection's family count to at least `2`; they may not introduce a new family label or change exact special-family quotas.

The latent `c` may be stored for diagnostics but has no named complexity class.

## 8.2 Batch family quotas

For `N` collections:

```text
N_ic     = round(0.625 * N)
N_dense  = round(0.845 * N)
N_border = round(0.700 * N)
```

These are exact target counts for the default sample.

They replace vague per-sample interpretation of:
- "frequent IC",
- "frequent dense modules",
- "60–80% borders".

### IC mixing requirement

At least:

`ceil(0.85 * N_ic)`

IC-containing collections must have family-count `>=2`.

Therefore IC-only one-family collections are capped at:

`floor(0.15 * N_ic)`

### Dense mixing requirement

At least:

`ceil(0.70 * N_dense)`

dense-containing collections must have family-count `>=2`.

### Ordinary-family coverage

For `N >= 15`, each ordinary family:

```text
square
circle
capacitor_circle
dot
dash
```

must appear in at least `2` distinct collections.

The `capacitor_circle` entity is additionally available as an optional ordinary family inside collections. It participates in weighted family assignment but is not itself subject to a mandatory minimum coverage quota; §11.3 also defines its independent isolated occurrence path.

---

# 9. Collection family assignment algorithm

For each sample:

1. choose exactly `N_ic`, `N_dense`, and `N_border` collection indices;
2. sample one continuous collection-complexity driver `c` per collection and derive `family_count` by §8.1;
3. pre-fill exact required `ic` / `dense` families;
4. raise `family_count` only as necessary to hold required special families;
5. enforce the IC/dense mixing requirements by promoting the family count of randomly shuffled eligible flagged collections to at least `2`;
6. fill remaining family slots by weighted sampling without replacement from ordinary families:

| Family | Weight |
|---|---:|
| square | `1.00` |
| circle | `1.00` |
| capacitor_circle | `3.90` |
| dot | `1.00` |
| dash | `1.00` |

7. after all collections are assigned, enforce ordinary-family minimum coverage:
   - if a family occurs fewer than twice,
   - replace a non-required ordinary family in randomly shuffled eligible collections,
   - never alter IC/dense quota counts,
   - never alter family count.

A family appears at most once as a family label inside a collection. Its internal entity count may exceed one **except for `capacitor_circle`**, which is singleton-only by construction.

The exact-quota precedence rule in §0.3 remains mandatory: filler never adds unflagged `ic` or `dense`.

---

# 10. Ordinary collection-family geometry

Square, circle, dot, and dash ordinary-family subgroups sample one lattice. `capacitor_circle` is explicitly excluded from the lattice system: one capacitor-family occurrence produces exactly one capacitor entity at the subgroup origin.

## 10.1 Lattice class

| Lattice | Probability |
|---|---:|
| orthogonal strip | `0.35` |
| orthogonal grid | `0.35` |
| diagonal grid | `0.20` |
| staggered grid | `0.10` |

These are **subgroup lattice calculations**, not complete collection templates.

## 10.2 Entity count

For square, circle, dot, and dash families, entity population is a bounded integer projection of a continuous center-biased driver:

```text
u_count = (R1 + R2) / 2
count = 2 + min(5, floor(6 * u_count))
```

Thus every integer count from `2` through `7` is reachable without a count preset table.

For `capacitor_circle`:

```text
count = 1
```

This is a semantic singleton rule, not a size/count preset. Capacitor entities must never be expanded into strips, chains, grids, staggered lattices, diagonal lattices, or any other repeated subgroup pattern.

## 10.3 Ordinary pitch

For each collection sample once:

`P_ord = Uniform(9.5U,13.0U)`

All ordinary-family lattices in that collection derive their base pitch from `P_ord`.

Per subgroup:

```text
pitch_x = P_ord * Uniform(0.90,1.10)
pitch_y = P_ord * Uniform(0.90,1.10)
```

## 10.4 Lattice construction

### Orthogonal strip
- orientation horizontal: `0.50`
- orientation vertical: `0.50`
- dimensions: `1 x count` or `count x 1`

### Orthogonal grid
Grid dimensions are derived from entity count and a continuous anisotropy driver:

```text
anisotropy = 1.0 + 2.5 * R^0.80
rows = max(1, round(sqrt(count / anisotropy)))
cols = max(1, ceil(count / rows))
```

Transpose rows/columns with probability `0.50`.

Unused final cells are omitted from the high-index end.

### Diagonal grid
Begin with the orthogonal-grid calculation.

Then rotate every lattice point around the subgroup origin by:

`45 degrees`

### Staggered grid
Begin with orthogonal grid.

Offset every odd-numbered row by:

`0.50 * pitch_x`

No other lattice classes exist for ordinary-family subgroups.

---

# 11. Ordinary entity geometry

All dimensions here are collection-local, before the final `0.780` scale.

## 11.1 Square family

Side length:

`Uniform(6U,9U)`

State mode:

| State | Probability |
|---|---:|
| all hollow | `0.40` |
| all filled | `0.35` |
| controlled mixed | `0.25` |

Mixed pattern:
- alternating by entity index: `0.60`
- one filled accent among otherwise hollow entities: `0.40`

Hollow stroke:

`1.8U`

## 11.2 Circle family

Radius:

`Uniform(2.5U,4.5U)`

State probabilities and mixed-state algorithm:
- identical to square family.

Hollow stroke:

`1.8U`

## 11.3 Capacitor-circle entity

This is a distinct circular secondary component intended to carry a clear **capacitor-like visual weight**. It is not merely a renamed ordinary circle. The same entity generator is available through two independent occurrence paths:

1. as a family inside collections;
2. as an isolated standalone secondary component on the canvas.

### Size

The outer radius uses one continuous, visibly wider distribution than the ordinary circle family:

```text
r_cap = (4.2 + 8.7 * R^0.90) U
```

Thus the generated radius spans `4.2U–12.9U` continuously. The additive size span is 50% wider than V22. No small/medium/large capacitor size menu exists.

When the entity is inside a collection, the collection's normal `COLLECTION_SCALE` applies. When isolated, it is rendered at its sampled standalone size.

### Visual state

Choose one genuinely categorical rendering state:

| State | Probability |
|---|---:|
| filled | `0.32` |
| hollow | `0.28` |
| concentric-ring | `0.40` |

Filled mode:
- one solid foreground circle.

Hollow mode:
- one hollow foreground circle, stroke `1.8U`.

Concentric-ring mode:
- one hollow outer circle;
- derive the number of inner rings from a continuous driver:

```text
inner_count = 1 + min(2, floor(3 * R^0.82))
```

- derive ring spacing continuously from the available radius;
- keep all rings concentric;
- preserve a positive visible gap between adjacent stroke-expanded rings.

The ring count is therefore an integer consequence of a continuous random variable, not a hand-authored ring-count option table.

### Occurrence inside collections

`capacitor_circle` participates in ordinary-family weighted sampling with weight `3.90`, exactly 3× the V22 weight of `1.30`, compared with `1.00` for the ordinary square/circle/dot/dash families. It remains optional and is not forced by the minimum ordinary-family coverage audit.

A selected capacitor family always materializes as exactly **one** capacitor entity. It does not call the ordinary entity-count, pitch, strip, grid, diagonal-grid, or staggered-grid rules. If multiple capacitors occur in one sample, they arise only from independent family occurrences in different collections and/or the isolated occurrence path.

### Isolated occurrence

For each complete sample, independently test:

```text
P(any isolated capacitor_circle) = 1.00  # 3×0.72 saturates at probability 1
```

If the occurrence test succeeds, derive the isolated count from one continuous intensity driver:

```text
count_isolated = 1 + min(2, floor(3 * R^1.10))
```

This yields a bounded `1–3` isolated capacitor-like entities without a discrete count-probability menu. Each isolated entity samples its own size and visual state independently.

Isolated capacitor entities are secondary placement sets:
- edge clearance: `20U`;
- clearance to main chips: `18U`;
- clearance to collections or other isolated capacitor entities: `12U`;
- they use the same spread-biased secondary placement logic as collections;
- each isolated capacitor is placed as an independent placement set, so two isolated capacitors may never overlap or touch and must satisfy the full `12U` clearance.

Concentric rings inside one capacitor are intentional internal structure and are not separate capacitor entities.

## 11.4 Ordinary dot family

Dot radius uses one continuous heavy-low-tail distribution rather than standard/accent modes:

```text
r = (2.1 + 2.9 * R^4.35) U
```

This keeps most dots near the former standard range while preserving a continuous, rarer large-radius tail through `5.0U`.

Dots are filled foreground.

## 11.5 Dash family

Length:

`Uniform(7U,12U)`

Thickness:

`2.1U`

Orientation:

For orthogonal strip/grid:
- horizontal `0.50`
- vertical `0.50`

For diagonal grid:
- diagonal `0.60`
- horizontal `0.20`
- vertical `0.20`

For staggered grid:
- horizontal `0.50`
- vertical `0.50`

Diagonal dash angle:
- `+45°` or `-45°`, each `0.50`.

---

# 12. Mini-IC family

All dimensions here are collection-local before `COLLECTION_SCALE`.

## 12.1 Mini-IC body

Short side:

`q_ic = Uniform(10U,14U)`

Aspect ratio is continuous across the complete allowed interval:

```text
A_ic = 1.00 + (1.85 - 1.00) * R^0.95
```

No near-square / medium / elongated sampling bins exist. Any such labels may only be computed after generation for diagnostics.

Orientation:
- horizontal `0.50`
- vertical `0.50`

Corner radius:

`1.2U`

Body stroke:

`1.8U`

## 12.2 Terminal-side mode

For a standalone or separate IC:

| Active sides | Probability |
|---|---:|
| 2 sides | `0.55` |
| 4 sides | `0.45` |

For 2-sided mode:
- left+right `0.50`
- top+bottom `0.50`

For an IC array:
- horizontal 1D array: left+right `0.60`, four sides `0.40`
- vertical 1D array: top+bottom `0.60`, four sides `0.40`
- 2D array: four sides `1.00`

## 12.3 Terminal length

Let:

`q_ic = min(body_width,body_height)`

Terminal length is sampled from one center-biased continuous distribution across the full hard interval:

```text
u_t = (R1 + R2) / 2
terminal_length_ratio = 0.20 + 0.20 * u_t
terminal_length = terminal_length_ratio * q_ic
```

This centers naturally near `0.30q_ic`; extreme short/long tails remain possible but uncommon.

Hard bounds are intrinsic to the formula:

`0.20q_ic <= terminal_length <= 0.40q_ic`

No central/tail mode exists.

## 12.4 Terminal thickness

`terminal_thickness = 0.18q_ic`

## 12.5 Terminal count per active side

For an active side of body-edge length `L_side`:

```text
rho = L_side / q_ic
```

Terminal count:

| Condition | Count |
|---|---:|
| `rho <= 1.15` | 1 |
| `1.15 < rho <= 1.45` | 2 |
| `rho > 1.45` | 3 |

Terminal centers are equally spaced:

```text
position_i = (i+1)/(n+1)
```

along the active body edge.

## 12.6 IC-family occurrence and arrangement

When a collection includes the IC family, arrangement emerges from conditional probability and procedural dimensions rather than a menu of `single / separate / connected-shape` presets.

### Step 1 — singleton condition

```text
if R1 < 0.10:
    generate one standalone IC
else:
    generate a multi-IC occurrence
```

### Step 2 — connectivity condition for multi-IC occurrences

```text
connected = (R2 < 0.91)
```

If not connected:
- generate `2` or `3` separate ICs by bounded continuous count projection, biased toward `2`,
- individual ICs may vary,
- arrange the subgroup as a 1D sequence; horizontal / vertical is sampled `0.50 / 0.50`,
- after full terminals, visible edge-to-edge gap is `Uniform(4U,8U)`,
- they must not touch.

If connected:
- all cells in the array are exact duplicates,
- derive dimensions procedurally as below.

### Connected dimension derivation

There is **no rows×columns shape table**.

```text
long_dim  = bounded_integer(2, 6, R^1.00)
short_cap = max(1, min(4, long_dim, floor(10 / long_dim)))
short_dim = bounded_integer(1, short_cap, R^1.00)

if R_transpose < 0.50:
    rows, cols = short_dim, long_dim
else:
    rows, cols = long_dim, short_dim
```

The numeric bounds constrain overall footprint and keep large chunks rare; they do not enumerate allowed shapes. Any integer pair produced by the rule is valid.

For a 1D horizontal array, terminal-side rule remains:
- left+right `0.60`, four sides `0.40`.

For a 1D vertical array:
- top+bottom `0.60`, four sides `0.40`.

For a 2D array:
- four sides `1.00`.

All cells in one connected array are exact duplicates in:
- body size,
- aspect,
- orientation,
- terminal-side topology,
- terminal count,
- terminal thickness,
- terminal length.

Horizontal center pitch:

`body_width + 2*terminal_length`

Vertical center pitch:

`body_height + 2*terminal_length`

This makes matching terminal tips touch exactly.

No bridge.
No stretched terminal.
No additional connector.

Post-hoc labels such as `chain`, `elongated`, or `balanced` may be reported for diagnostics only and never participate in dimension generation.


---

# 13. Dense-dot module

All dimensions are collection-local before `COLLECTION_SCALE`.

## 13.1 Occurrence

Occurrence count is already fixed by:

`N_dense = round(0.845*N)`

## 13.2 Grid-dimension generation

There is **no dense rows×columns lookup table**.

Dimensions are generated from independent continuous extent and anisotropy drivers:

```text
long_dim  = bounded_integer(3, 10, R^2.00)
short_cap = max(1, min(4, long_dim, floor(20 / long_dim)))
short_dim = bounded_integer(1, short_cap, R^1.90)

if R_transpose < 0.50:
    rows, cols = short_dim, long_dim
else:
    rows, cols = long_dim, short_dim
```

The short-axis exponent deliberately biases the system toward strong dimensional imbalance while allowing intermediate and balanced outcomes. The cell cap limits total area; it does not define particular permitted shapes.

Any post-hoc labels such as strip / elongated / compact are diagnostic only.

## 13.3 Grid orientation

| Orientation | Probability |
|---|---:|
| orthogonal | `0.50` |
| diamond, row-shifted | `0.25` |
| diamond, column-shifted | `0.25` |

Diamond-row mode:
- keep the base pitch axis-aligned,
- shift every odd row by exactly `0.50 * P_dense` along x,
- do not rotate the lattice.

Diamond-column mode:
- keep the base pitch axis-aligned,
- shift every odd column by exactly `0.50 * P_dense` along y,
- do not rotate the lattice.

This produces an alternating half-step lattice whose perceived grid shape is diamond-like rather than square.

## 13.4 Dot pitch

Use the collection's `P_ord`.

Sample tightening factor:

`F_dense = Uniform(0.50,0.70)`

Then:

`P_dense = P_ord * F_dense`

This is exactly 30–50% tighter than ordinary pitch.

## 13.5 Dense-dot radius

`r_dense = Uniform(1.7U,2.6U)`

Hard geometric condition:

`2*r_dense + 1.0U <= P_dense`

If false:
- resample radius.

## 13.6 Fill state

| State | Probability |
|---|---:|
| all filled | `0.35` |
| all hollow | `0.35` |
| controlled mix | `0.30` |

Controlled mix:
- 1D: alternate filled/hollow
- 2D: checkerboard by `(row+column)%2`

## 13.7 Mandatory local border

Border stroke:

`1.5U`

Border padding from the **stroke-expanded dot footprint**:

`Uniform(6U,9U)`

Border corner radius:

`2U`

Every dense-dot module has this border.

---

# 14. Generic collection packing algorithm

This section replaces all template/archetype interpretation.

A collection is built from independently generated family subgroups.

## 14.1 Family order

Randomly shuffle the selected family list.

The first family has no special semantic status.

## 14.2 Place first subgroup

Place its stroke-expanded local bounding-box center at:

`(0,0)`

## 14.3 Place every later subgroup

For each subgroup `G`:

1. compute its final local stroke-expanded geometry;
2. compute current accepted collection geometry `C`;
3. generate exactly `64` candidate translations.

For candidate `j`:

```text
theta_j = Uniform(0,2π)

Let `w_C,h_C` and `w_G,h_G` be the AABB dimensions. For the sampled axis `theta_j`:

```text
support_C = 0.5 * (abs(cos(theta_j))*w_C + abs(sin(theta_j))*h_C)
support_G = 0.5 * (abs(cos(theta_j))*w_G + abs(sin(theta_j))*h_G)

d_j = support_C + support_G + Uniform(3U,8U)

candidate_center =
    centroid(AABB(C))
    + d_j * (cos(theta_j), sin(theta_j))
```

The support terms are exact projections of the two AABBs onto the sampled separation axis. Therefore the construction provides a separating axis with at least the sampled `3U–8U` gap without treating each AABB as a larger circumcircle.
```

4. reject candidate if any visible geometry of `G` is closer than:

`3U`

to unrelated existing visible geometry in `C`.

5. For every valid candidate calculate:

```text
B = AABB(C union translated(G))
compactness_score =
    area(B)
    + 0.15 * perimeter(B)^2
```

6. choose the valid candidate with the **lowest** score;
7. ties are resolved by lower candidate index;
8. if no candidate is valid:
   - generate another set of 64 candidates;
   - maximum 8 rounds;
9. if still impossible:
   - regenerate the entire collection from its next retry seed.

No family is silently deleted.

## 14.4 Recenter and scale

After all family subgroups are placed:

1. compute the complete local content AABB;
2. translate content so AABB center is `(0,0)`;
3. add optional whole-collection border if assigned;
4. apply exactly:

`scale(0.780)`

to the entire collection.

---

# 15. Whole-collection outer border

Exactly `N_border = round(0.700*N)` collections receive an outer border.

No independent ad-hoc probability is used after the quota is assigned.

Construction:

1. finish all content;
2. resolve IC terminal touching;
3. include dense-module borders;
4. compute stroke-expanded content AABB;
5. sample padding:

`Uniform(7U,11U)`

6. draw one rectangular outer border around that AABB plus padding;
7. outer-border stroke:

`1.5U`

8. border corner radius:

`Uniform(1U,2U)`

9. include the outer border in the collection's collision geometry.

Content-to-border visible distance must be at least:

`7U`

before the final `0.780` collection scale.

---

# 16. Collection footprint calibration

After the final `0.780` scale:

Let:

```text
L_collection = max(final_width, final_height)
Q_collection = min(final_width, final_height)
```

Hard per-collection bounds:

```text
0.014S <= L_collection <= 0.096S
```

Batch requirements:

1. at least `80%` of collections must satisfy:

```text
0.026S <= L_collection <= 0.073S
```

2. median `L_collection` must satisfy:

```text
0.040S <= median(L_collection) <= 0.052S
```

3. median ratio of collection long dimension to main-chip short dimension must satisfy:

```text
0.42 <=
median(L_collection) / median(q_chip)
<= 0.56
```

If a batch fails:
- regenerate offending collections or the layout,
- do not apply a hidden collection-scale correction,
- do not change `COLLECTION_SCALE`.

---

# 17. Collision geometry

## 17.1 Authoritative geometry

Collision is computed from **final rendered geometry**.

Every primitive is converted to a filled collision region after:
- local geometry creation,
- stroke expansion,
- collection `0.780` scale,
- group translation,
- global placement translation.

## 17.2 Stroke expansion

For a stroke of width `t`:
- collision region extends `t/2` on both sides of its centerline.

## 17.3 Curve flattening

Quadratic curves are flattened to line segments with maximum geometric deviation:

`<= 0.25U`

before stroke expansion.

A smaller tolerance is allowed.
A larger tolerance is not.

## 17.4 Broad phase

AABBs may be used only to skip impossible intersections.

If expanded AABBs overlap:
- perform narrow-phase region intersection/minimum-distance testing.

AABB overlap is not itself a collision.
AABB non-overlap is sufficient to rule out collision only if the AABBs contain the complete final stroke-expanded geometry.

## 17.5 Narrow phase

Use:
- polygon intersection for filled/stroked regions,
- Euclidean minimum distance between collision polygons.

No renderer may use center-point or un-stroked-path tests as final validation.

---

# 18. Required clearances

All clearances are edge-to-edge after stroke expansion.

## 18.1 Inside one main chip

Unrelated motif groups:

`G_chip_internal = 6U`

Exceptions:
- nested borders are intentionally nested,
- a central pattern occupies the safe rectangle by §6,
- no other contact is allowed.

## 18.2 Inside one collection before collection scale

Unrelated family subgroups:

`G_collection_local = 3U`

After final scale, this becomes:

`2.34U`

## 18.3 Between distinct placement sets

| Pair | Minimum gap |
|---|---:|
| chip ↔ chip | `60U` |
| chip ↔ post-route collection / isolated secondary | `42U` |
| collection ↔ collection | `12U` |

The only zero-gap contact anywhere in v17 is:
- matching IC-array terminal tips inside one IC array.

## 18.4 Frame-edge clearances

True final footprint to canvas edge:

| Placement set | Minimum |
|---|---:|
| main chip | `120U` |
| collection | `20U` |

---

# 19. Global placement algorithm

## 19.1 Main chips first

For each main chip:

1. generate complete chip geometry from its chip seed;
2. generate candidate centers using placement PRNG;
3. each candidate:

```text
x = Uniform(edge_left, W-edge_right)
y = Uniform(edge_top,  H-edge_bottom)
```

where legal center limits include the candidate's true footprint plus §18.4 edge clearance;

4. compare against all accepted placement sets using §17 and §18;
5. collect valid candidates in small proposal batches sampled uniformly from the legal area;
6. with elevated probability, choose the valid candidate in that batch with the strongest spread score, where the score favors larger nearest-neighbor distances and lower local occupancy; otherwise accept the first valid candidate in the batch;
7. maximum candidate attempts per chip:

`4096`

7. if no valid position:
   - regenerate that chip with retry seed,
   - retry placement;
8. maximum chip-regeneration attempts:

`128`

9. if still impossible:
   - restart the complete sample with:

```text
retry_seed =
SplitMix64(sample_seed XOR retry_index).output
```

Do not rescale geometry.

## 19.2 Pathways before secondary components

After main chips are accepted, execute Section 27 completely before any collection or isolated
secondary receives a canvas position. During both pathway phases, the static obstacle set is the
main-chip set only; the later local-gap phase additionally treats the already-routed main pathway
network as occupied pathway geometry.

No secondary-component placement may cause a pathway reroute.

## 19.3 Connected-region residual component fill

After the main and local pathway networks are frozen:

1. generate the established collection population and isolated capacitor population from their deterministic streams;
2. sample a soft **area-weighted residual-region service target**:

```text
G_target = Uniform(0.90, 0.94)
```

3. analyze the remaining free field on a bounded `28×28` grid after applying exact chip/pathway keepouts, then partition free cells into 4-neighbor connected residual regions;
4. record each region's area, center, width, height, short span, and long span;
5. allocate the first component opportunities so the largest connected rooms accounting for at least 90% of residual-region area are represented before smaller repeated placements dominate;
6. distribute remaining opportunities by region area and fit larger collections before smaller isolated entities;
7. component size/family selection must be locally gap-aware: narrow/small pockets favor small capacitor/dot/dash/square/circle fillers, while larger rooms may accept collections and combinations of multiple fillers;
8. after the established population is placed, a bounded mop-up phase may add at most 28 gap-sized fillers, with a density target proportional to residual cell count and capped at 46 total accepted component placement sets;
9. the governing coverage metric is **served connected residual-region area**, not raw canvas pixel packing and not a global count of arbitrary point sites;
10. every placement uses exact frame, chip, pathway, and component geometry. Unauthorized component/pathway overlap is a hard rejection; the only exception is the explicitly designated terminal-attached component contact;
11. component-only layout/population retries operate against the frozen route network. Component failure may never rerun or steer routing.

The 90–94% rule means that components should meaningfully occupy/represent roughly 90% of the
remaining connected gap field while preserving visible breathing room. It is not a requirement to
cover 90% of every empty pixel with solid geometry.

## 19.4 Isolated capacitor-circle entities and reversed pathway attachment

Isolated capacitor-circle entities remain independent secondary placement sets. They normally use the
same post-route residual-fill process as collections and retain `12U` component-to-component
clearance.

Rare pathway-to-small-component relationships are created **in reverse**: after routing is complete,
an eligible free pathway terminal may receive an isolated capacitor centered on that terminal. The
component adapts to the pathway; the pathway never searches for or approaches a future component.
Only the local terminal contact region is exempt from the normal `10U` component-to-pathway
clearance. The component must still satisfy frame, chip, and other-component clearances.

No isolated capacitor may be grouped with another capacitor before placement.

---

# 20. Final collision audit

Prospective placement is not the final proof.

After all SVG transforms are final:

1. rebuild every collision region in canvas coordinates;
2. test every forbidden internal primitive pair;
3. test every distinct placement-set pair;
4. verify pair-specific clearance from §18.3;
5. verify every non-attached secondary component remains at least `10U` from pathway stroke geometry;
6. verify a pathway-attached isolated capacitor overlaps only its authorized terminal-contact region;
7. verify frame-edge clearance;
8. verify IC-array terminal contact exactly.

Acceptance requires:

```text
forbidden_intersection_count = 0
forbidden_touch_count = 0
clearance_violation_count = 0
IC_required_contact_failure_count = 0
```

Any non-zero result rejects the sample.

---

# 21. Multi-sample independence and no collection reuse

When one request asks for multiple samples, all samples belong to one **batch uniqueness domain**.

## 21.1 One-use collection rule

A completed collection construction has lifetime:

`1 instance`

It cannot be:
- copied,
- translated,
- rotated,
- mirrored,
- uniformly rescaled,
- cached,
- used as a prefab,
- reused in another sample.

## 21.2 Canonical collection fingerprint

For each completed collection before global placement:

1. include all visible primitives;
2. exclude global translation;
3. normalize the final collection AABB to width/height range `[0,1]`;
4. encode:
   - family set,
   - family counts,
   - entity counts,
   - lattice types,
   - filled/hollow modes,
   - IC mode,
   - IC array dimensions,
   - IC aspect ratio quantized to `0.02`,
   - IC terminal-side mode,
   - IC terminal-length ratio quantized to `0.01`,
   - dense dimensions,
   - dense orientation,
   - dense fill state,
   - outer-border state,
   - normalized primitive centers quantized to `0.02`,
   - normalized primitive sizes quantized to `0.02`.

5. calculate all 8 dihedral transforms of the normalized geometry:
   - rotations `0°,90°,180°,270°`,
   - each with and without reflection;

6. serialize each transformed signature;
7. choose the lexicographically smallest serialization;
8. SHA-256 hash it.

If the hash already exists anywhere in the current multi-sample request:
- reject the collection,
- regenerate from the next retry seed.

## 21.3 Near-duplicate rejection

If discrete structural fields match but hashes differ, compute normalized primitive-center RMS distance after the best of the 8 dihedral transforms.

Reject as near-duplicate when:

`RMS < 0.05`

and normalized size RMS difference is:

`< 0.05`

The same family combination may recur.

The same completed local construction may not.

---

# 22. Batch diversity checks

For one accepted sample:

## 22.1 Main chips

No two chips may have all of the following equal:
- orientation,
- aspect-ratio bin,
- motif set,
- inner-border count,
- exterior side-set configuration.

If equal:
- regenerate the later chip.

## 22.2 Collections

All collection fingerprints must be unique by §21.

## 22.3 Family coverage

Required:
- square appears in at least 2 collections,
- circle appears in at least 2,
- dot appears in at least 2,
- dash appears in at least 2,
- exact IC quota met,
- exact dense quota met,
- exact border quota met.

## 22.4 Dense-module shape balance

At least:

`60%`

of dense modules must have:

`max(rows,cols) / min(rows,cols) >= 2.5`

If not:
- regenerate dense dimensions in later dense modules until satisfied.

---

# 23. Natural-language tuning is numeric

Explicit user numbers always override this table.

When the user uses qualitative language, map it as follows.

## 23.1 Magnitude levels

| User phrase | Level |
|---|---:|
| slightly / a little | 1 |
| more / less / larger / smaller / tighter / looser | 2 |
| much / a lot / substantially | 3 |

## 23.2 Scalar size changes

Per level:

`factor = 1.10^level`

Increase:
- multiply by `factor`.

Decrease:
- divide by `factor`.

Apply only to the requested entity class.

Examples:
- "larger chips" level 2 → chip dimensions `×1.21`
- "smaller collections" level 2 → collection geometry `÷1.21`

## 23.3 Count changes

Per level:

`factor = 1.15^level`

New count:

`round(default_count * factor)`

For decrease:
- divide by factor.

Preserve hard minimum count `1`.

## 23.4 Probability changes

Per level:

`delta = 0.08 * level`

"more":
- `p_new = min(1, p_default + delta)`

"less":
- `p_new = max(0, p_default - delta)`

For quota probabilities:
- recompute integer quota from `round(p_new*N)`.

## 23.5 Gap changes

Per level:

`factor = 1.15^level`

"more breathing room" / "looser":
- multiply relevant gaps by factor.

"tighter":
- divide relevant gaps by factor.

No requested gap reduction may permit overlap or touching.

## 23.6 "More varied"

Level 2 default action:
- widen continuous numeric ranges around their current midpoint by `20%`,
- keep their midpoint fixed,
- cap at hard bounds already stated,
- flatten discrete weight vectors toward uniform by `20%`,
- do not add entity types,
- do not add collection templates.

---

# 24. Acceptance checklist

A sample is accepted only if all are true.

## 24.1 Scale

```text
chip count ∈ {3,4}
collection count ∈ {15,16,17,18}
all dimensions derive from S
MASTER_SCALE = 1.000 unless user explicitly tuned it
COLLECTION_SCALE = 0.780 unless user explicitly tuned collections
main-chip size bounds pass
collection footprint bounds/median pass
```

## 24.2 Main-chip curves

For every active M5:
- exact quadratic formula from §7.3 used,
- same `g`, `d`, and `kappa` on all four corners of that chip,
- `0.024a <= g <= 0.040a` and `0.054q <= d <= 0.070q`,
- `0.28 <= kappa <= 0.40`,
- no alternate curve family.

## 24.3 Perpendicular stacks

Across active M8 side instances:
- span is sampled from the continuous high-biased distribution in §7.5,
- clear-gap packing is sampled from the continuous tight-biased distribution in §7.5,
- geometry is constructed from the resulting span / pitch / derived-count formulas.

## 24.4 Collection quotas

Exact:
```text
N_ic     = round(0.625*N)
N_dense  = round(0.845*N)
N_border = round(0.700*N)
```

## 24.5 Mini IC

For every IC:
- body dimensions from §12.1,
- terminal sides from §12.2,
- terminal length from §12.3,
- terminal thickness from §12.4,
- terminal count from §12.5.

For arrays:
- exact cell identity,
- array dimensions from §12.6,
- exact terminal-tip contact.

## 24.6 Dense modules

For every dense module:
- dimensions from exact table,
- pitch factor `0.50–0.70`,
- mandatory local border,
- fill algorithm from §13.6.

## 24.7 Collision

All counters from §20 equal zero.

## 24.8 Uniqueness

No duplicate/near-duplicate collection fingerprint exists in the current requested multi-sample batch.

---

# 25. Machine-readable default parameter manifest

```yaml
version: v34-deterministic-portable-local-space-causal-route-first
pathway_extension: route-first-bounded-local-holistic-plus-local-gap

canvas:
  scale_basis: min_width_height_times_main_scale
  canonical_denominator: 1600
  main_scale_default: 1.0
  main_scale_runtime_argument: true
  canvas_dimensions_change_with_main_scale: false
  auto_fit_scale: forbidden

counts:
  chips: {2: 0.90, 3: 0.10}
  collections: {15: 0.20, 16: 0.30, 17: 0.30, 18: 0.20}

main_chip:
  short_side:
    min_S: 0.078
    max_S: 0.105
    driver: mean_of_2_uniforms
  aspect:
    min: 1.20
    max: 1.67
    driver_power: 0.82
  long_side_acceptance_S: [0.110, 0.151]
  orientation: {horizontal: 0.67, vertical: 0.33}
  rounded_probability: 0.85
  rounded_rx_U: [2.1, 2.7]
  motif_complexity:
    driver: mean_of_2_uniforms
    power: 0.90
    integer_formula: 1+min(3,floor(4*c^power))

M5_corner_curve:
  corner_standoff_sqrt_area_fraction: [0.024, 0.040]
  arm_reach_q_fraction: [0.054, 0.070]
  kappa: [0.30, 0.54]
  bezier: quadratic_only

M8_stack:
  span_fraction:
    min: 0.35
    max: 0.90
    driver_power: 0.326
  gap_stroke_multiple:
    min: 1.0
    max: 4.0
    driver_power: 3.82
  hard_min_count: 4

collections:
  scale: 0.780
  placement_spread_preference:
    chip_probability: 0.82
    collection_probability: 0.72
    chip_proposal_batch: 12
    collection_proposal_batch: 8
  complexity:
    driver: mean_of_2_uniforms
    power: 1.50
    integer_formula: 1+min(4,floor(5*c^power))
  ic_fraction: 0.625
  dense_fraction: 0.845
  outer_border_fraction: 0.700
  ordinary_family_weights: {square: 1.0, circle: 1.0, capacitor_circle: 3.9, dot: 1.0, dash: 1.0}

ordinary:
  entity_count:
    min: 2
    max: 7
    driver: mean_of_2_uniforms
  lattice: {orthogonal_strip: 0.35, orthogonal_grid: 0.35, diagonal_grid: 0.20, staggered_grid: 0.10}
  grid_anisotropy:
    min: 1.0
    additive_span: 2.5
    driver_power: 0.80
  dot_radius_U:
    min: 2.1
    max: 5.0
    driver_power: 4.35
  capacitor_circle_radius_U:
    min: 6.3
    max_additive: 13.05
    driver_power: 0.90
  capacitor_circle_mode: {filled: 0.32, hollow: 0.28, concentric: 0.40}
  capacitor_circle_inner_count:
    min: 1
    max: 3
    driver_power: 0.82
  capacitor_circle_collection:
    entity_count: 1
    lattice: forbidden
    repeated_pattern: forbidden
  capacitor_circle_isolated:
    occurrence_probability: 1.00
    count_min: 1
    count_max: 3
    count_driver_power: 1.10

mini_ic:
  short_side_U: [10, 14]
  aspect:
    min: 1.00
    max: 1.85
    driver_power: 0.95
  terminal_length_ratio:
    min: 0.20
    max: 0.40
    driver: mean_of_2_uniforms
  terminal_thickness_q: 0.18
  singleton_probability: 0.10
  multi_connected_probability: 0.91
  connected_dimensions:
    long: {min: 2, max: 6, driver_power: 1.00}
    short_max: 4
    cell_cap: 10
    short_driver_power: 1.00
    transpose_probability: 0.50

dense:
  occurrence_fraction: 0.845
  dimensions:
    long: {min: 3, max: 10, driver_power: 2.00}
    short_max: 4
    cell_cap: 20
    short_driver_power: 1.90
    transpose_probability: 0.50
  orientation:
    orthogonal: 0.50
    stagger_rows_half_step: 0.25
    stagger_columns_half_step: 0.25
  pitch_fraction_of_ordinary: [0.50, 0.70]
  border_required: true

clearance_U:
  chip_chip: 60
  chip_collection_post_route: 42
  collection_collection: 12
  chip_edge: 120
  collection_edge: 20
  collection_local_pre_scale: 3

collision:
  curve_flattening_tolerance_U: 0.25
  prospective_check: required
  final_post_transform_audit: required

batch_uniqueness:
  collection_instance_lifetime: 1
  fingerprint_position_quantization: 0.02
  fingerprint_size_quantization: 0.02
  near_duplicate_rms_position: 0.05
  near_duplicate_rms_size: 0.05

component_fill:
  phase: after_all_pathways
  residual_gap_site_target_fraction: [0.80, 0.90]
  chip_clearance_U: 42
  pathway_clearance_U: 10
  component_clearance_U: 12
  edge_clearance_U: 20
  attachment_probability: 0.24
  attachment_type: isolated_capacitor_to_free_pathway_terminal
  literal_canvas_area_quota: false

pathways:
  planner: route_first_bounded_local_holistic
  supplied_seed_direct: true
  candidate_seed_retries: 0
  route_searches: 0
  direction_count: 8
  max_visible_turn_degrees: 45
  continuous_polyline_required: true
  module_U: [31, 39]
  launch:
    sides_per_chip: 4
    side_coverage_fraction: [0.72, 0.90]
    spacing_U_initial: [4.35, 6.10]
    spacing_U_realized_guard: [4.20, 6.20]
    line_count_hard_bounds: [10, 34]
    shared_trunk_modules_preferred: 2
    shared_trunk_modules_crowded_fallback: 1
  local_gap_phase:
    runs_after_main_network: true
    representative_gap_fill_target_fraction: [0.38, 0.42]
    target_is_soft_best_effort: true
    bounded_coverage_waves_max: 3
    normal_lines_per_root: [3, 4]
    branch_probability_multiplier_vs_normal: [3.0, 5.0]
    branch_targets_uncovered_gap_cells: true
    visible_branch_peel: straight_or_plus_minus_45_selected_by_clearance
    frame_exit_probability_factor: 0.50
    special_trace_population_intent: [0.15, 0.30]
    special_root_members: 1
    special_thickness_multiplier: [5.0, 8.0]
    source_marker: filled_or_hollow_circle
    local_max_rounds: 28
    local_persistence_tail_rounds: 7
    local_reroute_budget: 4
    local_maximum_traceback_gestures: 2
  gestures:
    ordinary_run_modules: [2, 5]
    normal_submodule_segments: forbidden
    terminal_connection_exception: audited
    compensating_zigzag: forbidden
  split:
    initial_cohort_members: [3, 5]
    contiguous_trace_subsets: required
    max_recursive_depth: 3
    child_lateral_order_controls_turn: true
  profile:
    preferred_run_modules: [2, 4]
    turn_appetite: [0.40, 0.64]
    branch_appetite: [0.34, 0.54]
    branch_multiplier: [1.50, 1.80]
    connection_appetite: [0.74, 0.94]
    exit_inclination: [0.25, 0.44]
    max_synchronous_rounds: [40, 48]
    reroute_budget: 7
    maximum_traceback_gestures: 6
    recovery_mode_rounds: 4
    launch_recovery_mode_rounds: 6
    launching_front_variants: 3
    launch_block_failure_threshold_for_reroute: 1
  behavior:
    intentions_are_probabilistic_preferences: true
    realized_output_percentages_are_quotas: false
    physically_impossible_outcomes_may_be_absent: true
  connection:
    proximity_alone_counts_as_success: false
    cross_chip_join: explicit_trace_to_trace_terminal_contact
    young_facing_head_priority_after_gestures: 1
    young_facing_head_priority_max_modules: 5.0
    young_facing_head_join_still_requires_exact_clearance: true
    router_component_approach: forbidden
    post_route_small_component_attachment: rare_terminal_centered_capacitor
  termination:
    marker: filled_or_hollow_circle
    minimum_length_judged_on_shortest_materialized_lane: true
    free_head_extra_path_clearance_U: 4.5
    close_head_resolution: render_time_backoff_before_marker
    bundled_voluntary_termination_multiplier: 0.10
    exhausted_bundle_fragment_probability: 0.90
  overlap:
    ordinary_overlap: forbidden
    collapsed_centerlines: forbidden
    static_object_intersection: forbidden
    explicit_connection_contact_only: allowed
  stroke:
    thin_U: [1.00, 1.55]
    thick_U: [2.5, 3.7]
    thick_member_probability: 0.18
    multiple_thick_same_bundle: very_rare
```

# 27. Pathways

Pathways are generated **after main-chip placement and before every secondary component**. During
main routing the only static board obstacles are the main chips. After that network is frozen, the
local-gap pathway wave is generated against main chips plus the already-routed pathway field. Only
then are collections and isolated components fitted into the residual free space.

Failure to realize a preferred connection, branch, traversal, or escape is a legitimate soft outcome.
There is no router-side collection/component approach intent in the active v29 architecture.

## 27.1 Deterministic probability contract

The supplied sample seed is used directly. There is no pathway candidate-seed stream, accepted
seed list, output quota, pathway-driven board restart, A*, or other destination search.

One seeded profile controls the board's coherent tendencies. Conditional, seeded choices then
select among actions that are physically meaningful at the current bundle front. Probabilities
control attempted behavior; geometry controls what is realized. Realized percentages are report
measurements only and never acceptance conditions.

## 27.2 Routing object and launch

The routing object is a **bundle corridor**, not an individual trace. Each chip emits one broad
side bus from all four sides, perpendicular to the full outer chip bounds. The bus occupies
`80–90%` of its side with `5.90U–8.20U` sampled spacing (realized guard `5.50U–8.40U`) and `9–24`
derived members.

The complete side bus first attempts a two-module shared trunk. If the frame or static occupancy
makes that impossible, it may use an exactly one-module emergence. It then partitions into
contiguous `4–7` member cohorts. Individual lane geometry does not participate in routing.

## 27.3 Modular movement grammar

For each board, sample `M = Uniform(31U,39U)`. Normal corridor gestures are `2–5M` long. The
preferred length (`2–4M`) is part of the board profile.

Every visible direction is horizontal, vertical, or 45-degree diagonal. Consecutive visible
directions may continue or change by exactly `±45°`; larger instantaneous turns are forbidden.
After turning, directional persistence prevents an opposite compensating turn until substantial
travel has occurred.

No normal segment shorter than `M` is permitted. A shorter final alignment is allowed only when
it physically completes an explicit trace-to-trace connection, and it must be reported as a
terminal exception. Repeated compensating sequences such as `NE → SE → NE → SE`, and short
back-and-forth doglegs that merely approximate one direction, are forbidden.

## 27.4 Synchronous conditional gestures

All launch fronts exist before routing begins. Each decision round considers all active fronts
against one shared board state. A front scores only a small action set:

- continue through open space;
- turn left or right by 45 degrees;
- split into contiguous child bundles;
- approach an underused distant region, edge, or foreign network;
- form an explicit connection when contact is naturally available;
- terminate when useful continuation is unavailable.

Proposals are resolved together for that round. A blocked forced turn falls back to a full
two-module straight gesture if available. Other blocked fronts consider at most the neighbouring
45-degree channels; they do not perform microscopic rerouting.

## 27.5 Explicit branching

Branching is a topology operation. Parent members are partitioned into disjoint contiguous
subsets, and the children's lateral order controls which side they peel toward. Children inherit
the already materialized parent lanes, then route independently as bundles to a maximum recursive
depth of three.

A branch preference is not compulsory. If its assigned peel direction is obstructed, the child
may continue as a coherent bundle and reconsider later. Children may never collapse onto one
centerline, exchange lateral order, or silently merge.

## 27.6 Probabilistic best-effort intentions

Bundle intentions are soft inclinations toward exploration, a distant edge, or a foreign-chip
network. Components do not exist spatially during routing and are never route objectives. The
profile samples turn, branch, connection, exit, and outward inclinations from the manifest ranges.
V19 applies an additional seeded `1.50–1.80` multiplier to branch appetite.

An infeasible intention may fall back to another useful gesture. While a front still contains
multiple lanes, ordinary voluntary termination is reduced to roughly one tenth of the singleton
rate; persistent hard stops receive extended traceback/reroute and then preferentially fragment
into independent lanes. There is no minimum required realized fraction for connections, exits,
traversal, or branches, and no generated sample is rejected for missing those outcomes.

## 27.7 Physical connections

Proximity alone never counts as a connection. Multi-member bundles that encounter a foreign
network may split into narrower children. An eligible singleton can form a physical terminal
T-junction with the first foreign-chip trace encountered along its current direction or one legal
45-degree turn. Point-to-point singleton joins are also permitted.

The exact contact point is stored in the connection graph. Only that compact terminal envelope is
excluded from ordinary overlap rejection; every other intersection remains illegal. Connected
traces receive no termination marker.

## 27.8 Corridor conflicts and exact materialization

Accepted geometry from **earlier completed rounds** reserves its full bundle width, but recent history
remains eligible for bounded causal rollback. Same-round proposals are provisional and have no spatial
ownership at all until the round transaction commits.

Every movement round uses the hard parallel-routing invariant from §0.0.1: all fronts propose from one
immutable snapshot; interacting proposal pools form local conflict components; each component must find
one mutually compatible proposal for every participant. If it cannot, the component commits nothing and
causal/local rollback is scheduled. A priority-sorted same-round winner/loser fallback is forbidden.

The actual movement segments selected for the round are batch-written before post-move proximity,
branching, connection, or termination reactions are evaluated. Thus no front may treat an earlier
same-round movement commit as historical geometry.

There is no sequential per-trace routing and no permission to solve a conflict by collapsing lanes. Only
after the bundle forest is complete are corridor centerlines expanded into analytic parallel offset
polylines. Lane spacing and lateral order remain stable through turns. Each member is one continuous SVG
polyline.

## 27.9 Termination, strokes, and audit

True terminations receive a filled or hollow circular marker per trace. Most traces use the thin
stroke range; occasional thick members retain the existing low co-occurrence rule.

The final hard audit requires:

- zero static-object intersections;
- zero unmarked pathway intersections;
- zero collapsed centerline overlap;
- legal visible headings and turn deltas;
- zero compensating micro-zigzags;
- no sub-module normal segments;
- deterministic byte-identical output for the same seed and parameters.

These are bug assertions. Behavioral outcome counts remain descriptive and cannot trigger a
pathway seed retry or board regeneration.

---

# 28. Final implementation rule

A compliant renderer does not "interpret the look."

It:
1. reads the parameter manifest,
2. executes the algorithms,
3. samples only from the listed distributions,
4. performs the listed permutations,
5. runs the numeric validation,
6. rejects invalid outputs.

Anything not numerically authorized by this document is not part of the v17 static / v16 pathway
design language. Earlier v8–v12.1 pathway tuning prose is historical only; where it conflicts with
Section 27, Section 27 controls.

### V20 pathway implementation refinement

The active v19 pathway tendencies are further refined as follows: after roughly 60% of a front's originally sampled gesture lifespan (and at least five accepted gestures), its effective branching probability is multiplied by 1.50. Ordinary trace gauge is 2.00–3.10U with rare 5.0–7.4U emphasis traces, and launch pitch must preserve approximately 1.5× adjacent-mean-thickness edge gaps while retaining the existing 70–90% chip-body-side occupancy target. Foreign static routing keepout is 8U.

Trace-to-trace connectivity is head-to-head only. A trace may participate in at most one physical trace connection. Mid-segment attachment is forbidden. Compatible free cross-chip lane heads within 1.90 pathway modules receive deterministic connection priority, including safe lane peel-out from a broader cohort after exact terminal geometry validation. Any parent whose lane peels away receives a traceback floor at the shared prefix. Rendered involuntary terminal stubs below 2.75 pathway modules are forbidden. Unmarked centerline crossings, collapsed/duplicated lines, unmarked thick-stroke overlap/touch, mid-line connections, and multiply-connected traces are hard failures.

### V21 pathway implementation refinement

V21 retains the V20 synchronous / holistic route planner.  Termination marker radius is multiplied
by 2.0 relative to V20; hollow marker stroke is 2.70U.  Bundle lane pitch must satisfy both the
existing >=1.5× adjacent-mean-line-thickness visible edge gap and sufficient separation for the
outer edges of two adjacent hollow V21 termination markers plus 1U.  A hollow terminal trace stops
at the marker's outer border rather than entering the hollow interior.

The ordinary secondary/static pathway keepout remains 8U, while every main-chip body receives a
24U pathway keepout after the initial source-chip emergence gesture.  The 170U chip-secondary
placement moat is unchanged.

Normal pathway branching may continue to depth 5.  Multi-trace journey-limit and exhausted-hard-stop
termination are approximately 97% suppressed in favour of continued travel, branching, traceback,
escape, or recovery fragmentation.  Recovery-fragment singleton lanes are isolation-locked and may
not terminate while still embedded in their parent bus; specifically, a singleton terminal point
between continuing same-root lanes on both lateral sides is forbidden.  A 12-round persistence tail
is available after the normal planning horizon.  If all legal movement is exhausted, persistence
lanes are finalized coordinately rather than silently removed.

All V20 hard geometry invariants continue to apply: head-to-head trace joins only, one trace-to-trace
connection per trace, no mid-line joins, no unmarked centreline or thick-stroke intersections/touches,
no doubled traces, no tiny involuntary stubs, and no compensating zig-zag repair legs.


### V22 pathway implementation refinement

V22 retains all V21 hard geometry and visual rules but changes the pathway **decision architecture**.
Normal open-space movement remains the cheap seeded bundle-gesture fast path. A 40×40 congestion field and
bounded short-horizon future checks activate only for `LAUNCHING`, `STRUCTURAL_TRANSITION`,
`CONNECTION_PENDING`, `RECOVERING`, failed, or locally congested fronts. Nearby competing futures are
placed into a temporary conflict group through a spatial broad phase; no more than a tiny fixed set of
fronts/candidates is jointly evaluated. There is no global route search, A*, or full-board routing retry.

Launch fans and ordinary branches are transactional topology operations: children are committed only after
a legal short structural future exists. Fan birth may choose among a tiny bounded permutation of non-
crossing straight / ±45° child maneuvers rather than insisting on one decorative fan that geometry cannot
realize. A head-to-head connection may detach only an exposed **outer** lane of a live cohort. Interior
lanes must first become exposed by a real contiguous branch. Detached shared prefixes remain traceback-
locked.

Close compatible free heads receive deterministic connection priority when a legal physical join exists.
Same-chip ancestry is not itself a reason to refuse an obvious free-head join. Final marker arbitration may
perform bounded local blocker negotiation: only the unrelated terminal blocker's local tail is reopened,
the head pair is joined, then the blocker receives a bounded escape attempt. Mid-line joins remain
forbidden and each trace may still participate in at most one trace connection.

The acceptance model is explicitly split:

- **Hard invariants:** no forbidden static/path intersection or thick-stroke touch, no doubled/collapsed
  trace, no mid-line or multiple trace connection, no compensating zig-zag, no overlapping termination
  marker, no keepout violation, and no visible involuntary terminal stub below 2.75 pathway modules.
- **Soft best-effort tendencies:** the sampled 72–90% launch-span intent, connection frequency, branch
  realization, path travel/coverage, frame exits, and bundled-termination suppression. These values are
  measured and may fall short when the board geometry cannot realize them. They never justify violating a
  hard rule, regenerating the static board, or performing unbounded search.

Consequently, final materialization may suppress a failed tiny speculative route even when doing so leaves
the realized visible launch span below the nominal launch intent.


### V23 local-gap pathway and capacitor refinement

V23 keeps all V22 hard pathway invariants and the hard-vs-soft outcome policy. Main-chip routing completes first. A sparse second phase then samples candidate source positions from residual free space and starts a small number of local routing roots. Local roots are not attached to a main chip and therefore treat every static object and all previously routed main traces as foreign obstacles. They use the same bounded local holistic movement/branch/connection/recovery grammar, but a shorter horizon preserves their local gap-filling character.

The local-gap phase is explicitly non-quota-driven: it should attempt to enrich empty regions without filling every hole or rejecting a legal board because a local source failed. Ordinary local roots contain 2–5 traces. A probabilistic 5–10% share of the planned local trace population is represented by singleton special roots with 5–8× ordinary trace thickness. Special roots never spawn as bundles.

Every visible pathway trace now has a source marker as well as any applicable terminal marker. Hollow source and terminal markers clip the polyline to the outer stroke boundary, so the trace never visibly passes through the hollow center.

Capacitor occurrence is increased by 3× relative to V22: collection sampling weight is 3.90, and the independent isolated occurrence probability saturates at 1.00. Capacitor size span is widened by 50% by changing the continuous radius expression from `(4.2 + 5.8*R^0.90)U` to `(4.2 + 8.7*R^0.90)U`.


### V24 local-gap density, breakup, thick caps, and source spacing

V24 keeps every V22/V23 hard routing invariant and the hard-vs-soft outcome policy. The local-gap phase searches a denser residual candidate grid and normally attempts 6–7 ordinary 3–4-trace roots plus seeded special singleton roots. Local roots keep their local identity through child creation and recovery, receive a 1.90× branch boost, an earlier local late-life branch phase, and may first split into narrower parallel contiguous cohorts before those cohorts independently turn. This makes gap fillers disband readily without weakening transactional birth or collision checks.

The special local type's seeded soft probability is 15–30% (3× V23's 5–10% range). Special traces remain singleton-only and 5–8× ordinary thickness. Their line geometry is round-capped; a background-coloured negative circle hollows the source cap and any free terminal cap. Separate ordinary endpoint dots are not used for this type.

Main-chip emitting trace source points are offset 22.5U from the chip perimeter, three times the V23 7.5U gap. Capacitor rules remain those established by V23: 3× occurrence weighting and +50% continuous size span. Verification runtime budgets scale linearly with requested sample count; this is external execution budgeting, not a reason to expand the bounded routing search with trace population.


### V28 route-first architecture, residual component fill, and independent main scale

The V28 architecture changed the generation dependency graph rather than adding more routing intelligence. Main chips
are generated and placed first. The complete main-chip network is then routed while the board is
otherwise empty. The existing local-gap pathway wave runs second against the frozen main network. Only
after both pathway phases are complete are collections and isolated capacitors generated and fitted to
the remaining free field.

Consequences:

- secondary components are removed from the pathway static-obstacle set;
- pathway component intent/approach is removed;
- the historical 170U chip-secondary moat, whose routing purpose was to reserve launch room before
  component placement, is superseded by a 42U post-route visual chip clearance plus exact 10U
  component-to-pathway clearance;
- residual component placement targets seeded 80–90% coverage of representative residual gap sites;
- rare line-to-small-component relationships are created by attaching an isolated capacitor to an
  eligible free terminal after routing, never by routing toward a component;
- component-placement failure must be handled by bounded component-only recovery on the frozen route
  network. It must not trigger a new pathway pass; if bounded recovery cannot realize the static-language
  component population, the logical sample may be rejected by the outer batch policy.

The V28 architecture also made `MASTER_SCALE` an explicit positive runtime argument (`main_scale`, CLI
`--main-scale`) with default `1.0`. Canvas width/height remain fixed; all design-language geometry
that derives from `S` or `U` scales by this multiplier. The renderer never changes it automatically.

### Active V29 routing-space refinement

V29 keeps the v28 route-first dependency graph and does not restore any secondary-component routing
obstacles. It changes only the active pathway/component behavior that becomes possible once routing has
first claim on the board:

- a launching front that is blocked after emergence enters bounded recovery after its first failed
  movement rather than spending several rounds dying in place; launching fronts evaluate three bounded
  proposal variants and receive six recovery-mode rounds, while the global reroute budget remains bounded;
- close, facing young heads from different chips receive deterministic head-to-head connection priority out to
  `5.0` routing modules when the exact join is collision-clean. This is an arbitration shortcut, not a route
  search: it prevents two newly emerged networks from spending recovery budget merely blocking each other;
- terminal survival is judged from the shortest actually materialized lane in a bundle rather than the bundle
  centreline alone, so an inside lane shortened by a turn cannot be mistaken for a sufficiently long terminal;
- local-gap routing samples a representative residual-gap field after the main network freezes and targets
  `Uniform(0.38, 0.42)` of those open cells. Up to three bounded waves may be launched, with later waves
  sized from the measured coverage deficit; this is a soft composition target, never permission to violate
  geometry or perform global search;
- local bundles are `3–5×` as likely to branch as comparable main bundles. A local split must try to peel
  visibly by `±45°` toward uncovered cells in the gap it occupies, with a straight continuation used only
  when the preferred peel is not legal;
- local fronts have half the ordinary post-emergence frame-exit permission. Near the frame, legal interior
  pivots and uncovered-gap targets are preferred; the persistence tail does not forcibly convert local
  bundles to exit intent;
- local recovery is intentionally cheaper than main recovery: at most four reroute attempts and at most two
  traceback gestures per attempt, because another branch/pivot or later coverage wave is preferred to deep
  local search;
- a free terminal head must visually clear foreign pathway geometry by an additional `4.5U`. If necessary,
  the frozen terminal polyline is backed off at materialization before its endpoint marker is placed; this is
  a render-time trim, not another routing/recovery search;
- capacitor radius is shifted upward by 50% across the whole active continuous range:
  `r = (6.3 + 13.05*R^0.90)U`, i.e. `1.5×` the V28 radius expression at every sampled `R`;
- after local routing is frozen, residual component placement targets `80–90%` of the remaining representative
  component gap sites.

These refinements preserve the deterministic/probabilistic/variance-driven/conditional/permutational contract
and all existing hard no-intersection/no-collapse/no-zigzag invariants.



### Active V30 runtime/dependency correction

V30 is a runtime/dependency correction to the V29 visual behavior. It does not reduce the V29 local-gap
coverage, branching, exit, terminal-clearance, capacitor-scale, or residual component-fill targets.

Normative execution rules:

- component template generation, calibration, quota/coverage checks, dense-shape balance, IC-contact checks,
  and cross-sample uniqueness checks occur before `generate_pathways()` whenever those checks are independent
  of final XY placement; these templates are non-spatial and are never inserted into pathway occupancy;
- the residual component filler must precompute chip and pathway keepout unions once per placement attempt and
  reuse them for every candidate, including whole-field fallback candidates; rebuilding the complete routed
  keepout geometry inside a candidate loop is forbidden;
- after main and local pathways are frozen, component placement may retry deterministic layouts and may prepare
  bounded alternate component populations against the same frozen routes; these retries must never invoke route
  traceback, route regeneration, or a fresh pathway pass;
- a post-route component failure is not permission to internally reroute the same logical sample. Outer batch
  deadlock/skip policy remains the only mechanism that may advance to another logical sample;
- default execution (`count=1`, no seed, `main_scale=1.0`, default retry/calibration budgets) is a supported
  production path and must not depend on benchmark seeds or user-supplied tuning to complete;
- elapsed wall-clock time must never affect seeded geometry or branching decisions. Runtime protection is achieved
  by bounded work and dependency ordering, not by time-based visual degradation.

Successful reports expose `component_templates_prepared_before_routing=true` and
`route_restarted_for_component_failure=false`.

### V34 local-space causal routing, scale, and fill correction

V34 retains the V31 transactional-parallel core, V32 source-egress protection, and V33 connected-region fill architecture, but supersedes their active tuning/acceptance rules where stated below:

- **Whole-design default scale is reduced to canvas/1600.** The effective design basis is `S_canvas * MASTER_SCALE * 0.75`, so S-derived chips/collections and U-derived traces, strokes, clearances, routing modules, capacitors, and other geometry shrink together. `chip_count()` remains exactly `{2: 0.90, 3: 0.10}` and therefore does not fall with the smaller geometry.
- **Main-chip spacing is canvas-protective, not merely scale-proportional.** Pair clearance is `max(360U, 0.205*S_canvas)`. At the default 1200 square and `MASTER_SCALE=1`, this is 270 canvas units. A chip arrangement that cannot provide viable emitted-side egress is invalid.
- **Spacing is preventative, not a substitute for routing.** Every main route ranks its bounded legal candidate corridors using measured local free-space/capacity from the maintained congestion field. Immediate segment legality alone is insufficient when a materially more open local corridor exists.
- **Deadlock requires genuine causal rollback/re-route.** Recovery may rewind multiple committed gestures (up to the bounded recovery depth), including to the emergence anchor where allowed. The direction that actually left the rollback junction into the failed historical corridor is recorded as the replay direction and deprioritized/blacklisted during the recovery window. Recovery considers the other legal ±45° corridor(s) from the rollback point; a rewind followed by replay of the same failed corridor is not considered a successful reroute.
- **Foreign causal blockers may yield.** A young main launch cannot be killed merely because an older route has spent its ordinary reroute budget. Causal yield has a separate bounded allowance, and local conflict transactions may rewind the blocker, blocked route, or both.
- **Usable local space prevents cheap termination.** Before ordinary hard-stop/journey/round-limit termination of a main route, bounded local-capacity probes may defer termination and request a different corridor. This remains local/grid-ranked with exact geometry as final legality; V34 does not introduce A*, full-board search, or global route permutations.
- **Physical-lane grammar is authoritative.** Candidate reversal turns that risk an offset-lane compensating kink are checked against materialized tail geometry including inherited branch/fan prefixes. A route may not be accepted on a legal centerline if one visible lane would later need to be deleted.
- **Pathway bodies are straight-segment-only.** Consecutive pathway headings may differ only by `0` or `±45°`; a direct 90° turn is a hard invalidity. Pathway primitives may not use quadratic/Bézier geometry. Mitered polylines are required for bends; round terminal caps do not authorize curved route bodies.
- **Main-network preflight is fail-fast and reparative.** Before any local-gap/component work, materialized main lanes are audited. A late predicted zigzag/intersection identifies its owning leaf; V34 reopens it, causally rolls back recent history, blocks replay of the failed corridor, and performs a bounded local regrowth. If the repair cannot satisfy the physical-lane grammar, the logical sample is rejected before filler work.
- **Local gap lines do their own job.** The residual field is measured as connected regions on a `28×28` grid. Ordinary local sources are independent singleton lines. Region size/unmet area controls source capacity, route lifetime, target direction and stroke scale. The sampled internal target is `Uniform(0.42,0.50)` to maintain a hard accepted visual floor of about 40%; components may not compensate for local-line underfill.
- **Local interaction remains emergent.** Compatible independent local lines in the same region have a deterministic 50% chance to align temporarily for 2–4 atomic rounds, at most once per line, then separate and resume independent space-seeking. Local branching keeps the 3–5× boost and local frame-exit permission remains 50% of main behavior.
- **Residual components are independently space-aware.** A connected `28×28` residual-region field is evaluated after all routes freeze. Large established collections are attempted in rooms with matching capacity; bounded small gap-matched fillers serve remaining pockets. Accepted component visual-service coverage is at least 90% (seeded target 90–94%), and no component/path overlap is authorized except the explicit terminal attachment.
- **Hard overlap invariants remain exact.** Unauthorized line-line/stroke, line-chip, and component-path intersections are rejection conditions. Components never exist spatially during routing and never cause rerouting.

The V34 intent is not "more retries." It is: prevent obviously hostile chip layouts, reason about bounded local space while moving, rewind the causal decision when a deadlock nevertheless occurs, and make both residual filler phases independently accountable for their requested coverage.

### V33 space-aware routing and residual-fill rebalance (historical baseline retained where not superseded)

V33 retains the V31 transactional-parallel core and all V32 source-egress/family-survival invariants,
but rebalances board composition and replaces coarse global fill heuristics with connected-region
reasoning. These rules are a historical baseline retained only where V34 does not supersede them; their original V33 numeric values remain recorded below for history:

- main-chip pairs use a `210U` geometric clearance target during placement, with chip placement spread
  strongly preferred so one chip cannot casually consume another chip's launch territory;
- accepted multi-chip boards must contain at least one true cross-chip pathway connection; connection
  appetite and bounded post-main terminal pairing are restored without weakening source-egress survival;
- an entire emitted chip side may not be accepted as a set of short corpses: `pathway_main_stalled_side_count`
  must be zero, all launched main lanes must remain visible, and hard overlap/intersection cleanup may not
  silently remove a main lane;
- local-gap space is analyzed as connected regions on a `24×24` residual field with measured area,
  spans, center, size class, and principal orientation;
- the local pathway target is `Uniform(0.40, 0.50)` of the residual gap influence field, with a small
  bounded overshoot allowed when the final useful line claims an indivisible ribbon;
- ordinary local fillers are born as **independent singleton lines**, never pre-bundled. Region size and
  unmet area determine how many sources a gap receives, and region size controls useful lifetime/stroke
  scale so small gaps receive short/small activity while large rooms receive more varied activity;
- two independent local singleton lines in the same gap with compatible headings have a deterministic
  50% chance to form a temporary parallel affinity for 2–4 atomic rounds. Each line may bundle at most
  once, then releases and resumes independent gap-seeking/branching;
- per-region capacity/unmet-area weighting prevents one large gap from monopolizing all local sources;
- local branching remains 3–5× more likely than comparable main routing and targets uncovered cells in
  the same measured gap; local frame-exit permission remains 50% of ordinary main behavior;
- component placement uses the connected-region process in §19.3 and targets 90–94% served residual-region
  area with bounded gap-sized mop-up fillers;
- unauthorized line–line/stroke and component–pathway overlaps are hard acceptance failures. Safety cleanup
  may remove optional local filler geometry, but accepted main routing may not depend on such cleanup.
- batch generation defaults to one full sample attempt per logical index before deterministic skip, so an impossible protected-routing topology cannot multiply expensive whole-board reroutes; explicit retry overrides remain available.

The intent is compositional: main routes establish the skeleton, independent local traces articulate roughly
40–50% of the leftover routing space, and components adapt to roughly 90% of the field remaining after those
local traces. Fill behavior is conditional on the measured shape/capacity of each local gap, not on reusable
canvas coordinates or a global source count.

### V31 transactional-parallel routing baseline (retained by V34)

V31 keeps the V30 route-first dependency graph, V29 local-gap/component behavior, and bounded-runtime
component recovery. It changes the semantics of pathway movement and recovery so the long-standing
parallel-generation requirement is enforced rather than approximated.

- pending traceback is executed for all ready fronts before a movement-round snapshot is taken;
- all movement proposals are generated against that same snapshot;
- every pair of proposal pools that can interact is placed into one local conflict component, not only
  fronts already tagged for holistic handling;
- each conflict component is solved as a complete deterministic assignment over bounded alternatives;
- if no full assignment exists, no participant in that component moves during the round; causal rollback
  is scheduled instead of accepting a priority-sorted winner;
- mixed conflicts involving a root main-chip launch first rewind the non-young participants; all-young or
  all-normal unresolved groups are repaired symmetrically;
- root main-chip recovery floors are zero post-emergence until explicitly locked by shared/connected
  geometry, allowing true rollback to the launch anchor;
- young blocked launches may request rollback from the active foreign route whose recently committed
  geometry is actually blocking their forward corridor;
- accepted movement segments are written as one atomic batch before post-move proximity/branch/terminal
  reactions run, so no front observes an earlier same-round movement as historical geometry;
- the renderer exposes `pathway_planner_mode=route_first_family_protected_transactional_parallel` and reports atomic-round,
  conflict-deferral, causal-blocker, and root-emergence traceback diagnostics.

This section remains the transactional baseline for V33. The V33 source-egress/family-survival rules in §0.0.2
are the current strengthening and supersede any older termination/recovery behavior that conflicts with them.
Earlier V16–V30 descriptions remain historical context and do not override the hard invariants above.

