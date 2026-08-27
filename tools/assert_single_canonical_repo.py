#!/usr/bin/env python3
"""DEVELOPMENT safety invariant: exactly one writable/canonical PCB repository state.

This is intentionally the *only* workflow/governance check implemented in Python.
All optimization-method, reporting, cadence, and handoff rules are prose-governed.
"""
from __future__ import annotations

from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = ROOT / '.pcb_repo_identity.json'


def fail(msg: str) -> None:
    raise SystemExit(f'FAIL: {msg}')


def main() -> int:
    if not IDENTITY.is_file():
        fail('missing .pcb_repo_identity.json in canonical repository')
    ident = json.loads(IDENTITY.read_text(encoding='utf-8'))
    rid = ident.get('repository_id')
    if not rid:
        fail('repository identity has no repository_id')

    # 1) If this runtime root has Git metadata, Git itself must expose only this worktree.
    # Replacement-ready handoff roots intentionally may omit .git; in that case the durable
    # repository identity scan below is the authoritative duplicate-state guard.
    git_checked = False
    try:
        subprocess.check_output(
            ['git', '-C', str(ROOT), 'rev-parse', '--is-inside-work-tree'],
            text=True,
            stderr=subprocess.STDOUT,
        )
        git_checked = True
    except subprocess.CalledProcessError:
        pass
    if git_checked:
        try:
            out = subprocess.check_output(
                ['git', '-C', str(ROOT), 'worktree', 'list', '--porcelain'],
                text=True,
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as exc:
            fail(f'git worktree inspection failed: {exc.output.strip()}')
        worktrees = [
            Path(line.split(' ', 1)[1]).resolve()
            for line in out.splitlines()
            if line.startswith('worktree ')
        ]
        if worktrees != [ROOT.resolve()]:
            fail('parallel Git worktrees detected: ' + ', '.join(map(str, worktrees)))

    # 2) A copied canonical repo carrying the same durable identity is always forbidden.
    matches = []
    for p in Path('/mnt/data').rglob('.pcb_repo_identity.json'):
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        if data.get('repository_id') == rid:
            matches.append(p.parent.resolve())
    uniq = sorted(set(matches))
    if uniq != [ROOT.resolve()]:
        fail('duplicate canonical repository identities detected: ' + ', '.join(map(str, uniq)))

    mode = 'git-worktree + durable-identity' if git_checked else 'durable-identity (handoff root has no .git metadata)'
    print(f'PASS: single canonical repository only: {ROOT} [{mode}]')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
