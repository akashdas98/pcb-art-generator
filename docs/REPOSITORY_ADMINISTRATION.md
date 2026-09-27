# Repository Administration Mode

Use this mode for **pure version-control / repository housekeeping on an already-existing project state**. It is intentionally separate from DEVELOPMENT.

## Typical requests

Examples include:
- `git status`, `git diff`, `git log` / history inspection;
- stage / unstage files;
- commit or amend an already-prepared change;
- create/delete ordinary branches or tags;
- inspect/configure remotes;
- fetch, pull, merge, or rebase existing repository history;
- push commits/tags or otherwise sync to a remote.

## What this mode does NOT trigger

A pure repository-administration request does **not** automatically run:
- `tools/assert_single_canonical_repo.py`;
- release tests or stress tests;
- benchmark/qualification suites;
- `tools/build_handoff_bundle.py`;
- DEVELOPMENT missed-handoff recovery.

The single-canonical-repository guard exists to prevent competing writable project states during **development work**. It is not a prerequisite for committing or pushing the current state.

## Boundaries

Repository Administration must not silently become source/spec development.

- If the requested task requires changing renderer code, tests, specifications, behavior docs, or other project content, route that work to **DEVELOPMENT** first.
- If one request says “fix X, then commit and push,” it is DEVELOPMENT while X is being changed/qualified; commit/push is merely the administrative tail after qualification.
- Do not create a second canonical worktree/repository as an administrative convenience. A request specifically about adding/moving/removing Git worktrees touches the project's single-canonical-state policy and must be handled explicitly rather than treated as an exemption.
- Ordinary Git metadata writes (index, commit objects, refs, remote updates) are expected in this mode and are not renderer/repository-content development by themselves.

## Stop rule

Perform the requested administration, report the result, and stop. Do not add tests, qualification, packaging, or renderer work unless the user also requested them.
