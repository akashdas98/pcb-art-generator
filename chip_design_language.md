# PCB Graphic Design Language — v48 Deterministic Portable — Seed-Total Constructive Generation

## 0. Status and normative contract

This is the **single authoritative, context-independent specification** for the active v48
main-route-first board language and its deterministic bundle-gesture pathway system.

### 0.0 Document identity and maintenance contract

```yaml
canonical_filename: chip_design_language.md
active_design_language_version: v48
version_location: document_metadata_not_filename
```

The canonical filename is intentionally version-neutral. The active version is recorded in this document so the
authority path remains stable across releases.

Every repository session must read `AGENTS.md`, `CONTEXT.md`, and this complete specification before making a
change. Every repository change must update this specification in the same change. Updates must preserve this
document's established structure: numbered normative sections, explicit numeric rules, the machine-readable
manifest where applicable, and versioned historical refinements. A change may not weaken or bypass an established
hard invariant merely to make an implementation or test pass.

It consolidates:
- cumulative m1–m17 / v17 behavior,
- the portable scale calibration,
- the later corrections for curve geometry, overlap, multi-sample reuse, perpendicular-stack density/coverage, collection-border frequency, and mini-IC terminal length.

The active generation order is normative and hierarchical:

1. generate and place main chips;
2. route and freeze the complete main-chip pathway network against main chips only;
3. analyze the post-main residual field and place gap-aware components to a seeded **50–60%** service target;
4. freeze those components;
5. route local residual-gap lines through the actual remaining free field, treating both the main network and components as immutable obstacles, to a seeded **80–90% of the remaining service budget** target;
6. perform final exact pathway/component/marker/clearance audits.

Components never exist spatially during **main-chip routing** and therefore can never block, steer, terminate,
or trigger recovery in the main router. In V39 they intentionally do exist before the local-gap phase, and
local fillers must route around them with the same exact component/pathway moat. No residual-fill failure may
reroute the frozen main network, and local routing may not move or resize an already accepted component.

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
S = S_canvas * MASTER_SCALE
U = S / 1600 = S_canvas * MASTER_SCALE / 1600
```

`W` and `H` define the unchanged canvas. `S` remains the canvas-relative basis used by S-derived geometry;
`U` is the finer construction unit and is now exactly `S/1600`. There is **no additional 0.75 multiplier**.
Therefore changing `MASTER_SCALE` still scales both S-derived and U-derived geometry together, while the
default `MASTER_SCALE=1` keeps `S=S_canvas` and only the unit denominator is 1600.

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

## 3.1 Main-chip population — aspect-invariant spatial stationarity

Entity scale and population extent are separate quantities.

Let the normalized raw-canvas territory and logical design territory be:

```text
short = min(W,H)
T_canvas  = (W*H)/(short*short) = max(W,H)/min(W,H)
T_logical = T_canvas / main_scale^2
full = floor(T_logical)
frac = T_logical - full
```

One complete logical territory contributes **exactly two main-chip opportunities**. Every complete additional logical
territory contributes the same two opportunities. In the fractional final territory, each of its two opportunities is
independently realized with probability `frac`.

Therefore:
- at `main_scale=1`, every square canvas at any absolute SVG size has exactly two main chips;
- reducing `main_scale` is a true zoom-out and exposes more logical board area on the same SVG;
- on a square at `main_scale=0.5`, `T_logical=4` and there are exactly eight main-chip opportunities;
- rotating a canvas at the same `main_scale` cannot change the chip-count distribution;
- expected chip count is `2*T_logical`.

This is not tiling. Placement remains one global deterministic composition with the existing spread/clearance rules;
`T_logical` only defines how many statistically identical population opportunities the visible logical board contains.

## 3.2 Prepared-collection population

The historical square-territory collection distribution remains:

| Count | Probability |
|---:|---:|
| 15 | `0.20` |
| 16 | `0.30` |
| 17 | `0.30` |
| 18 | `0.20` |

Each complete normalized territory receives one independent draw from this distribution.  A fractional final territory
receives an independent draw whose individual collection opportunities are retained with probability `frac`.
Consequently collection-language density and family/quota composition remain stationary per unit territory on square,
portrait, and landscape canvases.  `MASTER_SCALE` does not affect this population law.

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

## 19.2 Main pathways before residual objects

After main chips are accepted, execute the **main-chip portion** of Section 27 completely before any
secondary component receives a canvas position. During this phase the only static board objects are the
main chips. The complete main network is preflight-materialized, repaired if necessary, hard-audited, and
then frozen.

No later component or local-gap failure may cause this frozen main network to reroute.

### 19.2.1 Residual density controls

Two public controls govern only the **post-MAIN residual phases**:

```text
D_local     = local_density     in [0, 1], default 1.0
D_component = component_density in [0, 1], default 0.5898123324396783
```

The nominal component default is the historical midpoint-convention share:

```text
C_mid = 0.55
L_mid = 0.85
D_component_default = C_mid / (C_mid + (1-C_mid)*L_mid)
                    = 0.5898123324396783
```

For each seed, the legacy residual convention still defines its own seeded reference budget:

```text
C0 = Uniform(0.50, 0.60)
L0 = Uniform(0.80, 0.90)
T0 = C0 + (1-C0)*L0
```

At the **exact default pair** (`D_local=1`, `D_component=0.5898123324396783`) the renderer takes a legacy fast path: it uses `C0` and `(1-C0)*L0` exactly, preserving the pre-knob default geometry/RNG behavior. The numeric component-density default is therefore the nominal midpoint share, not a claim that every historical seed had one fixed component share.

Away from the exact defaults:

```text
T_target         = D_local * T0
C_target         = T_target * D_component
A_local_budget   = T_target * (1-D_component)
```

Consequences are literal at the allocation level:

- `D_local=0`: leave the post-MAIN residual field empty — no residual components and no LOCAL lines;
- `D_component=0`: allocate the requested residual-fill budget to LOCAL lines and emit no residual components;
- `D_component=1`: allocate it to components and assign no residual-fill budget to LOCAL lines;
- intermediate values split one common total budget rather than independently multiplying two unrelated phase targets.

These controls change **density targets, not geometry law**. Existing component grammar, LOCAL grammar, clearances, octilinear routing, frozen-MAIN ordering, and exact legality remain authoritative. At extreme allocations the requested density may be physically under-realized; the renderer must not relax clearance or invent a new routing algorithm merely to hit a knob. Historical hard floors are scaled downward with reduced density and are capped at their established legacy maxima when a knob requests more work, so a high-density endpoint does not create a new superlinear 90%+ construction invariant. Embedded report fields expose both requested and actual combined residual service and the realized component share.

## 19.3 First residual phase — connected-region component fill

After the main network is frozen:

1. use the established deterministic component population and substantial-region classifier;
2. derive the component residual-service target from the residual-density controls in §19.2.1. At the exact defaults this is the historical seeded draw `Uniform(0.50, 0.60)`; away from default it is the component share of the scaled combined post-MAIN residual budget;
3. analyze the residual field after exact main-chip and main-pathway keepouts;
4. classify substantial/mandatory versus optional thin/sliver residual regions;
5. allocate component capacity by region size and usable short/long span: small rooms prefer small components,
   medium rooms medium assemblies, and large rooms require larger and/or multiple component-capacity units;
6. **coherent collection language is primary.** Once the prepared full collections are placed, any additional
   component capacity required in a medium or large connected room must first be supplied by a coherent compound
   assembly made from at least two established entity families (ordinary pad/dot/dash families, capacitor, IC,
   dense-dot subgroup), with an outer collection border strongly preferred and increasingly likely with room size;
7. standalone dot/dash/square/circle tokens are **micro-pocket-only**. They may be generated only for a connected
   region classified as genuinely micro by its region short-span/cell capacity, never merely because one chosen
   cell inside a large room has poor local clearance. A sample-wide micro-token cap prevents confetti from becoming
   the dominant component language;
8. local clearance may select a better placement point or reject one candidate, but it may not crush a medium/large
   compound assembly below 72% of its generated residual-instance scale. If that much shrink would be required,
   search another location/room instead;
9. the historical bounded 90%→82%→75% adaptation remains available for the original prepared full collections;
   source collection language/quota validation is performed before routing and is not redefined by fit-only adaptation;
10. exact chip/main-path/component-component/edge clearances remain authoritative;
11. once the active component service obligation is met (historical seeded 50–60% at exact defaults), freeze all accepted components.

The governing service metric remains the V35 substantial-region **area representation × size/quantity capacity**
metric. One token object cannot satisfy a large room, and medium/large rooms may not be serviced visually by a
field of disconnected micro-primitives. Tiny/sliver fragments are not allowed to hold the board hostage. A
component-placement failure may regenerate/retry only component templates or placements against the same frozen
main network; it may never rerun main routing.

## 19.4 Second residual phase — local lines over the remaining service budget

After components freeze, derive the LOCAL absolute target from the residual-density controls in §19.2.1. At the exact defaults the historical rule is preserved exactly:

```text
L_target = Uniform(0.80, 0.90)
R = max(0, 1 - C_actual)
A_local_target = R * L_target
```

Away from the exact defaults, `A_local_target` is the remaining LOCAL allocation of the common post-MAIN residual budget after accepted component service, capped so component overshoot cannot make the combined residual service exceed the requested total. Component under-realization is not silently reassigned to LOCAL because `component_density` owns the modality split.

The local planner then analyzes and routes through the **actual physical post-component free geometry**. It must:

- treat main pathways and all accepted components as immutable obstacles;
- preserve the V35 independent singleton birth rule;
- preserve deterministic 50% temporary compatible-line bundling, at most once per line, followed by release;
- preserve the 3–5× local branching tendency and reduced frame-exit behavior;
- select line lengths/source quantities from measured gap size and usable span;
- treat a long open corridor as room to **articulate**, not as permission for a ruler-straight start-to-end filler:
  each local front samples a deterministic 1–3-gesture straight-run allowance, after which a legal `±45°` turn
  receives a strong preference while geometry/clearance remains authoritative;
- keep target attraction weaker than main-route target following so a local front explores the room instead of
  beelining to one sampled cell; a two-gesture post-turn cooldown prevents compensating zigzag/twitch behavior;
- make the bounded final service pass **bent-first**: ordinary mop-up fillers must contain a mid-body `±45°`
  pivot and may then extend through additional legal gestures. A pure straight mop-up is exceptional, allowed only
  for a measured genuinely narrow pocket and under a small board-level cap; fragmented residual rescue is bent-only;
- bound stochastic retry **per unchanged direct-mop-up run family**, not per board: one residual corridor family
  receives at most **3** stochastic realizations (initial attempt plus two retries) during one direct-mop-up call.
  Larger logical territory may create more independent run families, but may not increase retry opportunity for the
  same unchanged family. Once that local budget is exhausted, the family leaves the current candidate pool; every
  admitted realization still passes the ordinary exact source/gesture/clearance predicates;
- count only visible line stroke plus its legitimate exclusion/spacing perimeter as service;
- preserve thickness-aware local-to-local, main-to-local, and component-to-local clearances;
- permit bounded endpoint-marker backoff only along the line's already legal path when required to keep the final
  dot outside a component moat;
- enforce straight-segment pathway bodies with only 0/±45° heading changes. A direct 90° turn is rejected at
  proposal/commit, checked again from the actual rendered polyline tail, and remains a hard failure in the final
  materialized audit. Curved pathway primitives are forbidden.

The reported normalized local result is:

```text
L_actual = A_local_actual / R
```

and an accepted board targets roughly 80–90% of the remaining service budget. The final 10–20% may remain
intentional negative space, especially in thin, triangular, isolated, or otherwise awkward pockets.

## 19.5 Isolated capacitor-circle entities and reversed pathway attachment

Isolated capacitor-circle entities remain independent secondary placement sets. In V36 they participate in
the same **post-main / pre-local** component phase as collections and retain `12U` component-to-component
clearance.

Rare pathway-to-small-component relationships are created **in reverse** against the already-frozen **main**
network: an eligible free main-pathway terminal may receive an isolated capacitor centered on that terminal.
The component adapts to the main pathway; the main pathway never searches for or approaches a future component.
The component is then frozen and becomes a real obstacle for local-gap routing. Only the designated main-terminal
contact region is exempt from the normal `10U` component-to-pathway clearance. The component must still satisfy
frame, chip, other-component, and all non-designated pathway clearances.

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
chip count satisfies the normalized-territory rule in §3.1; every square canvas must equal 2
prepared collection count satisfies the stationary per-territory projection in §3.2
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
version: v43-deterministic-portable-aspect-invariant-spatial-population
pathway_extension: main-route-first-component-first-residual-plus-local-gap-completion

canvas:
  scale_basis: min_width_height_times_main_scale
  canonical_denominator: 1600
  main_scale_default: 1.0
  main_scale_runtime_argument: true
  canvas_dimensions_change_with_main_scale: false
  auto_fit_scale: forbidden

population:
  normalized_territory: "T = (W*H)/min(W,H)^2 = max(W,H)/min(W,H)"
  rotation_invariant: true
  main_scale_affects_population: false
counts:
  chips: "2 per complete normalized territory; each of 2 fractional-territory opportunities retained independently with probability frac(T)"
  collections_square_territory: {15: 0.20, 16: 0.30, 17: 0.30, 18: 0.20}
  collections_extended: "independent square-territory draws plus itemwise fractional-territory thinning"
  isolated_capacitors_extended: "historical 1-3 batch opportunity per normalized territory"

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
  chip_chip: "max(430U, 0.265*S_canvas)"
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
  phase: after_frozen_main_before_local_gap
  residual_density_controls:
    local_density: {range: [0.0, 1.0], default: 1.0}
    component_density: {range: [0.0, 1.0], default: 0.5898123324396783}
    component_density_default_basis: "0.55 / (0.55 + (1-0.55)*0.85)"
    exact_default_preserves_legacy_seeded_targets: true
  residual_service_target_fraction_at_exact_default: [0.50, 0.60]
  substantial_region_size_quantity_capacity: required
  optional_sliver_regions: permitted_negative_space
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
    runs_after_components: true
    components_and_main_network_are_immutable_obstacles: true
    remaining_service_target_fraction_at_exact_default: [0.80, 0.90]
    absolute_target_formula_at_exact_default: "(1-component_service_actual) * sampled_remaining_target"
    nondefault_budget_formula: "T=D_local*T0; C=T*D_component; LOCAL=T-C after component overshoot cap"
    visible_stroke_plus_legitimate_perimeter_service_only: true
    target_is_hard_acceptance_with_small_numeric_tolerance: true
    bounded_coverage_waves_max: 3
    birth_mode: independent_singleton
    branch_probability_multiplier_vs_normal: [3.0, 5.0]
    branch_targets_uncovered_gap_cells: true
    visible_branch_peel: straight_or_plus_minus_45_selected_by_clearance
    target_following_role: weak_region_attraction_not_beeline
    seeded_straight_run_allowance_gestures: [1, 3]
    overdue_turn_preference: strong_soft_plus_or_minus_45
    post_turn_cooldown_gestures: 2
    final_service_mopup: bent_midbody_plus_or_minus_45_first
    direct_mopup_run_family_attempt_cap: 3
    direct_mopup_retry_scope: unchanged_run_family_within_one_direct_mopup_call
    straight_mopup_exception: genuinely_narrow_pocket_only_and_board_level_capped
    fragmented_residual_rescue: bent_only_dogleg
    direct_90_degree_turn: hard_forbidden_at_proposal_commit_render_tail_and_final_audit
    release_regression_straight_visible_trace_fraction_max: 0.20
    frame_exit_probability_factor: 0.50
    special_trace_population_intent: [0.15, 0.30]
    special_root_members: 1
    special_thickness_multiplier: [5.0, 8.0]
    source_marker: filled_or_hollow_circle
    local_max_rounds: 12
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

### V36 component-first residual fill and local-line completion

V36 inherits V35's `S/1600` scale, canvas-gated main-chip population, main-router causal recovery,
hard 0/±45° pathway grammar, honest line-service accounting, component size×quantity capacity model,
and all exact collision/clearance invariants. It supersedes V35 **only in residual phase ordering and targets**:

- **Main routing remains first and isolated.** Main chips are placed, the complete main-chip network routes
  against chips only, materialization preflight/causal repair completes, and the main network freezes before
  any secondary object obtains a board position.
- **Components become the first residual phase.** The post-main substantial residual field is served to a seeded
  `Uniform(0.50,0.60)` target. Gap-aware behavior is unchanged: small gaps prefer smaller objects; large gaps
  receive larger objects and/or more objects according to area-weighted size×quantity capacity; optional thin
  pockets may receive micro fillers if feasible or remain empty.
- **Local lines become the second residual phase.** Let `C_actual` be component service and
  `R = 1 - C_actual`. Sample `L_target = Uniform(0.80,0.90)` and require an absolute local-line service target
  `A = R * L_target`. The local report normalizes visible local service by `R`, so the user-facing value describes
  the requested **80–90% of the remaining service budget**.
- **Physical routing remains literal.** The normalized service-budget denominator does not make components
  invisible. Local fillers route through the actual post-component free geometry, with the frozen main network
  and every component as real obstacles.
- **Local behavior remains V35 behavior.** Sources are independent singleton lines; compatible lines may
  temporarily bundle with deterministic 50% probability and later separate; branching remains elevated; region
  size controls source count/length; only visible stroke plus legitimate spacing perimeter contributes service.
- **Component/local clearance is symmetric and exact.** A line body must preserve the full component-pathway
  moat. Ordinary endpoint/source dots are included in final clearance; when a legal line terminates too near a
  component, its terminal may back off only along the already legal path until the marker also clears.
- **No late dependency reversal.** Component failure cannot reroute main pathways. Local failure cannot reroute
  main pathways or move components. The outer logical-sample policy may reject/skip a sample that cannot satisfy
  the hard final invariants.
- **Intentional residual negative space remains valid.** Filling 80–90% of the remaining service budget does not
  mean every geometric sliver must receive a line; the final residual 10–20% and physically awkward pockets may
  remain open.

The V36 compositional intent is: main traces establish the structural network; components next establish the
secondary mass/density pattern over roughly half of the usable residual capacity; local traces then articulate
most of what remains, weaving around the already-frozen component field rather than being decorated afterward.

### V35 honest gap service, canvas-gated population, and residual-pocket correction (historical baseline; superseded by V36 residual order/targets)

V35 keeps the V34 causal main-router corrections but supersedes V34's active scale/population/fill accounting where stated below:

- **No double scale reduction.** `S = S_canvas * MASTER_SCALE`; `U = S / 1600`. There is no extra `0.75` multiplier anywhere. At default `1200×1200`, `MASTER_SCALE=1`, `S=1200` and `U=0.75`.
- **Chip population is canvas-gated.** A `1200×1200` board always has exactly two main chips. The rare third-chip probability is `0.10 * clamp((W*H)/(1200*1200)-1,0,1)` and is independent of `MASTER_SCALE`. A smaller rendered construction on the same canvas does not create another chip.
- **Main-chip separation remains routing-protective.** Pair clearance is `max(430U, 0.265*S_canvas)`; on the default 1200 square this is `322.5` canvas units. This is preventative only; genuine local-space routing and causal traceback/re-route remain mandatory.
- **Local-line coverage is honest visible service.** The board-level target is sampled from `Uniform(0.40,0.43)`. Coverage is measured from geometry that will actually render: the trace stroke plus only its legitimate allocated exclusion perimeter. The meter uses a deterministic 4×4 subcell raster inside each residual-field cell to union that real service width without expensive polygon-union artifacts. Abandoned/short-pruned local routes contribute neither coverage nor collision occupancy.
- **Forty percent is a board-level target, not a requirement to invade every cavity.** Some thin, triangular, short diagonal, isolated, or even complete residual pockets may remain empty. Organic local waves distribute independent fillers across significant connected regions; once the board-level service target is reached, local routing stops.
- **Substantial empty rooms receive a bounded exact mop-up.** After organic synchronous local growth, V35 identifies long contiguous unserved horizontal/vertical/diagonal grid runs inside substantial residual regions and exact-checks a small set of straight filler traces. It does not run full main-network recovery or randomly probe every sliver.
- **Local fillers have real perimeter rules.** Local-to-local spacing is thickness-aware with a minimum edge gap of approximately `1.5×` adjacent mean trace thickness, never below the ordinary inter-route keepout. Later components must preserve the same `component_pathway_clearance` from local lines as from main lines. This spacing is also the only perimeter that may contribute to local service accounting.
- **No invisible abandoned geometry.** A local route pruned as too short is removed from the spatial index and from the coverage field immediately. A line that is not emitted in the SVG cannot help satisfy the 40% target or block a later filler.
- **Hard pathway grammar applies to local fill too.** Every visible pathway body is piecewise straight; consecutive segment headings differ only by `0` or `±45°`. Direct 90° turns and curved pathway primitives are hard rejection conditions after materialization as well as guarded during proposal/branch creation.
- **Main preflight repair is state-safe and lane-preserving.** A physical-lane preflight failure first performs the genuine causal operation: reopen, rollback committed history, suppress the replay corridor, and regrow against the frozen main network. If that real reroute has no legal continuation for a shared-prefix child, the attempt is restored exactly. Only when the inherited physical prefix is already at least four routing modules long and itself passes the complete visible grammar may that one child terminate at its last valid prefix checkpoint; the lane is never silently deleted.
- **Intersection-pair preflight repair is single-causal-side.** Materialization intersection diagnostics identify `new_front` as the later offending trace against `old_front`. Repair `new_front` first; attempt `old_front` only if the first repair cannot succeed. Once one side repairs successfully, never reroute its sibling from the stale pair diagnosis. Final materialization must still show every launched main trace and zero cleanup/intersection counters.
- **Connection geometry is physical-lane geometry.** Head-to-head rendezvous legs must continue the actual rendered incoming lane by `0` or `±45°`. A one-lane child that still retains a non-zero cohort offset is rebased to its exact materialized head with zero offset before any physical junction leg is appended, so offset cannot be applied twice and manufacture a terminal 90° kink.
- **Residual components use substantial-region size × quantity capacity, not literal sliver packing or one-object-per-room accounting.** After pathways freeze, the connected residual field classifies regions as mandatory/substantial versus optional thin/sliver pockets. A region is substantial when it has enough cell area/short-span to plausibly host ordinary component geometry (current gate: at least 4 cells and either short span ≥1.75 component-grid cell widths or at least 10 cells). Only substantial regions form the mandatory `90–94%` denominator. Within them, capacity derives from region area/short span: large rooms require multiple component-capacity units; larger component groups count for more units but one large group cannot satisfy an arbitrarily large room. Acceptance uses the minimum of substantial-region area representation and area-weighted size×quantity capacity, with the seeded target from `Uniform(0.90,0.94)`.
- **Component size follows gap size.** Large substantial rooms prefer larger/multiple groups; medium rooms receive medium groups; small substantial pockets receive small groups. Optional thin pockets may receive a `micro` singleton dot/dash/square/circle when it fits cleanly, but they are not required to be filled and micro components receive no clearance exemption. Oversized collection instances assigned to a smaller usable room may receive a bounded deterministic gap-adaptation scale-down (90%→80%→75%) before exact rechecking; this does not change the global component language. The exact chip/path/component clearances remain authoritative. The source collection scale/quota language is validated on the unadapted templates before routing, so this explicit fit-only shrinkage cannot become a late whole-board collection-scale rejection.
- **Some residual negative space is intentional.** A pocket too thin or awkward for a legal line or component may remain empty. V35 optimizes board-level occupancy and regional proportionality, not literal pixel packing. Components may not compensate for a local-line phase below its own accepted coverage floor, and component failure never triggers routing.

The V35 intent is therefore: two properly separated anchors on the default canvas; main traces that genuinely route/re-route through available local space; roughly 40% of residual routing space visibly articulated by real local lines and their real perimeter; then roughly 90% of the remaining *component capacity* populated with gap-sized, gap-quantity-aware components while preserving intentional negative space.

### V34 local-space causal routing, scale, and fill correction (historical baseline; superseded by V35 where stated above)

V34 retains the V31 transactional-parallel core, V32 source-egress protection, and V33 connected-region fill architecture, but supersedes their active tuning/acceptance rules where stated below:

- **Historical V34 scale rule (superseded by V35):** V34 used `S_canvas * MASTER_SCALE * 0.75` and fixed `{2:0.90,3:0.10}` chip sampling. V35 removes the extra multiplier and replaces chip sampling with canvas-gated population.
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
- **historical V33 rule, superseded by §29.24:** V33 required accepted multi-chip boards to contain at least one true cross-chip pathway connection; current production no longer treats connection count as a board quota. Connection appetite remains, and any already-legal foreign-chip encounter is immediate success without weakening source-egress survival;
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



### V37 coherent residual-component assemblies and anti-confetti correction (retained by V38)

- The V36 phase order remains unchanged: main routes → 50–60% components → 80–90% of remaining service by local lines.
- V33–V36 generic residual dot/dash/square/circle mop-up is no longer allowed to dominate normal open rooms.
- Medium/large residual completion uses compound assemblies built from the established collection grammar, with at least two entity families and high border probability.
- True one-token micro fillers are permitted only in genuinely micro connected residual regions and are capped at eight per sample.
- A medium/large assembly may adapt to local clearance only down to 72% of its generated residual-instance scale; otherwise the candidate point is rejected and a wider location is sought.
- If a later local terminal marker cannot clear a frozen component by retreating along its already-legal path while preserving the minimum visible trace length, that optional local filler is pruned rather than weakening component clearance.

### V38 articulated local-gap routing and 45-degree-only turn hardening

V38 preserves the V37 component-first residual architecture and coherent component-assembly correction. It changes
the **local-line articulation policy**, not the phase order or service accounting.

- Long usable stretches are not normally serviced by one start-to-end ruler stroke. Organic local fronts sample a
  deterministic straight-run allowance of 1–3 accepted gestures. Once that allowance is due, a legal `+45°` or
  `-45°` turn receives a strong soft preference over continuing straight.
- Local gap targets are region attractors rather than rails: their score weight is reduced relative to V37 so a front
  is encouraged to traverse and articulate the available room instead of beelining to a sampled target.
- A two-gesture turn cooldown remains in force after an accepted bend. This deliberately separates **more turning**
  from the old failure mode of rapid compensating zigzags.
- The bounded coverage tail is no longer a straight-corridor shortcut. Normal mop-up traces must contain a
  mid-body `±45°` pivot before commit; they may then continue with ordinary legal local gestures.
- A pure straight mop-up is an exception for a measured genuinely narrow pocket only and is globally capped. If
  fragmented residual capacity still needs service after the ordinary tail, V38 uses a bent-only two-leg dogleg
  rescue rather than reintroducing straight fillers.
- The heading grammar is now defense-in-depth. A direct 90° heading change is rejected by proposal grammar, rejected
  again at commit, checked again from the actual rendered polyline tail, and counted by the final materialized audit.
  No special local repair, mop-up, marker, or fallback constructor is exempt.
- Release regression boards require the **entire visible local population** to remain bent-dominant (straight
  start-to-end traces ≤20% on the maintained reference gates). This is a release gate, not permission to violate
  geometry to force a bend in a pocket where only a legal straight trace can fit.
- New diagnostics report straight visible local count/fraction, mean visible turns per local trace, maximum rendered
  single-vertex turn angle, and bent/straight mop-up counts.

All V37 component service, V36/V37 phase ordering, exact clearance, deterministic seeding, transactional-parallel
main routing, and 50–60% component / 80–90% remaining-local service rules remain unchanged.



### V39 exact octilinear network grammar, rendered-moat hardening, and restored main launch dots

V39 preserves V38 articulation and V37 coherent residual components. It hardens legality at the **network and
rendered-primitive levels**, closing cases that a per-polyline audit could not see.

- **Exact octilinear segments are structural.** Every nonzero pathway segment must be exactly horizontal, vertical,
  or 45-degree diagonal within numeric tolerance. Nearest-octant quantization is diagnostic only and may never make
  a non-octilinear segment legal.
- **Every in-trace heading transition is 0 or ±45 degrees only.** Proposal, commit, recorded path history, materialized
  SVG polyline, and final audit all enforce the same grammar.
- **Connections obey the same grammar through the junction.** Two individually legal traces may not form a 90-degree
  L when joined head-to-head. Traversing across an accepted connection must continue at 0 or ±45 degrees. Illegal
  rendezvous candidates are rejected before commit and counted again by the final network-junction audit.
- **Rendered line-to-line clearances are audited after materialization.** The audit uses actual visible stroke width,
  including local thick-line geometry. Legitimate branch/connection contact is exempt only inside a bounded junction
  envelope; the normal moat resumes immediately outside it.
- **Visible round caps cannot exploit flat-ended planner geometry.** Optional local traces are admitted against the
  frozen chip/component field and already admitted rendered strokes using their actual visible primitive. If a thick
  round cap intrudes into a required moat, the optional trace is omitted rather than weakening geometry.
- **Main-chip emergence dots are trace-owned.** Every visible physical main-chip launch receives a source marker at its
  original emergence point regardless of later branching, release, traceback ownership, or which leaf finally owns
  the visible route. Source markers are no longer conditional on `parent is None`.
- The seeded local service target remains 80–90% of post-component remaining capacity. Exact geometry is hard; if the
  sampled target is exhausted by legal candidates, the release invariant is an 80% normalized floor rather than
  permitting a collision, non-octilinear segment, or illegal junction to force the precise sampled value.

V39 reports `pathway_non_octilinear_segment_count`,
`pathway_illegal_connection_junction_turn_count`, `pathway_unmarked_clearance_violation_count`,
`pathway_main_source_marker_count`, rendered-clearance cleanup counts, and sampled-target shortfall. Release samples
require zero values for all illegality/clearance counters and one main source marker per visible main launch trace.

### V40 verification architecture and test-coevolution hard contract

V40 is intentionally a **verification-architecture release**. The generation algorithm is behavior-equivalent to
V39; only non-behavioral authority/class/output labels change. That equivalence is itself an active release test. V40
repairs the stale-test debt discovered after V39 and makes test maintenance part of the normative design language.

The following rules are hard release invariants for V40 and every later version:

1. **Tests co-evolve with code and design rules.** Any change to generation behavior, probabilities, geometry,
   clearances, phase order, retry/skip policy, fixture assumptions, or reporting must reconcile every affected active
   test in the same version. Carrying forward a test that no longer represents the current architecture is a release
   defect even if that test is not normally executed during development.
2. **The active suite is complete and mandatory.** `tests/active/` contains the current release contract.
   `python run_release_tests.py` must execute the entire discovered active suite and return zero failures, zero errors,
   zero skips, and zero expected failures. Targeted/version-specific tests are development aids only; they never
   substitute for the full active suite.
3. **Active-test manifest exactness is mandatory.** The discovered active test set must exactly match
   `tests/ACTIVE_TEST_MANIFEST.json`. An added, removed, or renamed active test without a simultaneous manifest update
   fails the release gate before the suite can be considered valid.
4. **No stale-test carry-forward.** When a test fixture or literal assertion becomes obsolete, first identify the
   behavior it was protecting. If that behavior remains normative, migrate it to a current bounded fixture before the
   old implementation leaves the active suite. If the behavior itself is intentionally superseded, record that
   supersession explicitly in the version migration ledger and design-language change.
5. **No silent deletion or weakening.** Removing, skipping, xfail-marking, or materially weakening an active test is
   prohibited unless its intent is explicitly migrated or explicitly superseded. A test may not be made green by
   disabling current production machinery or resurrecting obsolete execution semantics.
6. **Current production semantics govern fixtures.** Active tests must model the current one-attempt logical-sample
   policy, deterministic skip behavior, current component-first residual phase, current routing grammar, and current
   clearances. Historical `NoPathRenderer`-style fixtures or old 64-restart grinding may not be used where they
   contradict the active pipeline.
7. **Historical tests are archives, not hidden failures.** Superseded implementations live in complete
   `archive/releases/vNN/` snapshots. The authoritative runner discovers only `tests/active/`, so archived tests remain
   available for provenance but can never masquerade as the current suite. Optional multi-seed probes live under
   `tests/stress/` and are explicitly non-gating; stress results cannot be cited as a substitute for the active gate.
8. **Behavioral snapshot inheritance is exceptional and mechanically proven.** A prior accepted production snapshot
   may carry forward only when the new renderer is mechanically proven behavior-equivalent to the prior renderer.
   V40 uses `test_v40_renderer_is_behavior_equivalent_to_v39` for this purpose. Any future behavioral code change
   invalidates inherited-snapshot status and requires a freshly generated/accepted production snapshot.
9. **Release language is reserved.** A version may not be described as a "pass", "successful build", "verified
   release", or "new baseline" unless the authoritative release runner passes. Verification summaries must state the
   exact command, test count, and zero-exception result.

V40 specifically migrates the seven V39 failing test intents rather than deleting them: batch-domain preservation,
bundle/network collision-clean behavior, deferred hard-stop recovery, holistic connections/loop guard/deep repair,
component-to-main-chip breathing room, single-population component invariants, and cross-population fingerprint
uniqueness. Their obsolete fixtures/seeds are archived; their live behavioral intents remain active.

### V41 tall-canvas exact escape-clipping hard contract

V41 fixes a materialization defect without weakening any routing or audit rule. These rules are normative for every
canvas size and aspect ratio:

1. **Canvas aspect ratio is not a pathway-grammar exemption.** A tall or wide canvas uses the same exact octilinear
   pathway grammar and the same final rendered audits as a square canvas. No aspect-ratio cap or audit relaxation is
   introduced.
2. **First-frame clipping preserves the routed heading.** An escaped visible trace ends at a canvas-frame crossing;
   frame clipping may shorten invisible continuation but may not skew any retained visible segment away from its
   original 0/45-degree heading.
3. **Microscopic escape tails are collapsed through the previous legal leg.** If the final frame-crossing fragment is
   shorter than the established 0.10-module visible-segment floor, the materializer extends the previous visible
   octilinear leg along its own exact DIR8 heading to that leg's frame crossing. It must not move that previous vertex
   to the following fragment's crossing.
4. **No tolerance laundering.** The V39 exact-octilinear classifier and final non-octilinear/illegal-turn counters are
   unchanged. A malformed previous leg or a previous heading that cannot reach a frame is a hard error rather than a
   reason to reinterpret skewed geometry as legal.
5. **Behavior-changing snapshot rule applies.** V41 does not inherit V40's V39-equivalent acceptance snapshot. Fresh
   V41 reference and difficult production snapshots are required and are the active integration evidence.

The regression originates from real `1200×6248` and `1200×8046` portrait canvases. The rule is geometric rather than
aspect-specific: any canvas that produces the same legal-leg + microscopic-final-escape pattern receives the same
correction.

### V42 tall-canvas local-fill scale-invariance and bounded-work hard contract

V42 removes square-canvas assumptions from local residual service while preserving the existing density and geometry
semantics. These rules are normative:

1. **Local service cells preserve physical locality.** The short canvas axis retains `local_gap_grid_n = 56`; the long
   axis uses a proportional cell count so local service cells remain approximately square in physical SVG units. A
   1200×1200 board remains exactly 56×56; 1200×6248 resolves to 56×292 and 1200×8046 to 56×375. The same rule
   applies symmetrically to landscape canvases.
2. **Component population does not inherit local-grid aspect scaling.** `component_gap_grid_shape()` remains 56×56.
   Extreme aspect ratio alone must not multiply the component population or create a new component-density policy.
3. **Existing service semantics are unchanged.** Residual components still service approximately 50–60% of the
   post-main residual field first. Local lines still target 80–90% of the post-component remainder, with the existing
   hard 80% floor and the existing rule that geometry legality wins over forcing an exact sampled percentage.
4. **Broad phases may remove impossible global comparisons, never exact local legality.** Spatial hashes/nearest-
   neighbor queries may replace scans of geometry that cannot affect a capped score or clearance decision. Geometry
   returned as potentially relevant is still evaluated by the same exact Shapely/renderer legality checks.
5. **Execution budgets are not design-language probabilities.** Computational work allowances may scale with canvas
   workload without changing per-line probabilities or routing grammar. V42 scales the local exact-gesture allowance
   by the square root of the tall-area multiplier, caps the articulated fragmented-pocket pass at 200 lines, and caps
   late ordinary local waves at `min(10, ceil(area_multiplier))`.
6. **Dense-tail completion returns to the ordinary router.** After the established bent mop-up and bounded articulated
   fragment cleanup, any remaining tall-canvas deficit is serviced by ordinary local routing waves. Late waves stop
   after two consecutive gains below 0.0025. No straight-line shortcut, illegal geometry, or relaxed clearance may be
   introduced merely to reach the service target.
7. **Pathway grammar and audits remain exact.** Main/local lines remain octilinear; consecutive headings may only stay
   straight or change by ±45 degrees; V39/V41 rendered-clearance, junction-angle, source-marker, and clipping rules
   remain in force.
8. **Determinism remains version-local.** Same V42 seed + arguments produce the same V42 decisions/output. Search
   optimizations must use stable ordering where ordering can affect a deterministic choice.
9. **Fresh acceptance evidence is required.** Because V42 changes local-grid/service execution behavior, it uses fresh
   V42 square acceptance snapshots plus deterministic tall acceptance evidence at 1200×6248 and 1200×8046 rather
   than inheriting V41 output snapshots.

The tall acceptance cases using deterministic base seed 1 realize normalized local remainder service of approximately
0.8381 and 0.8309 respectively, with zero non-octilinear, illegal-turn, illegal-junction, rendered-clearance,
main/local-clearance, local/component-clearance, or unauthorized component/pathway-overlap violations.

---

# 29. Active change record

This section records active specification maintenance. It does not supersede the normative sections above; each
entry identifies where the corresponding rule is defined.

## 29.1 2026-08-14 — Stable authority path and mandatory session governance

- Renamed the canonical specification from `chip_design_language_v39_variance_driven.md` to the version-neutral
  `chip_design_language.md`.
- Stored the active version in §0.0 and the machine-readable manifest instead of relying on the filename.
- Established mandatory full-session reading and same-change specification maintenance through root `AGENTS.md`
  and `CONTEXT.md`.
- Persisted the established root-cause-first, full-system verification, standards-based frontend, deterministic
  output, SVG paint-order, hydration, and progressive-enhancement working agreements in root `AGENTS.md`.
- Preserved historical versioned specifications under `archive/` unchanged.
- This governance and authority-path change intentionally does not alter renderer behavior or regression tests.

## 29.2 2026-08-14 — V40 verified test-contract architecture

- Promoted the behavior-equivalent V40 renderer while retaining the V39 renderer as the mechanically compared
  behavioral baseline required by the active equivalence test.
- Reconciled all seven stale V39 test implementations into bounded current-architecture tests without deleting their
  still-normative intent; preserved the prior implementation with the complete V39 release snapshot.
- Established `tests/active/`, the exact `tests/ACTIVE_TEST_MANIFEST.json`, and `python run_release_tests.py` as the
  zero-exception authoritative release gate defined above and in `TEST_ARCHITECTURE_V40.md`.
- Separated optional current-policy multi-seed probing into `tests/stress/`; stress results are not release evidence.
- Preserved the version-neutral authority path and corrected incoming references to `chip_design_language.md`.
- Preserved the V39 exact-octilinear machine-manifest lineage while advancing its version identity to V40; the
  incoming changed-files package's stale `v38` manifest label was not carried forward.
- Reused the accepted V39 reference artifacts from `examples/` because source equivalence is asserted by the active
  suite; no renderer algorithm or geometry rule changed in V40.
- Verified the consolidated repository with `python run_release_tests.py`: 44/44 active tests passed with zero
  failures, errors, skips, expected failures, or manifest mismatch.

## 29.3 2026-08-14 — Repository-native V39 archival consolidation

- Moved the superseded V39 renderer, test suite, design-language snapshot, changelog, README, and verification summary
  into the established `archive/releases/v39/` structure used by V34–V38.
- Updated the active V40 source-equivalence test to read the archived V39 renderer and normalize only the known
  non-behavioral authority/class/output labels before requiring exact source equality.
- Kept inherited V39 production reference SVG/report artifacts in `examples/` because they remain active V40
  acceptance evidence; they are not superseded runtime source files.
- Removed the package-oriented `history/tests/` layout in favor of the repository's complete-release archive model.
- Preserved active discovery exclusively under `tests/active/`; archived tests are neither imported nor executed by
  the authoritative release runner.
- Re-ran `python run_release_tests.py` after reference relocation: 44/44 active tests passed with zero failures,
  errors, skips, expected failures, or manifest mismatch.

## 29.4 2026-08-14 — V41 tall-canvas exact escape clipping

- Reproduced the reported `1200×6248` failure on deterministic base seed `1`; the main-network preflight contained
  exactly one non-octilinear rendered segment even though the pre-clipped materialized path was fully octilinear.
- Traced the defect to `_clip_escaped_polyline_to_frame()`: its sub-0.10-module tail cleanup moved the previous
  visible vertex to the current final leg's frame crossing, skewing a preceding 45-degree leg.
- Corrected the cleanup to extend the previous visible octilinear leg along its own exact heading to its own first
  frame crossing. The exact-octilinear classifier, turn grammar, collision audits, and visible-segment floor were not
  weakened.
- Added active regression coverage for the microscopic-tail mechanism at heights `6248` and `8046`, and optional
  real main-network stress coverage for both `1200×6248` and `1200×8046` using base seed `1`.
- Because renderer behavior changed, retired the V40 source-equivalence gate and generated fresh V41 reference and
  difficult acceptance snapshots.
- Archived the superseded V40 release under `archive/releases/v40/`.

## 29.5 2026-08-14 — V42 tall-canvas local-fill scaling and bounded performance

- Kept local residual service physically local by scaling only the long-axis local grid count with canvas aspect ratio;
  the 1200-square reference remains 56×56 while 1200×6248 and 1200×8046 use 56×292 and 56×375.
- Deliberately retained the fixed 56×56 component population grid so portrait/landscape aspect ratio does not silently
  multiply component population.
- Replaced capped-distance all-to-all source scoring and global residual-distance work with spatial broad phases that
  preserve the same exact nearby geometry decisions.
- Removed repeated whole-field sorting/recomputation where only bounded top candidates or affected regions are needed.
- Scaled local exact-gesture computational allowance with sqrt(area multiplier), bounded the efficient articulated
  fragmented-pocket cleanup at 200 lines, and returned remaining tall-board deficit to ordinary local waves with a
  bounded stagnation stop.
- Preserved component-first 50–60% service, local 80–90% remainder service, exact 0/±45-degree grammar, rendered
  clearances, deterministic seeding, chip source markers, and V41 first-frame clipping.
- Added V42-specific active regression coverage for physical local-grid size, unchanged component grid, and bounded
  tall work allowances; retained the V41 microscopic escape-tail regression.
- Generated fresh V42 standard/difficult square snapshots and deterministic 1200×6248 / 1200×8046 tall acceptance
  artifacts with all exact geometry/clearance counters at zero.
- Archived the complete superseded V41 release under `archive/releases/v41/`.



### V43 aspect-invariant spatial-population hard contract

V43 supersedes V42 wherever V42 treated an extended rectangle as a square-board population inside a larger coordinate
frame.  The renderer has **one generative law for every aspect ratio**; only the amount of normalized physical territory
changes.

1. **Entity scale is not population extent.** Chip/component/trace dimensions continue to derive from the short-side
   design basis and explicit `main_scale`.  Population opportunity derives only from normalized territory
   `T=(W*H)/min(W,H)^2`. Changing `main_scale` cannot create or remove population opportunities.
2. **Rotation invariance is hard.** Swapping `W` and `H` preserves `T`, chip-count distribution, prepared-collection
   count distribution, isolated-capacitor opportunity density, component-filler limits, and all probability laws. Grid
   shapes transpose; rules do not change.
3. **Main-chip population is stationary.** Each complete short-side-square territory contributes exactly two chips;
   the fractional final territory independently realizes each of two opportunities with probability equal to its
   fractional area. All chips are placed by the existing global spread/clearance solver—never by copied tiles or bands.
4. **Prepared component language is stationary.** The square baseline 15–18 prepared-collection draw is repeated per
   complete normalized territory, with fractional-territory thinning as in §3.2. Isolated-capacitor batches receive the
   same per-territory opportunity law. Residual coherent assemblies remain the gap-aware completion language rather than
   a substitute for missing prepared population.
5. **Component and local service grids preserve physical locality.** Both residual-service grids keep approximately the
   same physical cell size as the square reference and transpose under canvas rotation. A fixed 56×56 grid may not be
   stretched across an extended axis.
6. **Coverage/service cannot be faked by giant cells or giant connected regions.** The existing component 50–60% and
   local-line 80–90%-of-remainder contracts apply over the full physical canvas. Population and candidate selection must
   remain spatially distributed; a cluster occupying one short-side-sized portion of an extended canvas cannot count as
   whole-board service merely because the rest belongs to the same connected residual region.
7. **Population-related execution caps scale with territory without changing per-entity behavior.** Main gesture-check
   allowance, residual component completion allowance, micro-filler cap, local branch/source ceilings, articulated local
   cleanup allowance, and late ordinary-wave opportunity are bounded per normalized territory. Historical square-only
   maxima such as the 34-source per-region ceiling scale by `T` while the existing local cell-capacity rule remains in
   force. If the normal late-wave cap ends below the normative 80%-of-remainder local floor, a target-gated reserve of the
   **same ordinary local router** may continue with an orientation-neutral cap that scales with normalized territory.
   A single zero-gain wave cannot cancel the remaining bounded reserve. After untouched-cell reserve opportunities are
   exhausted, the same ordinary router may retarget cells whose 16-subcell service mask is still below 80%; this changes
   candidate eligibility only, never the service metric, geometry grammar, clearances, branching probabilities, or hard
   floor. This reserve introduces no new visual geometry/probability language.
8. **Pathway broad phases are locality-preserving optimizations only.** Spatial hashes may replace global scans for
   connection candidates, source-egress conflicts, nearest foreign heads, congestion/coverage bookkeeping, repeated
   same-snapshot legality checks, and rendered/pathway-clearance candidate discovery. Every potentially relevant pair
   must still reach the same exact geometry rule; a broad-phase radius may never be narrower than the maximum exact moat
   that the queried pair can require. During local routing, the frozen main network must be indexed both as routing
   segments and as its exact rendered multi-segment stroke geometry; flat per-segment approximations may not create a
   blind wedge at a mitered 45-degree main-trace joint. Local materialization must redundantly admit visible strokes
   against those exact frozen rendered-main primitives.
9. **Proposal-variant legality is snapshot-cacheable.** Multiple variants for one front in one transactional round see
   the same immutable committed geometry. Exact legality for an identical direction/length candidate may therefore be
   computed once and reused inside that transaction; stochastic scoring/weighted selection remains independently drawn.
10. **No aspect-specific visual mode.** There is no "tall", "wide", or "square" rendering behavior. Any special-case
    branch whose only semantic trigger is aspect ratio is invalid unless it is purely an execution/storage optimization
    proven not to change the generative contract.
11. **Acceptance evidence covers orientation and extension.** V43 release evidence includes square reference output plus
    deterministic extended portrait and landscape boards. Reports must show population across all long-axis quarters,
    component/main-chip span across the long axis, service targets met, and zero octilinear/turn/clearance violations.

V43 intentionally invalidates V42 rule 2 under "tall-canvas local-fill scale-invariance": the fixed 56×56 component grid
and fixed global component population were the mechanism that allowed a long board to report high service while visibly
placing almost all components near one end.

## 29.6 2026-08-14 — V43 aspect-invariant spatial population

- Reclassified extended-canvas population as a first-class stationary spatial process rather than a square-board
  population embedded in a larger coordinate frame.
- Defined normalized territory `T=(W*H)/min(W,H)^2`; entity dimensions remain short-side / `main_scale` based while
  main-chip, prepared-collection, isolated-capacitor, residual-completion, and bounded routing opportunities scale with
  physical territory.
- Made component and local residual grids preserve approximately square-reference physical cell size and transpose
  under width/height rotation. Removed V42's fixed 56×56 component-grid assumption.
- Spatialized main-router connection/source-egress/nearest-head/bookkeeping work and cached deterministic same-snapshot
  gesture legality without changing stochastic proposal scoring or exact geometry decisions.
- Corrected pathway/render-admission broad-phase clearance reach so thin traces can never miss a nearby thick trace whose
  exact pair-specific moat exceeds the old fixed query radius; final rendered audits remain exact and redundant.
- Corrected frozen-main representation in the local phase: exact rendered multi-segment main polylines are now immutable
  planner obstacles and are preloaded into final local render admission, closing the miter-joint blind wedge left by
  segment-only flat-cap approximations. The final main/local audit broad phase also uses the maximum pair-specific moat.
- Scaled local exact-gesture computational allowance linearly with normalized territory, matching the stationary
  amount of local routing work on extended canvases; the V42-era sqrt-territory CPU allowance is superseded.
- Added bounded hard-floor rescue using only the ordinary local router when area-scaled normal work ends below the
  normative 80%-of-remainder floor; no service target or geometry rule was lowered.
- Strengthened active placement coverage across multiple deterministic portrait and landscape seeds so every long-axis
  quarter must receive main-chip population on the maintained extended fixture.
- Reconciled remaining square-era local execution assumptions found by the upper 1200×8046 integration gate: the
  historical 34-source per-region ceiling now scales per normalized territory, one zero-gain rescue wave no longer
  cancels the remaining bounded ordinary-router reserve, and hard-floor-only targeting may revisit partially serviced
  cells whose binary "touched" status otherwise disagrees with the 16-subcell area service audit.
- Corrected the local exact-check allowance to scale exactly once (`22000*T`), not accidentally `22000*T^2`, and made
  large local-target shortlisting workload-triggered rather than aspect-triggered.
- Added direct regressions for mixed `None`/integer fragmented-region queue priorities discovered during full 6248
  production acceptance, territory-scaled region-source capacity, non-cancelled hard-floor reserve, and partial-service
  retargeting semantics.
- Final fresh full 1200×6248 acceptance (logical sample 0): 10 main chips distributed `[2,3,3,2]`, 200
  component groups distributed `[50,44,50,56]`, 54.0955% component service, 80.1533% local remainder service,
  427/427 main source markers, and zero exact octilinear/turn/clearance violations.
- Final fresh full 6248×1200 rotated acceptance (logical sample 0): 10 main chips distributed `[3,2,2,3]`, 204
  component groups distributed `[54,50,50,50]`, 54.1830% component service, 80.2944% local remainder service,
  427/427 main source markers, and zero exact octilinear/turn/clearance violations.
- Final fresh full 1200×8046 upper-range acceptance (logical sample 0): 13 main chips distributed `[3,3,4,3]`,
  270 component groups distributed `[72,70,66,62]`, 54.0034% component service, 80.2779% local remainder
  service, 541/541 main source markers, and zero exact octilinear/turn/clearance violations. The ordinary hard-floor
  reserve used all seven territory-scaled untouched-cell waves and then two area-aligned partial-service retarget waves.

### Historical V44 scale-stationary fine-detail hard contract — superseded by V45

V44 extends V43's coordinate-free population law across explicit `main_scale` values substantially below 1.0.
`main_scale` changes the physical size of design entities; it does not create a second rendering mode and it does not
change the normalized-territory population law.

1. **Population and detail scale are separate.** Normalized population territory remains
   `T=(W*H)/min(W,H)^2` and is independent of `main_scale`. Main-chip and prepared-population opportunities therefore
   remain unchanged when only `main_scale` changes. Entity dimensions and all U-based clearances remain proportional
   to `main_scale`.
2. **Service bookkeeping follows the design unit.** Component and local service grids preserve approximately the same
   cell size in design units. Relative to the scale-1 square reference, grid resolution grows by `1/main_scale` on each
   axis and still transposes under W/H rotation. A smaller design may never be judged by giant scale-1 bookkeeping
   cells.
3. **Fine-detail completion capacity follows design-scale area.** Define `D=T/main_scale^2`. Residual component
   completion, local trace/source ceilings, hard-floor rescue opportunities, and other completion work whose purpose is
   to service physical design area are bounded per `D`, not by scale-1 global caps. This does not alter the 50–60%
   component target or 80–90%-of-remainder local target.
4. **Main routing does not brute-force extra global rounds.** The main router retains the existing synchronous
   transactional round language and branching/turn/connection probabilities. Coarse congestion/coverage bookkeeping
   remains aspect-aware but `main_scale`-independent. Exact-computation allowance may scale with physical journey
   resolution (`1/main_scale`) and normalized territory, but a smaller scale does not authorize a different routing
   grammar or arbitrary multiplication of global lifecycle rounds.
5. **Fine-front performance optimizations are decision-preserving.** Spatial singleton pairing replaces all-pairs
   scans only inside the same exact distance window; same-round ready tracebacks may rebuild shared spatial indexes once
   after the batch; immutable-snapshot candidate legality/corridor calculations may be cached. Every candidate that can
   affect an exact geometry decision must still reach the same exact test, and seeded stochastic draws retain their
   defined order/independence.
6. **Inherited visible-lane grammar applies from a child's first gesture.** A branch/recovery fragment that inherits a
   rendered prefix may not use a one-point child-centerline shortcut to complete a forbidden compensating A→B→A→B
   weave. Every structural turn that can combine with inherited visible geometry is validated against the actual
   materialized lane tail before commit. The final zigzag audit remains unchanged and hard.
7. **Fine local-service bookkeeping is incremental but semantically identical.** Untouched/retarget sets and per-region
   candidate availability may be maintained incrementally rather than reconstructed from the entire service field on
   every source decision. Rollback/rebuild paths must resynchronize those indexes from authoritative path geometry. The
   16-subcell service masks remain the source of truth for measured coverage.
8. **Rendered local clearance includes all visible primitives.** Final admission of an optional local trace validates
   its actual rendered stroke plus any source/terminal marker extent against frozen chips/components and the exact
   rendered main network. A line body that clears a component does not legalize a marker that enters the component
   moat; the optional trace is pruned instead of weakening clearance.
9. **No aspect-or-scale visual mode.** Portrait, landscape, square, scale 1.0, and fine `main_scale` inputs all use the
   same deterministic/probabilistic language. Differences arise only from the amount of normalized territory and the
   physical size/resolution implied by `main_scale`.
10. **Fine-scale acceptance is production acceptance.** Maintained release evidence includes logical-sample-0 full
    production renders at 1200×6248 and 1200×8046 with `main_scale=0.35`. They must satisfy the normal population
    distribution, 50–60% component service, 80–90% local-remainder service, exact 0/±45° grammar, marker rules, and all
    frozen-geometry clearances without batch skip/retry hiding a failed logical sample.


### V45 true-zoom logical-area hard contract

V45 supersedes V44 wherever V44 made `main_scale` affect entity dimensions without increasing primary population.

1. **`main_scale` is a zoom.** Define `T_canvas=(W*H)/min(W,H)^2` and `T_logical=T_canvas/main_scale^2`. A fixed SVG at smaller scale shows proportionally more logical board distance on each axis and more logical board area overall.
2. **Primary population follows logical area.** Main chips, prepared component collections, and isolated-capacitor opportunities all use `T_logical`. Residual fillers may not compensate for artificially missing primary population.
3. **Geometry remains linearly scaled.** Chip/component/trace dimensions and clearances still derive from `U=min(W,H)*main_scale/1600`. In particular, chip-to-chip clearance may not retain a raw-canvas floor that prevents fine-scale entities from occupying the newly exposed territory.
4. **All spatial bookkeeping uses design-local resolution.** Main congestion/coverage grids and component/local service grids refine by reciprocal `main_scale` on each axis and transpose under W/H rotation.
5. **Work scales once with logical area.** Fine-scale population/detail work budgets use `T_logical`; they may not multiply by a second inverse-distance or inverse-area factor simply because scale is small.
6. **No scale/aspect mode.** Square, portrait, landscape, default scale, and fine scale use the same probability laws, routing grammar, component language, and exact legality gates. Only available logical territory and linearly scaled physical dimensions change.
7. **Routing remains parallel and transactional.** More fine-scale chips create more simultaneous fronts; performance optimizations may use exact broad phases, spatial indices, deterministic caches, and bounded ranking heuristics, but final collision/clearance and 0/±45° grammar decisions remain exact.
8. **Journey scale is local in design space.** Explore/exit targeting must not make a fine-scale trace chase a raw-canvas-scale destination merely because the SVG is physically large relative to one design module. Global board coverage emerges from the greater number of stationary local populations.
9. **Horizon completion is lifecycle-local.** A mature route that has already earned a legal local ending is not forced into a physical-frame escape search merely because the synchronized global horizon ended. Expensive bounded survival search is reserved for genuinely immature/protected main-chip launches; this rule is scale/aspect independent.
10. **Global recovery horizon is not route length.** The synchronized transaction horizon is 24–28 rounds. It only bounds board-wide rollback/recovery opportunity; each front's sampled run-length, turn, branch, connection, and gesture grammar is unchanged.

## 29.7 2026-08-14 — V44 scale-stationary fine detail and bounded performance

- Extended V43's stationary canvas law across `main_scale` by separating population territory `T` from design-detail
  area `D=T/main_scale^2`.
- Made component/local service grids local in design units, giving 160×833 at 1200×6248 @ 0.35 and 160×1073 at
  1200×8046 @ 0.35 while preserving the 56-cell short-side reference at scale 1.0.
- Kept main-chip/prepared-population opportunities independent of `main_scale`; only fine residual/detail capacity and
  execution opportunity scale with the amount of smaller geometry required to satisfy unchanged service rules.
- Spatialized fine-network singleton connection pairing, batched same-round traceback index rebuilds, and cached
  deterministic same-snapshot proposal geometry/legality to remove superlinear costs without reducing branch or route
  behavior.
- Corrected inherited-prefix zigzag validation for long-lived structural children and for the first gesture of a
  recovery-fragment child; forbidden visible weaves are rejected before commit rather than cleaned up after rendering.
- Reworked fine local targeting/first-touch bookkeeping to maintain authoritative untouched/retarget state
  incrementally while preserving the same 16-subcell service masks and rebuild semantics.
- Hardened local materialization so source/terminal marker geometry, not only the line body, must preserve frozen
  component/chip clearance. This closes the rotated scale-1 regression discovered during V44 release verification.
- Hardened main preflight intersection repair so a diagnosed pair repairs one causal side at a time; the already-valid peer is not independently rerouted after the first side succeeds. This closes the stress-discovered main-trace cleanup regression without weakening the final materialization audit.
- V44 release is gated by the exact active manifest plus fresh square, extended scale-1, and 0.35 extended production
  acceptance reports; release status is recorded in `V44_VERIFICATION_SUMMARY.md`.



## 29.8 2026-08-15 — V45 true zoom / logical-area population

- Replaced V44's scale-independent primary population law with `T_logical=T_canvas/main_scale^2`.
- Removed the raw-canvas chip-clearance floor that prevented fine-scale chips from using the newly visible territory.
- Made main-routing occupancy grids design-local, matching residual service grids.
- Unified primary population and fine-detail capacity on the same logical-area basis, removing V44's separate `T` versus `D=T/main_scale^2` split.
- Removed the extra main-routing distance multiplier from the gesture-check allowance; logical area already accounts for the increased amount of board.
- Spatialized same-round conflict grouping and added exact AABB broad phases/caches so larger true-zoom populations do not pay scale-1-hidden all-pairs costs.
- Fixed chip-placement broad-phase reach so the spatial query covers the full exact `430U` chip-to-chip moat before the exact geometry test; dense true-zoom populations can no longer bypass clearance because of an undersized query window.
- Made post-horizon completion lifecycle-local: mature routes terminate locally, while bounded beam search remains only for immature/protected launches. Reduced family settlement to two bounded ticks and set the global transactional recovery horizon to 24–28 rounds without changing any front's own route grammar.
- Fresh V45 evidence: 1200×1200 at `main_scale=0.35`, seed 45035 produces 16 primary chips; 1200×6248 at `0.35`, seed 45036 produces 86 chips across long-axis quarters `[22,22,18,24]`. A real 1200×1200/0.35 main-network run on seed 45035 completed with 682 visible launch traces, 79 cross-chip connections, and zero hard geometry-audit violations.
- Kept exact route legality, deterministic seeding, component-first residual service, local-line remainder service, and all frozen-geometry audits unchanged.

## 29.9 2026-08-15 — V45 scale-0.35 forensic performance audit and release revocation

- Revoked V45's prior release-PASS designation after a real `1200×6248 @ main_scale=0.35` production render failed to emit and exposed a combinatorial prepared-collection calibration solver whose implementation still assumed `N<=18`; true-zoom territory produced approximately 699 prepared collections on the inspected logical sample.
- Classified the subsequent large-board failures separately: whole-population component-template retry on one duplicate/near-duplicate creates retry/livelock risk; main routing contains repeated global/per-chip bookkeeping whose cost grows faster than logical territory; terminal and marker cleanup retains repeated all-pairs work.
- Established the governing performance invariant for the next implementation: **scale and aspect ratio may increase only logical territory, not the semantic scope of local decisions.** A local routing, uniqueness, placement, or terminal-conflict question must not rebuild or pair-scan the entire board merely because more independent territory is visible.
- Required locality-preserving replacements include one labeled shared active-head spatial index; indexed family/owner/child/fragment lifecycle state; versioned materialized-lane geometry with a spatial join index; spatial terminal-head and terminal-marker conflict queries; local offending-collection uniqueness retry with bucketed fingerprint lookup; and region/fit-indexed residual component sites.
- Clarified that expected work is primarily proportional to logical territory `A = canvas_territory/main_scale^2`, with bounded local stochastic variance. The specification does not require a mathematically exact O(A) runtime, but forbids hidden full-board O(N^2) or per-local-candidate full-board rebuilds when a spatial/local equivalent preserves the same exact geometry rule.
- Required future release evidence to execute complete long fine-scale production through accepted SVG/report emission and to record normalized wall-clock and peak-memory behavior. Population-only fixtures, square-only fine-scale routing evidence, or historical long scale-1 reports cannot substitute for this gate.
- No renderer behavior was changed by this forensic record. `pcb_v45_renderer.py` remains the failing V45 baseline so the next architectural correction can be measured against the actual defect.


## 29.10 2026-08-16 — V46 logical viewBox and locality-preserving optimization

V46 supersedes V45's implementation of scale while retaining V45's governing insight that a smaller scale exposes more logical board territory.

### V46 logical-space hard contract

1. **Public geometry is aspect ratio + scale only.** The renderer does not accept user-controlled SVG width/height and does not expose `main_scale`. Aspect ratio determines shape; scale determines how much logical board is visible.
2. **Canonical logical geometry is stationary.** Let the canonical short side be 1200 logical units. At scale `s`, the logical short side is `1200/s`; the other axis follows the requested aspect ratio. Chip, component, trace, clearance, module, probability, and route-grammar dimensions remain canonical in logical units instead of being individually multiplied by scale.
3. **Aspect extension and zoom are the same operation.** Population/work opportunity derives from logical viewBox area divided by `1200²`. The generator must not know whether extra logical territory came from a longer aspect ratio, a smaller scale, or both.
4. **SVG output is dimensionless.** The root SVG contains a logical `viewBox` and no fixed `width`/`height` attributes. Physical display size is external to generation.
5. **Locality is a performance invariant.** Increasing logical territory may increase the number of independent objects/networks, but may not enlarge the semantic scope of a local decision. Route-head, terminal, component, rollback, uniqueness, gap-site, and local-target decisions use local/family spatial indexes or bounded equivalent structures where exact behavior permits.
6. **No functionality may be traded for speed.** Exact octilinear geometry, straight/±45° turn grammar, connection rules, chip/component/pathway/marker clearances, deterministic seeded generation, phase order, component 50–60% service, and local-line 80–90% remainder service remain hard.
7. **Optimization predicates remain exact.** Spatial broad phases may reduce candidate sets only when they provably contain every object capable of satisfying the original exact predicate. The exact geometric predicate remains authoritative after the broad phase. Active differential/brute-force tests guard these replacements.
8. **Prepared population scales without combinatorial state.** Collection calibration may not create a state dimension per collection. A duplicate/near-duplicate template may retry only itself inside its already-selected calibration category; it may not restart an otherwise valid whole population merely because logical territory is larger.
9. **Local service scales opportunity, not repeated board scans.** Full-board local waves are bounded. Source/branch/trace opportunity scales with logical territory, while hard-floor rescue may exceed bookkeeping region caps only to realize the existing 80% floor and must still obey global work ceilings and exact geometry legality.
10. **Visible main-side progress remains 8 modules.** Terminal/source marker clipping cannot legalize a side that renders shorter than the hard floor. A diagnosed singleton may be repaired only by physically extending through ordinary proposal generation and exact gesture/clearance gates; the threshold itself is never reduced.
11. **Workload-changing releases require fresh full production evidence.** Historical scale-1 or partial population/main-network reports cannot satisfy a V46 release. The maintained long scale-0.35 case must execute through accepted SVG/report emission and normal final audits.

### V46 optimization pass

- Replaced the large-N collection calibration explosion with bounded deterministic quota solving while retaining small-N differential behavior.
- Localized duplicate-template retry to the offending calibrated collection.
- Replaced per-chip/global route-head structures, terminal joins, marker conflicts, temporary local-bundle affinity, and final static audits with exact spatial broad phases.
- Added indexed family/child/fragment/side state, per-front route-segment ownership, and versioned materialized-lane caches so recovery/connection work is proportional to the affected family/region rather than whole-board history.
- Replaced repeated whole-residual-field/site/region scans with stable partitions, incremental counters, spatial indexes, and exact lazy priority queues.
- Vectorized nearest-geometry scoring over unchanged candidate points/distances.
- Avoided giant dissolved GeometryCollection/pathway keepout operations where primitive-local set-equivalent checks preserve the same forbidden set.
- Corrected ordinary unbundled local traces being retargeted every round; only actual temporary-bundle release triggers the documented retarget behavior.
- Corrected an expanding nearest-head broad-phase exactness bug that could otherwise skip a candidate seen in a square query before it entered the circular search radius.
- Added narrow post-materialization main-side progress repair that preserves the existing 8-module visible requirement by legal physical extension only.


## 29.11 2026-08-17 — V47 persistent-locality reconstruction and memory-lifetime hardening

V47 supersedes the unreleased V46 candidate. It preserves V46's aspect-ratio + scale logical-viewBox
architecture and all visible grammar/service rules, while repairing V45/V46's premature main-route lifecycle
regression and the V46 long-fine-scale runtime/memory bend.

### V47 main-route persistence contract

1. Normal main routing remains **24–28 synchronized transactional rounds**. This is followed by **32–40
   shared-clock persistence ticks** for still-live main families. The late phase is family-local in proposal scope
   but all families advance on one shared clock.
2. Rollbacks becoming ready on one shared tick are applied as one batch and the shared path index is rebuilt once
   for that state transition. Cross-family singleton connection targeting is refreshed once per shared tick.
3. A live main route owes hard persistence debt while its materialized visible journey is below **6 modules**, while
   source-egress/fan/fragment/required branch structure remains unfinished, or while a singleton is still visibly
   embedded in its live family. Reroute bookkeeping alone is not debt after visible maturity.
4. The **4-module main-launch floor** and **8-module chip-side visible-progress floor** remain unchanged. The 6-module
   journey is the preferred persistence terminal threshold; a sample is rejected rather than horizon-killing an
   internal free main route below it. Legitimate frame clipping is reported separately.
5. Final terminal settlement is **atomic at the visible cohort level** for both same-root ending cohorts and
   recovery-fragment sibling cohorts. The anti-singular-terminal rule is hard throughout normal routing, the shared
   persistence clock, and the bounded exact separation repair. After those legal movement opportunities are exhausted,
   an otherwise-complete route that is already at least 6 visible modules may become legally terminable through the
   final coordinated persistence fallback; impossible physical movement is not infinite debt. This exception is allowed
   only for a lane already marked unresolved by the failed bounded repair, never for under-length, source-egress, fan,
   fragment-birth, or branch-transition debt. Every such fallback is counted explicitly. Sequential per-lane
   classification is forbidden because it can falsely keep an adjacent mature ending cohort alive forever.
6. Bounded embedded-lane separation uses only ordinary straight/±45° geometry and exact normal collision/clearance
   predicates. There is no board-global late search and no restoration of V44's heavy whole-board persistence tail.
7. Close-head terminal connections are transactional: every lane detachment required by the pair must be proven
   possible before either family is mutated. A failed pair leaves both lifecycle states unchanged.
8. Post-marker rendered geometry is authoritative for visible-persistence reporting. Hollow source/terminal styling
   may be replaced by the legal filled-dot variant when clipping would visually amputate a mature main route below
   the protected persistence journey; the route threshold itself is never lowered for marker styling.

### V47 runtime and memory-lifetime contract

- Main/local planner objects are transient and may not be retained after frozen geometry/statistics are extracted.
- Component templates are instantiated only after main routing is frozen and main-planner transient state is gone.
- Component residual raster/region fields are released before local routing once their minimal retained service state
  has been extracted.
- Finished `Group` union/collision/spatial-index caches are rebuildable and are released at phase boundaries; immutable
  primitive geometry remains available to later phases that need exact neighbouring obstacles.
- Component placement indexes raw main-path primitives and constructs exact keepout buffers only for nearby queried
  candidates instead of retaining one buffered GEOS object per path primitive.
- Local routing retains each frozen main rendered polyline once. Congestion/coverage replay does not retain duplicate
  buffered geometry for every segment.
- Residual/local service accounting is incremental. It must remain exactly equivalent to the governing service metric;
  board-sized open-cell sets may not be recopied per object.
- Final rendered trace centreline/stroke/clearance checks share one exact spatial pair pass. Spatial broad phases are
  filters only; exact geometry remains authoritative.
- Straight-polyline nearest projection used by sibling-embedding checks is computed by exact segment arithmetic rather
  than repeated GEOS projection object allocation.

### V47 reporting and release gate

The live candidate reports post-materialization main launch accounting, per-trace visible length/outcome, frame exits,
connections, horizon-under-preferred terminals, floor-hugging terminals, stalled sides, and active-but-unmaterialized
launch IDs. Historical V44/V45/V46 reports cannot satisfy a V47 live persistence gate.

The active manifest and `python run_release_tests.py` are necessary but not sufficient. V47 release additionally
requires fresh accepted production output for `1:1 @ 1.0`, `1:1 @ 0.35`, `1200:6248 @ 1.0`, and
`1200:6248 @ 0.35`, with exact geometry/service audits, visible-persistence accounting, wall-clock normalization,
and peak RSS recorded in `V47_VERIFICATION_SUMMARY.md`.

## 29.12 2026-08-20 — LOCAL direct run-family bounded stochastic work

The LOCAL direct mop-up keeps V38's bent-first grammar, the V47 territory-scaled direct service opportunity,
and exact geometric legality. This refinement changes only **how much stochastic retry work one unchanged residual
corridor may generate**.

1. A direct-mop-up run family is the same residual-region axis run with the same two physical run endpoints,
   independent of which endpoint is chosen as the stochastic start for one realization.
2. During one `_local_gap_direct_mopup()` call, one unchanged run family receives at most **3** stochastic
   realizations: its initial realization plus at most two retries for thickness/order variance.
3. After the third failed realization, that run family is quarantined from candidate generation/ranking for the
   remainder of that direct-mop-up call. Larger logical territory creates more run families; it may not create more
   retries of the same unchanged family.
4. The quarantine is generation-side work control, not a geometric legality shortcut. Every admitted realization
   still passes exact source clearance, straight/±45-degree grammar, pathway/component/static clearance, and the
   existing one-sided exact failure-certificate checks.
5. The local service target remains the canonical physical **80–90% of the post-component remainder**. Quarantine
   may not lower the hard 80% floor; downstream ordinary bounded service machinery remains available when genuine
   independent debt remains.
6. The retry budget is scale/aspect independent. This prevents stochastic polling count from becoming a hidden
   multiplier as logical territory grows, in accordance with the locality invariant in §29.10.

This refinement intentionally preserves deterministic probabilistic variation without preserving invisible,
unbounded repeated attempts of the same unchanged corridor.
## 29.13 2026-08-20 — LOCAL two-stage hard-floor rescue aligned to physical service debt

LOCAL hard-floor recovery now separates two different jobs that were previously conflated: broad visual spread over
untouched residual territory and payment of the canonical 16-subcell physical service debt.  This refinement preserves
the existing routing grammars, exact legality predicates, hard **80%** floor, and sampled **80–90%** normal preference.

1. Hard-floor recovery receives at most **2 broad ordinary untouched-cell rescue waves**.  These are the same ordinary
   local-wave opportunities and use the same source/routing grammar; the bound is not scale- or aspect-specific.
2. If physical service is still below the hard floor after those broad opportunities, the residual problem is treated
   as **subcell service debt**, not as another binary whole-field spread problem.  Emergency direct/fragment cleanup
   temporarily targets the hard 80% floor and may not continue merely to chase the optional sampled preference.
3. During that emergency direct cleanup only, residual regions are prioritized by their actual unpaid service mass:
   each targetable cell contributes `max(0, 13 - serviced_subcells) / 13`.  Bend-plan service ranking uses the same
   physical debt rather than counting every targetable cell as one equal unit.
4. Debt bookkeeping is **stage-local and incremental**.  The region debt ledger is initialized only when emergency
   debt mode opens.  Accepted emergency direct geometry captures only the service cells it actually changes and
   subtracts the exact paid subcell amount from the affected region ledger.  Normal LOCAL coverage updates do not
   maintain a global debt ledger and therefore do not pay an easy-scale bookkeeping tax.
5. Exact geometry legality remains authoritative.  Debt weights affect only which existing legal stochastic/direct
   opportunity is considered first; they do not relax clearance, alter octilinear grammar, create geometry, or lower
   the physical service invariant.
6. If bounded debt-aware direct/fragment cleanup still cannot pay the hard floor, the existing bounded partial-service
   reserve remains available.  The optimization may reduce unnecessary broad-front generation but may not convert an
   infeasible sample into a silently under-serviced output.
7. The scaling objective is explicit: increasing logical territory may create proportionally more useful residual
   service work, but it must not create extra whole-field binary rescue waves merely because the same physical debt is
   distributed across more subcells.
## 29.14 2026-08-20 — Optimization work-mode governance

This governance refinement defines when optimization work stops for a user-facing report. It does **not** change renderer geometry, probabilities, service targets, routing semantics, or release criteria.

1. **NORMAL is the default work mode.** After one meaningful validated/promoted optimization change, the complete authoritative state is checkpointed, active optimization stops, and a report is produced before another target is started. Rejected experiments do not count as the meaningful promoted change.
2. **NIGHTLY is explicit and run-scoped.** When the user explicitly requests NIGHTLY/overnight/keep-working-as-much-as-possible execution, optimization continues across multiple meaningful promotions and across correctly earned stage transitions. NIGHTLY does not become the default for later work requests.
3. **Stage stops are not session stops.** Complexity-first and stage-gated rules remain mandatory in both modes. Once a reasoning stage has enough evidence, investigation of that stage stops and work moves to the next earned stage. In NIGHTLY this transition must not be mistaken for a reason to end the overall run.
4. **NIGHTLY checkpointing is mandatory.** Preserve a recoverable replacement-ready authoritative checkpoint after every promoted meaningful change, at major phase boundaries, before expensive/risky work when recovery would otherwise be costly, and after important forensic findings that would be expensive to reconstruct.
5. **Authority remains last-known-good.** Unproven experiments, rejected variants, or partially verified changes never overwrite the last validated/promoted renderer. Their evidence may be retained separately for diagnosis/resumption.
6. **NIGHTLY whole-phase stop invariant.** NIGHTLY may end only when the user explicitly interrupts/asks for STOP/report, or when the **entire active optimization phase is demonstrably finished optimizing**. The assistant may stop NIGHTLY on its own only for whole-phase completion. Candidate completion, rejection, promotion, stage/subtarget exhaustion, blocker/stuck/error conditions, profiling failures, tool/command timeouts, execution-window ends, detached-job waits, and resource pressure are not NIGHTLY stop conditions while the phase remains unfinished; recover/retry/switch methods and continue. **No execution-boundary exception exists; NIGHTLY self-stop is legal only at whole-phase completion.**
7. **Interruptibility is a first-class requirement.** If the user interrupts NIGHTLY work, do not begin another target. Preserve the latest authoritative checkpoint and the minimum in-flight forensic state required to resume, then report from that checkpoint.

This rule exists to prevent two opposite process failures: stopping a long NIGHTLY run after the first meaningful improvement, and continuing past a meaningful checkpoint in NORMAL mode without giving the user the requested review boundary.


## 29.15 2026-08-20 — MAIN transactional preflight defers redundant full hard audit

This refinement preserves the complete MAIN routing grammar, synchronous transaction semantics, causal repair
semantics, exact materialized acceptance invariants, and final hard-audit requirements. It changes only when an
already-proven repaired state is subjected to the next **full whole-board materialization**.

1. A transactional MAIN preflight repair is accepted only after its existing **fast rendered trial** has
   materialized the exact repaired visible trace set and verified all repair-sensitive invariants against the
   last authoritative hard-audit baseline.
2. `_repair_main_preflight_materialization()` returns both whether any repair committed and the latest exact
   rendered trial diagnostics. Those diagnostics are the authoritative repaired preflight state for the remainder
   of `_run_main_core_and_preflight()`.
3. After one or more transactional repairs have committed, `_run_main_core_and_preflight()` must **not** immediately
   perform another complete whole-board hard materialization merely to rediscover the already-proven repaired state.
   It carries the successful trial diagnostics forward instead.
4. This deferral never removes the hard acceptance audit. `run_main_only()` still performs its mandatory final full
   materialization after terminal-marker conflict repair and rechecks launch identity, persistence, exact overlap /
   clearance, static intersections, octilinear grammar, and cross-chip connection requirements before the MAIN
   network can be frozen.
5. If the fast transactional trial does not improve/repair the actual rendered state, historical rollback and hard
   failure behavior remains unchanged. No failed repair can bypass a full hard audit or become accepted geometry.
6. The optimization is deliberately **repair-regime conditional**. A healthy scale/workload with no transactional
   preflight repair performs exactly the historical materialization sequence. Finer workloads that enter the repair
   regime do not pay for an extra whole-board confirmation immediately before the already-mandatory final one.
7. Same-version deterministic geometry and behavior are unchanged. On the maintained reference seed, MAIN geometry
   hashes and tracked routing counters are bit-for-bit identical at `0.75`, `0.5`, and `0.35`; full materialization
   call count is unchanged at `0.75`, reduced `4 -> 3` at `0.5`, and reduced `6 -> 5` at `0.35`.
8. This is a scaling optimization, not an audit weakening: the removed operation is a duplicate **timing/location**
   of the same full hard audit, while the final authoritative audit remains mandatory and unchanged.

The adjacent-scale MAIN approach audit preceding this refinement also closed the approach-replacement diagnosis:
when normalized by logical territory, the core routing machinery is already near-linear and the tested broad
workflow replacements either weakened topology or worsened scaling. MAIN therefore retains its current routing
approach and proceeds to scaling-first algorithmic optimization of residual implementation/finalization work.


## 29.16 2026-08-20 — Mandatory BEFORE / AFTER optimization reporting

This governance refinement changes reporting only; it does not alter rendering behavior.

1. Every meaningful promoted optimization checkpoint must report **BEFORE and AFTER** scaling side by side.
2. For every important affected category and for the overall active phase / whole renderer as applicable, the required
   columns are **Work Growth**, **CPU Growth**, and **CPU / Work Growth**.
3. `CPU / Work Growth = CPU Growth / Work Growth`. A value of `1.000x` means linear CPU scaling with the actual
   useful/generated work of that category.
4. The required adjacent scale comparisons are `0.75 -> 0.5` and `0.5 -> 0.35` whenever those points are available.
5. The primary work denominator must be the category's real useful/generated work: emitted routing geometry, serviced
   residual area/cells, accepted components/primitives, audited geometry/checks, materialized work volume, or another
   explicitly justified natural unit.
6. Logical territory (`1/main_scale^2`) is supplementary context used to diagnose whether work generation itself is
   scaling correctly. It does **not** replace CPU/work normalization when actual work is measurable.
7. A report that contains only raw speedups, only AFTER numbers, only territory-normalized CPU, or only the scaling of
   removed work is incomplete.
8. Category results must be accompanied by an **overall** result. A category-level optimization that shifts equal or
   worse superlinearity elsewhere does not satisfy the scaling-first objective.
9. Deterministic behavior/correctness evidence remains mandatory beside the scaling table: output hashes, relevant
   behavior/work counters, and release/regression-gate status.
10. The authoritative detailed schema is `V47_OPTIMIZATION_REPORTING_STANDARD_2026-08-20.md`.

### 29.17 Mandatory complete handoff bundle on every assistant response

1. Every assistant response concerning this project must provide a downloadable complete replacement-ready repository bundle, regardless of whether a meaningful renderer change has been promoted.
2. The bundle must be refreshed before the response so it contains the latest authoritative renderer, governance/specification, tests, status, forensic findings, rejected experiments, and next continuation point.
3. This is independent of work mode: NORMAL controls when active optimization stops for review; NIGHTLY controls whether optimization continues across promotions; neither mode permits a response without a current complete handoff bundle.
4. If interrupted mid-investigation, preserve the last validated authority and package all newly established forensic evidence so the next chat can resume without reconstructing the investigation.

**2026-08-20 governance refinement:** handoff packaging is now a per-response durability requirement, not only a meaningful-change checkpoint requirement.



## 29.18 2026-08-21 — Non-negotiable NORMAL stop invariant

This governance refinement closes the execution-boundary loophole in the optimization workflow. It changes process only and does not alter renderer behavior.

1. In NORMAL mode, a rejected candidate, failed experiment, completed audit/profile, incomplete candidate, tool/command timeout, execution-window boundary, response-length concern, or identified next step is **not** a valid user-facing stop/report boundary.
2. If another evidence-backed optimization step remains, work must continue within the **same response** through as many rejected/incomplete candidates and tool invocations as necessary.
3. Tool/runtime windows are implementation details. A timed-out/expired command is retried or resumed; it must not be reframed as a project checkpoint or reason to hand off.
4. NORMAL may stop active optimization and report only after: (a) an integrated candidate clears all adjacent-scale/behavior validation, the mandatory categorized + overall BEFORE/AFTER Work Growth / CPU Growth / CPU-per-Work report, the complete active release/regression gate, and explicit **ACCEPT/PROMOTE**; or (b) the current stage is demonstrably exhausted with no defensible evidence-backed next target.
5. A blocker exception is valid only if the execution environment remains genuinely unusable for further reliable work after bounded recovery/retry attempts. A single command timeout, profiler overrun, or tool window is not a blocker.
6. Elementary ACCEPT-FOR-CONTINUATION and REJECT decisions are internal transitions. Neither authorizes a NORMAL final response while further evidence-backed work remains.
7. The complete handoff bundle remains mandatory on every response, but bundle cadence does not create extra NORMAL stop boundaries.
8. This section overrides any older repository wording that could be read to permit voluntary mid-candidate or post-rejection NORMAL handoffs because of tool/chat/execution boundaries.

### 29.19 2026-08-21 — response-boundary contract preflight
Before any user-facing PCB-project response is finalized, verify the active mode's stop condition, canonical BEFORE/AFTER scaling report shape when performance is presented, authoritative renderer status, and complete refreshed handoff bundle. In NIGHTLY, if the whole optimization phase is unfinished, the response may not self-stop regardless of tool/window/execution-boundary events. A one-sided residual ranking cannot substitute for the required categorized + overall BEFORE/AFTER scaling tables.


### 29.20 2026-08-21 — Continuous NIGHTLY checkpointing is mandatory

Checkpointing and stopping are independent. During NIGHTLY, every promoted meaningful change must immediately produce a full authoritative replacement-ready checkpoint. Coherent unpromoted implementation states and costly forensic findings must be recovery-checkpointed before the run moves past them whenever loss would require meaningful reconstruction. Major transitions and long/risky work also checkpoint. Checkpoint completion never ends NIGHTLY; execution continues until the whole active optimization phase is complete unless the user explicitly interrupts.

### 29.21 2026-08-21 — handoff preserves state, not permission to reset execution discipline
A new-chat handoff preserves repository authority, decisions, evidence, metrics, rejected experiments, and explicit process governance, but it does not make rehydration/re-audit a new optimization stage or authorize a user-facing response at a tool boundary. Rehydration is setup only. After setup, keep one evidence-backed target funnel active until rejection, full qualification/promotion, or demonstrated stage exhaustion. Tool/command/runtime boundaries are retry/resume events. The response-boundary preflight must be enforced literally rather than treated as descriptive prose.

### 29.22 2026-08-21 — recovery checkpoint preserves exact in-flight candidate
The current NORMAL recovery/conflict stage is checkpointed without changing renderer authority. The already-built transactional on-demand conflict-expansion candidate is preserved as an isolated unpromoted file and must be resumed directly rather than reconstructed. First-time conflict behavior remains symmetric; expansion is earned only for recurrent post-reroute conflicts and restores RNG state when unsuccessful. This is process/experimental state only until full adjacent-scale behavior/scaling and release qualification promotes it. See `V47_CURRENT_STATUS_2026-08-21_1720IST_CONFLICT_EXPANSION_INFLIGHT.md`.

### V47 optimization scale-qualification cadence (2026-08-21)

Optimization execution uses `main_scale=0.75` and `0.5` for ordinary candidate qualification. `main_scale=0.35` is an end-of-full-phase acceptance fixture, not an ordinary development/profiling loop. When a full optimization phase reaches final scale acceptance, execute and record `0.75`, then separately execute and record `0.5`, then separately execute and record `0.35`. This is an optimization/verification cadence rule only; it does not alter renderer geometry or scale semantics.


### Optimization status note — 2026-08-21 21:47 IST
No design-language behavior change. Current performance work is confined to residual MAIN proposal/future-option work generation and geometric scoring. Recovery/conflict policy, singleton settlement semantics, clearance semantics, transactional admission semantics, and routing behavior remain retained after rejected optimization families. Scale-development cadence: 0.75 + 0.5 only; 0.35 is end-of-phase acceptance only.

## 2026-08-21 21:56 IST — handoff-integrity recovery note
No design behavior changed. Repository governance was corrected after discovering that several optimization findings had existed only in chat context. The missing post-19:39 results are now durably recorded in `V47_HANDOFF_GAP_RECOVERY_2026-08-21_2156IST.md`. Renderer authority remains unchanged; ordinary optimization qualification remains 0.75 then 0.5 only, with 0.35 reserved for full-phase acceptance.

## Process durability amendment — 2026-08-21 22:07 IST
Repository/process changes must preserve a single canonical mutable worktree and immediate durable optimization worklog. Every user-facing project response is preceded by a verified complete checkpoint build from that canonical worktree. This is a process invariant and does not alter PCB visual behavior.


## 2026-08-21 23:01 IST — repository-state integrity / single-root governance

Process-only change; renderer geometry/behavior is unchanged. The repository now has one canonical mutable root identified by `.pcb_repo_identity.json`, duplicate-root preflight rejection, write-ahead worklog durability, an explicit active-governance allowlist/document-authority hierarchy, exhaustive Markdown authority audit, and mandatory verified `tools/build_handoff_bundle.py` packaging before every response. Historical checkpoint prose is non-governing. Ordinary optimization scale cadence remains 0.75 then 0.5 only; 0.35 is reserved for final full-phase acceptance.


## 2026-08-21 23:10 IST — duplicate worktree retirement

Process-only change; renderer behavior is unchanged. All legacy scratch repository trees in the current runtime were reconciled against canonical, unique workflow-repair artifacts were merged, and the old trees were retired. Current workflow identity is exclusively `.pcb_repo_identity.json`; duplicate roots are rejected by `tools/response_preflight.py`.


## 2026-08-21 23:14 IST — exhaustive governance reconciliation verification

Process-only change; renderer behavior remains unchanged. The final preflight audit read all 343 Markdown files, current governance is allowlisted, historical workflow statements are non-governing, duplicate repository identities are rejected, and every response bundle is built/verified from the single canonical root under neutral archive root `pcb_v47_repo/`.


## 2026-08-21 23:16 IST — single response toolchain and reconciliation closure

Process-only change; renderer behavior is unchanged. The repository has one active workflow implementation: `.pcb_repo_identity.json` + `tools/response_preflight.py` + `tools/build_handoff_bundle.py`. The obsolete alternate checkpoint/session-lock prototype is removed. Every Markdown file is read/classified by the authority audit; only the explicit active-governance allowlist may define current process. Parallel-worktree progress has been reconciled into canonical, with the two unpromoted rejected source artifacts that did not survive recorded explicitly in the reconciliation report.

## 2026-08-21 23:38 IST — Item 21 proposal-work decomposition in progress
Process/performance evidence only; no design-language behavior changed. On the unchanged authority at the governing 0.75 fixture, every requested `_proposal_variants` draw re-entered `_propose` (8,419 requested / 8,419 `_propose` calls). This is being evaluated as a candidate-generation/selection coupling issue under the approach-driven scaling pass. Ordinary cadence remains 0.75 then 0.5; no 0.35 until final MAIN-phase acceptance.

## 2026-08-21 23:40 IST — Item 21 proposal-work decomposition conclusion
Performance evidence only; no design-language behavior changed. The paired 0.75/0.5 probe showed that repeated stochastic proposal draws are approximately a scale-invariant multiplier, while legal/scored candidate work per proposal and exact geometric service work rise with density. Proposal-pool/selection decoupling is therefore retained only as a later constant-factor cleanup, not promoted as the current scaling fix. The active scaling target remains exact legal/scored candidate work generation inside MAIN proposals, with ordinary qualification at 0.75 then 0.5 only.

## 2026-08-21 23:44 IST — Item 21 proposal architecture judgment: MODIFY
Performance architecture only; governing visible rules are unchanged. Exact same-direction blocker-prefix pruning was not adopted because its removable-work fraction decreased slightly at the denser ordinary scale. The active candidate instead restructures proposal search hierarchically: all existing legal directions remain available, each direction retains the same seeded module-length candidates and blocked-length fallback opportunity, but only its first legal run length proceeds to expensive candidate scoring/selection. This is intended to remove density-sensitive Cartesian scoring breadth, not to shorten route life or weaken clearance, octilinear grammar, emergence, branching, connection, or persistence behavior.

## 2026-08-21 23:50 IST — hierarchical run-length experiment rejected; full legal breadth retained
The first-legal-run-per-direction experiment is rejected because its 0.75->0.5 CPU-per-useful-work scaling worsened (`1.2776x -> 1.4473x`) and its route feedback became scale-inconsistent. Governing behavior therefore continues to retain the complete legal direction/run-length opportunity set. The next performance candidate may reuse construction of that unchanged set across stochastic draws in one immutable proposal-variant call, but it must not remove legal route alternatives, shorten route-life opportunity, or weaken exact clearance/grammar checks.

## 2026-08-21 23:52 IST — full legal proposal-pool reuse candidate in qualification
Performance architecture only. The candidate retains every existing legal direction and run-length alternative and every exact clearance/grammar gate. It changes only when that immutable candidate set is constructed: once per `_proposal_variants` call, followed by fresh stochastic scoring/selection draws from the same complete pool. Historical RNG mapping may change, as permitted for an architectural behavior-preserving refactor; per-version determinism remains mandatory.

## 2026-08-22 00:50 IST — Item 21 future-certificate-first exact-work elimination promoted

MAIN holistic lookahead now treats a still-live future-failure certificate as the dependency it actually is: an exact proof of blockage is consulted before corridor geometry is materialized. This preserves the complete visual/routing behavior while removing geometry that could no longer influence any choice. Governing output is byte-identical at 0.75 and 0.5; exact future-corridor constructions fall by 2,768 and 7,947 respectively. This is an approach-driven scaling change: eliminate certified-impossible work rather than weaken lookahead or tune scale-specific thresholds. Production SHA is `06a1f9255ff4b6908e02e9ebcf5c76d3222c86c45246aa7d6ec48b10209aac20`; 134/134 candidate and post-promotion gates pass. Item 21 remains open for a fresh residual audit; no 0.35 until Item 22 final MAIN acceptance.

## 2026-08-22 01:40 IST — Item 21 exact regional path-clear success certificate promoted

MAIN primary proposal clearance now treats geometric locality as an exact dependency boundary for the **successful path-collision sub-proof**. An unchanged front/head may reuse a prior no-path-collision proof only when the exact set of committed path-index records returned for that corridor remains unchanged and the path-index generation is unchanged. Static clearance, source-egress, endpoint/grammar, visible-lane, gesture-budget and all other dynamic checks still execute; any local path insertion/removal or index rebuild invalidates the proof, while distant commits outside the corridor no longer force an irrelevant repeated per-record GEOS scan. This is approach-driven computational locality, not heuristic pruning. Governing output/counters remain exact at 0.75 and 0.5; `_gesture_clear` CPU/work growth improves `1.229607x -> 1.212888x` and same-harness overall MAIN improves `1.255274x -> 1.236641x`. Candidate and post-promotion gates pass 134/134. Production SHA is `a9c3f37157e078614290d7eea75a67cc45cc172da548e7c12e994a0d82421bce`. Item 21 remains open; no 0.35 until Item 22 final MAIN acceptance.


## 2026-08-22 01:46 IST — response packaging-reserve hardening

Process-only change; PCB design/rendering behavior is unchanged. A NORMAL promotion is no longer treated as a completed checkpoint at ACCEPT/PROMOTE or post-promotion test PASS alone: current authority/status documents must be synchronized and the verified complete response bundle must be built immediately afterward, with execution capacity reserved for that transaction. NIGHTLY checkpoints immediately after each promotion and continues.


## 2026-08-22 18:40 IST — scaling optimization program closure

Process/performance-status note only; PCB visual/design-language behavior is unchanged. All scaling optimization targets 1–26 are DONE. Final guarded whole-render acceptance completed on authority `8a43f6c2421e67b66f3d83a5f40dc269074a237d63eac2f183a60bad29b3b744`; final production gate is 134/134 PASS. There is no active optimization target. Any future optimization must begin from new causal evidence or explicit user direction rather than automatically reopening hotspot search. The canonical runtime root is `/mnt/data/pcb_work/v47_single_canonical`; the old `/mnt/data/pcb_work/pcb_v47_repo` runtime path is retired from authority use after external artifact rehydration contaminated it during Item 26.

## 29.19 2026-08-23 — Anti-line-murder is proactive MAIN construction, never sample acceptance

This clarification is normative and overrides any older wording that could be read as permitting a late
accept/reject policy for line survival.

1. **Prevent the doomed state during routing.** MAIN must account for local free space, sibling progression,
   and plausible future continuation while selecting/committing gestures, with particular care at emergence and
   the first few turns. A lane should not commonly emerge, take one turn, and immediately leave itself with no
   legal way to continue merely because earlier proposals ignored foreseeable local constraints.
2. **Local proposal rejection is normal.** If a candidate gesture/path would commit the lane into a foreseeably
   trapped or premature-terminal state, reject/replan that candidate locally using the existing deterministic
   proposal/conflict/clearance machinery. Do not discard unrelated valid lanes, components, or the whole board.
3. **Late murder detection is diagnostic.** Short/embedded/dead-end/line-murder checks at settlement or final
   validation are regression assertions that proactive construction failed. They are not a production quality
   filter and must not select which seeds are allowed to exist.
4. **No acceptance escape hatch.** Retry exhaustion may not make an otherwise forbidden premature/embedded
   terminal legal. Conversely, detecting such a terminal may not reject the whole sample, skip to a different
   logical seed, or start a whole-board reseed/rebuild cycle.
5. **Seed totality is complementary, not competing.** For every valid canvas/scale/seed, construction must produce
   one valid board. Ordinary failures are repaired at the causal local routing/planning operation while preserving
   unrelated valid work. Final validation remains an assertion of construction correctness.
6. **Do not substitute a broad late rescue architecture for route intelligence.** A narrowly scoped local repair
   may correct an exceptional committed defect, but the governing fix for systematic line murders is smarter
   proposal/selection before the lane becomes doomed. Evidence of many late trapped lanes is therefore evidence
   to trace backward into MAIN planning, not justification for an end-of-board acceptance/rescue campaign.

## 29.20 2026-08-23 — V48 seed-total constructive generation (MAIN line-survival subsequently closed by §29.21)

This refinement is normative. It strengthens the production contract without weakening geometry, clearance, density, or service requirements.

1. **A valid seed is an input, not an acceptance candidate.** For every valid canvas / scale / seed, ordinary production construction must proceed deterministically toward one valid board. `render_batch()` and `generate_sample()` may not discard the requested logical seed, reseed the whole board, or treat retry exhaustion as a normal quality/acceptance decision.
2. **Randomized work is a fast path, not an existence proof.** Finite stochastic proposal budgets are permitted for variety and efficiency. When an ordinary randomized budget exhausts, the causal phase must switch to a finite deterministic/local constructive completion using the same design grammar and exact validity rules. Raising a retry budget is not a seed-totality fix.
3. **Main-chip construction is total outside true invariant failure.** Procedural chip regeneration exhaustion falls through to a deterministic in-language chip constructor. Chip uniqueness is judged by exact generated geometry rather than a coarse motif/aspect signature. Stochastic placement exhaustion falls through to deterministic legal placement, including deterministic whole-Phase-A population placement before MAIN routing exists.
4. **Component construction is total outside true geometric impossibility/corruption.** Required family assignments, collection planning/generation/calibration, and residual placement retain their stochastic normal paths but have deterministic grammar-preserving completion. Component recovery may inspect finite residual-service candidates and gap-aware scales with exact component/pathway/chip clearance; an arbitrary random-attempt counter may not make the board unacceptable.
5. **LOCAL hard-floor construction is total by local debt service.** After ordinary LOCAL routing/rescue paths, remaining service debt is visited deterministically over finite residual cells. Candidate bent octilinear fillers use the same exact clearance/static-obstacle rules and commit only legal geometry. The deterministic sweep is exceptional completion proportional to actual residual debt, not a board-wide reroll mechanism.
6. **Hard visual/service requirements stay hard.** The seeded 50–60% component service target and 80–90% remaining-service LOCAL target are construction requirements. V48 does not redefine a shortfall as acceptable merely to preserve the seed. If exhaustive exact-legal construction still cannot satisfy a required invariant, that is a construction/design-language defect to diagnose—not an acceptance-rate outcome.
7. **Work ceilings cannot secretly become acceptance ceilings.** Global gesture-check/candidate counters may remain as telemetry, diagnostics, or bounded normal-path work controls only when the underlying construction is otherwise finite. Their exhaustion alone cannot reject a requested seed.
8. **Final validation is an assertion.** Exact octilinearity, clearance, replay determinism, launch accounting, hard floors, and other final invariants remain mandatory. A final failure means construction produced an invalid state and must be fixed at its causal phase; it is never permission to spin another seed.
9. **MAIN line-survival is part of seed-total construction.** The formerly deferred `persistence horizon unresolved` / MAIN materialization-survival family is governed by §29.21's proactive first-rebase fairness / atomic residual structural settlement and §29.22's hard-four/soft-six progress-driven true-final relational settlement. Those failures remain programmer/construction defects if they recur; they may never be hidden, downgraded, or rerolled.
10. **Required regression style.** Seed-totality regressions should deliberately force former stochastic ceilings to zero/tiny values where practical and prove deterministic constructive completion, rather than merely demonstrate that a larger random budget usually succeeds.

## 29.20.1 2026-09-04 — User controls for total residual density and component/LOCAL mix

This current V48 control extension supersedes fixed residual target wording only when either new density control is moved away from its exact default. It does **not** change MAIN behavior, component/LOCAL geometry grammar, clearances, seed totality, or phase order.

- `local_density` is `[0,1]`, default `1.0`, and scales the seed's historical combined post-MAIN residual-service budget.
- `component_density` is `[0,1]`, nominal default `0.5898123324396783`, and divides that common budget between components and LOCAL lines.
- The default value is the midpoint-convention share `0.55/(0.55+0.45*0.85)`.
- The **exact default pair is behavior-preserving**: old seeded `50–60%` component and `80–90%` remainder-LOCAL draws are used exactly, with no extra RNG consumption.
- `local_density=0` emits no residual components or LOCAL lines. `component_density=0` assigns the residual budget to LOCAL; `component_density=1` assigns it to components.
- Density requests are best-effort above the established hard phase floors. Exact geometry is never weakened to force an extreme mix, and new higher knob targets do not become new superlinear hard-floor obligations.
- The report exposes requested total residual budget, component allocation, LOCAL allocation, actual combined residual service, and actual realized component share.

## 29.21 2026-08-24 — Proactive first-rebase fairness and atomic residual structural settlement

This refinement is normative and closes the separately tracked MAIN line-murder family without weakening §29.19 or seed totality.

1. **A viable newborn structural child may HOLD instead of being murdered by arbitration.** For a non-local child in `STRUCTURAL_TRANSITION` at `branch_stage == 0`, the first mandatory rebase remains subject to ordinary same-round conflict arbitration. If it loses that first conflict but already has at least one exact future option, it may remain at its clean head and re-propose rather than being rolled back solely because a sibling won the round.
2. **Fairness begins only after one real HOLD.** A newborn receives no unconditional first-conflict priority. After it has been held once, the next first-rebase arbitration includes one-round anti-starvation fairness so an otherwise viable child is not repeatedly denied by the same local competition. The fairness state resets immediately when that first rebase commits.
3. **Fairness never relaxes geometry.** Eligibility requires exact future viability. Octilinearity, source egress, lane order, static/path clearance, turn grammar, and conflict geometry are unchanged. Fairness chooses among already-legal proposals; it never makes an illegal move legal.
4. **Residual structural persistence is a shared-snapshot transaction.** Late residual structural fronts must not be advanced sequentially one front at a time. They propose from one committed snapshot, are grouped by exact conflicts, and commit only a mutually compatible subset atomically. Incompatible peers explicitly HOLD and may re-propose against the next committed snapshot.
5. **No sequential late sibling bypass.** A residual helper may not commit a sibling move that ordinary same-round arbitration would have rejected against a peer merely because that peer has not yet been visited in a loop. This rule exists specifically to prevent render-only same-family crossings that final preflight would otherwise have to shorten away.
6. **Bounded unresolved decorative intent may be cancelled only on a valid mature prefix.** If bounded shared-snapshot settlement leaves mutually incompatible mature branch-turn intent and the lane already owns the required clean visible journey with no source-egress/fan debt, only the unmaterialized turn preference may be cleared. Existing valid visible geometry is preserved; no crossing, late corpse legalization, or whole-seed rejection follows from the cancellation.
7. **Rendered visible route length is the line-survival observable.** `pathway_main_outcome_by_trace` after marker clipping/backoff and final preflight is authoritative for short-route regression reporting. Logical travel alone must not be mixed with rendered-length histograms.
8. **Late repair remains a guard, not the architecture.** Final preflight may still assert/repair an exceptional defect, but the promoted construction is expected to avoid the systematic first-rebase starvation and sequential residual-sibling defects upstream. A recurrence is evidence to trace back into MAIN, never permission to reject or reroll the board.


## 29.22 2026-08-25 — Long/fine MAIN persistence totality: hard-four / soft-six and progress-driven final residue

This refinement is normative and closes the `1:6 @ 0.35` persistence-totality defect discovered after §29.21. It does **not** weaken line-survival, clearance, octilinearity, or seed ownership.

1. **Work debt and validity debt are distinct.** A MAIN launch below the preferred **6 visible modules** still deserves late routing work. Missing six is not, by itself, a reason to reject a board once the route has met the true **4-module hard launch-survival floor**. Hard validity debt remains: below-four visible survival, uncleared source egress, pending required fan/fragment birth, unfinished required branch transition, or unresolved live-family relational embedding.
2. **The six-module target remains a quality target.** Normal/shared persistence and the bounded young-survival beam continue trying to carry mature routes to six visible modules. A 4–6-module terminal is therefore diagnostic quality debt and should remain observable. It is not silently redefined as ideal; it simply cannot invalidate an otherwise legal requested seed solely for missing the preference.
3. **A fixed persistence clock may schedule work but may not decide validity.** After all existing bounded final cleanup, any remaining mature singleton MAIN lane whose only hard debt is sibling/family embedding enters true-final relational settlement. The renderer must not raise merely because a global tick count expired while an exact legal ordinary continuation still exists.
4. **True-final relational settlement is progress-driven and shared-snapshot.** Residual lanes propose ordinary exact straight/±45 gestures from one committed snapshot. A deterministic conflict-clean compatible subset commits atomically; held lanes re-propose against the next snapshot. Settlement continues while real legal movement is committed and relational debt remains. There is no aspect-ratio exception, seed retry, or correctness-affecting tick budget.
5. **Zero-proposal residue is geometric exhaustion, not clock failure.** If no residual lane has any exact legal ordinary proposal, the state is handed to the existing coordinated visible-cohort terminal arbitration. Exhaustion does not legalize a route below the hard four-module floor or with unfinished source/fan/fragment/branch debt.
6. **Placement of the mechanism is hard.** Progress-driven settlement runs only at the **true final residue point**, after ordinary/shared persistence, young-survival repair, structural settlement, escape opportunities, and stalled-family cleanup. Running it earlier over hundreds of transient sibling-embedded fronts is forbidden; that was an explicitly rejected prototype because it turned exceptional completion into a broad late routing phase.
7. **Seed ownership remains exact.** `1:6 @ 0.35` is not a special case. The same rules apply to every valid aspect/scale/seed. More territory may increase work and memory, but it may not make correctness probabilistic or permit whole-board reseeding.
8. **Performance is qualified separately from correctness.** The long/fine regime may be expensive, but a totality fix is not accepted if it materially worsens normalized scaling. The promoted source passed the ordinary 0.75 -> 0.5 gate and a fresh same-host 0.5 -> 0.35 recheck; the earlier apparent fine-scale regression was timing contamination.

## 29.23 2026-08-25 — LOCAL hard-floor reserve is one debt campaign; exact first-leg proofs may be reused

This is a performance/locality refinement of the existing LOCAL 80–90% service contract. It does not weaken the hard 80% floor, the sampled normal preference, candidate geometry, exact clearance, or seeded ownership.

1. Once ordinary LOCAL routing and bounded broad hard-floor rescue have finished, the partial-service reserve treats the remaining unpaid field as **one debt campaign**, not as permission to reopen and re-score the same whole field in several independent stochastic campaigns.
2. The campaign preserves the historical total source opportunity (`partial rescue cap × ordinary wave source cap`) but admits/scans the unpaid candidate field once. Exact local source ranking, routing grammar, conflict handling, clearance, and service accounting remain authoritative.
3. If the one stochastic debt campaign does not pay the hard floor, deterministic exact-legal debt completion remains the construction backstop. Correctness never depends on receiving a second or third randomized whole-field campaign.
4. Inside deterministic two-leg completion, when several second-leg alternatives share an identical cell/source/first-direction/first-length first leg, the exact first-leg legality result may be reused. Every distinct second leg still runs its ordinary exact clearance check, in the historical candidate order, and first-success semantics are unchanged.
5. Rescue-work elimination may remove failed/non-visible stochastic sources, but may not thin the actual design language. Qualification must preserve the physical 80% floor, bent-dominant/local articulation constraints, straight-visible cap, motif ratios within ordinary stochastic variation, and comparable visible residual coverage.
6. This scheduling/cache policy is scale- and aspect-independent. It exists to make LOCAL work proportional to unpaid service/actual geometry rather than to the number of times the same field is revisited.

## 29.24 2026-08-27 — Residual-fill spatial mosaic and bounded mixed cluster language

This section is normative and supersedes any older residual wording that can be read as permitting macroscopic
component-only and LOCAL-line-only territories merely because components are generated before LOCAL routing.
Generation order remains component-first for exact collision ownership; **spatial composition ownership is shared**.

1. **Residual fill is a spatial mosaic, not two territorial phases.** After MAIN freezes, the remaining usable field
   must be serviced as many compact spatial composition parcels. Components may still be physically admitted before
   LOCAL lines, but the first phase may not claim one macroscopic connected room as a component country and leave a
   different macroscopic room as a line country. Both languages must remain distributed across the board-scale
   residual territory, subject to exact geometry and genuine negative-space constraints.
2. **Component cluster cardinality has full seeded support from 1 through 12.** Singular components are normal
   outcomes; small and medium clusters are common; genuinely large clusters of roughly 10--12 remain normal but
   minority outcomes. A connected residual room can and normally should contain several independent clusters rather
   than being represented by one unbounded colony.
3. **LOCAL groups have varied, physically bounded capacity.** Root counts follow seeded probabilities and feasible
   route-domain area; they may exceed twelve roots, as explicitly authorized. Each source and descendant retains one
   connected composition domain. The public area-scaled population ceiling and exact route gates remain governing.
4. **Cluster size distributes authorized work.** Seeded size targets distribute component opportunities and LOCAL
   source opportunities according to local feasible capacity. Larger groups do not authorize broader route searches,
   relaxed constructors, lowered service floors or weaker clearance. Public work ceilings, octilinear grammar and
   the cached local collision architecture remain governing.
5. **Completion retains composition ownership.** Component recovery and completion use ordinary seeded 1--12
   member clusters, canonical constructors and original substantial-region quotas. LOCAL debt sources belong to the
   same physically bounded domains as ordinary sources; completion may not bypass exact ownership or clearance.
6. **Mixing is macroscopic, not forced microscopic alternation.** Components and LOCAL lines do not need to alternate
   token-by-token, and exact obstacles may create naturally one-sided pockets. The forbidden outcome is systematic
   board-scale segregation produced by scheduler ownership. On open sparse boards, multiple component and LOCAL
   clusters must be represented across the same broad residual territory.
7. **Existing fill percentages remain governing.** Components still service the existing 50--60% post-MAIN residual
   target and LOCAL still services 80--90% of the remaining service budget. The mosaic changes distribution, not the
   amount of requested residual workload.
8. **Efficiency must remain workload-proportional.** Parcel construction/allocation must be linear or near-linear in
   residual cells, parcels, and admitted sources. No all-pairs component/LOCAL coordination, whole-board rescoring per
   source, or new global placement/routing search is permitted to satisfy the visual rule.
9. **Cross-chip connection remains opportunistic success, never a board quota.** A geometrically legal foreign-main-
   chip connection, when encountered, immediately counts as successful route completion regardless of remaining MAIN
   journey target. A valid board is not required to manufacture at least one foreign-chip encounter. Zero realized
   cross-chip joins is valid when no legal encounter occurs, including sparse/short-run boards.
10. **Cluster anchors must remain dispersed.** Shared composition uses independent physical x/y parcel counts,
    with seeded component/LOCAL allocation inside small neighboring parcel groups. This supersedes the fixed 8x8
    scheduler. Component center cores locate clusters; their selected tiles contain complete canonical glyphs.
    Prepared and completion placement use cluster-count-first local load. After components freeze, actual cluster
    hulls remain protected and unused reservation fringe returns to LOCAL routing opportunity.

## 29.25 2026-09-27 ? Shared residual construction and final visible service

This refinement is normative. It preserves MAIN, phase order, exact seed ownership, canonical component grammar,
octilinearity and every clearance. It supersedes older LOCAL root caps and density-floor wording where stated.

1. **Accounting and opportunity are separate.** The canonical post-MAIN service denominator is immutable. Policy
   seams and route exclusions may not shrink it. The LOCAL numerator is the union of final emitted flat-cap stroke
   service ribbons, including only the legitimate exclusion perimeter, sampled at the established 4x4 subcell mask.
   Planned paths, suppressed traces and markers do not manufacture service. Recount final visible geometry.
2. **Ordinary construction retains the default language.** LOCAL targets attract less strongly than MAIN; singleton
   branching uses the public area-scaled population cap. Source/target scheduling uses local chunk pools, heaps and
   spatial indexes rather than whole-board scans or all-pairs coordination. Raster room labels nominate proposals;
   exact frame, composition, static, route and marker predicates decide geometric legality.
3. **Higher requested LOCAL work receives early capacity construction.** Exact legal bent visible packages reserve
   feasible service before ordinary routes fragment corridors. Seeded ordinary gauge/special draws, compatible
   affinity, branching and tails realize that capacity through bounded local transactions. A replacement must preserve
   the original packet's service bits; rejected local replacements retain their certificate. Minimum logical/visible
   length comparisons use the existing numerical tolerance. Filled certified terminals may reach their proven prefix
   without a fictitious hollow clip; genuinely hollow markers retain the full clipping reserve.
4. **Construction and final marker guards share exact circle spacing.** Logical terminal indexes carry centers and
   radii. Admission uses the same analytic circle predicate as final cleanup; faceted disc distance cannot certify
   a pair that the final guard would delete. Existing exact static, stroke, marker and ownership gates remain active.
5. **Density semantics remain explicit.** Exact default mixed settings retain a hard 80% LOCAL remainder floor and
   seeded 80--90% preference. Nondefault LOCAL floors cap the full-density floor before multiplying by `local_density`.
   All-LOCAL density 0.9 therefore requires 0.72 absolute service; density 0.5 requires 0.4. Only the exact full-density
   all-LOCAL endpoint (`local_density=1`, `component_density=0`) uses best-effort 80%: construction must generally reach
   it and any misses remain close, with true achieved service and shortfall reported. This approval does not weaken
   reduced-density floors, default floors, geometry or seed ownership. Finite qualification is not seed-totality proof.
6. **Work must remain proportional to opportunity and visible output.** Preserve cached exact first legs, incremental
   service masks, bounded spatial queries and chunk scheduling. Do not raise retries, rescore the board per source,
   repeat full debt campaigns, or add aspect/scale-specific modes to obtain a passing fixture.
