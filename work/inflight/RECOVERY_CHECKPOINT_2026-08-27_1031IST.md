# V48 recovery checkpoint — 2026-08-27 10:31 IST

## Authority / promotion state

- **Authoritative promoted baseline:** the repository from `pcb-art-generator_V48_CLEAN_2026-08-26_2246IST(1).zip`.
- **Unpromoted current renderer candidate:** baseline plus `work/inflight/evidence/20260826_wide_fragment_side_progress_candidate.diff`.
- Candidate renderer SHA-256 after exact diff reconstruction: `03e25cbf3ac46f86dced3822cbfa29e526b576499adacb0cf30684e329cf297d`.
- **Correctness remains OPEN. Do not treat this candidate as promoted or release-qualified.**

## Preserved findings from the interrupted run

Exact failing production sample mapping:

- base seed: `8528317405406420078`
- sample seed: `9409060408987575905`
- canvas/aspect: `1:6`
- `main_scale=0.35`

The failure was localized to two 13-lane MAIN buses fragmented at the hard horizon. Wide fragments (>4 lanes) bypassed the existing short-future proof; all singleton siblings could then settle/terminalize before any lane established the 8-module side-progress obligation.

The unpromoted candidate adds a bounded, proactive wide-fragment side-progress leader and protects that trace from render-time terminal backoff below 8 modules. It **does not remove or lower the ordinary 4-module minimum.**

Frozen exact-board evidence on the preserved candidate:

- stalled sides: `2 -> 0`
- root `[74,1,left]` leader rendered: `8.154822` modules
- root `[81,2,bottom]` leader rendered: `8.000000` modules
- MAIN short terminations: `0`
- unaccounted launches: `0`
- illegal turns/intersections/overlaps/clearance violations: `0`

Preserved evidence:

- `work/inflight/evidence/exact_seed_9409060408987575905_wide_fragment_candidate_check.json`
- `work/inflight/evidence/20260826_wide_fragment_side_progress_candidate.diff`

The interrupted run reported an active release gate of `168/168 PASS` plus geometry stress `1/1 PASS`, after adding two permanent regressions. **Those exact test-source edits did not survive in the available filesystem artifacts and therefore are not falsely reconstructed here.** The baseline test source in this recovery bundle is unchanged from the uploaded 22:46 IST package. Any recreated regression tests must be treated as new work and reviewed explicitly.

A fresh from-scratch replay of the exact production board had been launched on the candidate and was still in MAIN construction with no exception at the interruption (~3m55s elapsed). It did **not** complete, so the candidate was not promoted.

## Mandatory next action after this freeze bundle

1. Recreate the two regression tests from the preserved failure semantics (as new work, not claimed byte-identical recovery).
2. Run the ordinary release/stress gates.
3. Run the fresh exact-seed `1:6 @ 0.35` reconstruction through completion.
4. Promote only if the complete from-scratch board and full gates pass.
5. Then update authority docs/changelog and package a fresh complete handoff bundle.
