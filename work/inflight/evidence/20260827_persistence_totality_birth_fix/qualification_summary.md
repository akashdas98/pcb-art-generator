# 2026-08-27 persistence-totality topology-birth / rollback-floor qualification — PROMOTED

## Trigger
Three of five user production runs from the 12:33 promoted V48 authority threw `MAIN persistence horizon unresolved`. The three raw logs are retained verbatim in this directory.

## Failure classes
- sample seed `1638463186752876422`: under-survival sibling-entrapment residue;
- sample seed `13995978127231202083`: under-survival sibling entrapment plus fragment embedding;
- sample seed `3524258640260304746`: under-survival `branch_stage` residue.

These were not bad seeds. They exposed one persistence-totality family: young topology could be created correctly and later leave, or be rewound back into, an impossible under-four-module state that the finite final horizon could only assert about.

## Causal corrections
1. **No under-floor recovery fragmentation.** A non-local MAIN family whose shortest materialized lane is still below the unchanged four-module survival floor cannot be recovery-fragmented into singleton children. Recovery fragmentation may not export unresolved survival debt into sibling topology.
2. **Young branching is transactional.** A normal MAIN branch created below four modules must atomically prove and commit every child's structural birth maneuver, prove all physical child lanes reach >=4 modules, and prove the sibling tails are mutually legal before the parent topology is replaced.
3. **The structural certificate is a traceback floor.** The exact transactional fan/young-branch maneuver that makes child topology valid becomes that child's `recovery_floor_segments`. Later ordinary traceback may reroute geometry after the certificate, but cannot erase the certificate while leaving the child topology alive. This closes the exact run-5 recurrence where a correctly born ~5.57-module fan child could previously be rewound to ~1 module with `branch_stage=0`.
4. Future persistence exceptions report `sample_seed`, aspect ratio, and scale. The supplied logs predate this diagnostic and therefore do not prove their invocation geometry.

The ordinary MAIN per-line survival floor remains **4 modules**. No four-module straight lock was restored, no clearance was relaxed, no validator acceptance filter was added, and no safe-seed/whole-board retry mechanism was introduced. The separate >=8-module side-progress obligation remains one physical outcome per launch side.

## Qualification
Final renderer SHA-256: `9541c2f62cf9afccf3388eac6b929d7dd9437c19d04acb600855e61175bd1b42`.

- active test manifest SHA-256: `8d6b41c4381438ea16a79153ecdaa233de32924c8163578e5d09bde5b232a4bd`;
- active test source SHA-256: `77effc4418629da2c06bf41a504ed45a3887915c707d1b9d6d5da15d7f491ee6`;
- release gate after the rollback-floor correction: **178/178 PASS**, zero failures/errors/skips/xfails;
- maintained geometry stress: **1/1 PASS**;
- exact user-failing sample seed `1638463186752876422`, MAIN-only at the explicitly **inferred** reproduction geometry `1:6 @ 0.35`: **PASS** in 463.067 s, 4,109/4,109 launches visible, zero unresolved persistence, zero stalled sides, zero short terminations, zero unaccounted launches;
- exact user-failing sample seed `13995978127231202083` under the same inferred reproduction geometry: **PASS** in 367.804 s, 4,091/4,091 visible, all four hard counts zero;
- exact user-failing sample seed `3524258640260304746` under the same inferred reproduction geometry: **PASS** in 441.910 s, 4,084/4,084 visible, all four hard counts zero.

The aspect/scale above remain explicitly labeled **inferred**, because the user's three raw ZIPs contained stdout/stderr only and no invocation arguments. The sample seeds and original failure diagnostics are exact.

## Decision
**ACCEPT / PROMOTE.** All three user-failing sample seeds are closed on one byte-identical renderer after the complete regression + maintained-stress gate. There is no active renderer candidate. Any future valid-seed construction exception reopens correctness immediately under seed totality.
