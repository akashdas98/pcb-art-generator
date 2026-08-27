#!/usr/bin/env python3
"""Authoritative V43 release-test runner.

A V43 release is not a pass unless this command exits 0. It validates that the discovered
active suite exactly matches the checked-in manifest, rejects hidden skips/expected failures,
and then runs every active test.
"""
from __future__ import annotations
import ast
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
ACTIVE=ROOT/'tests'/'active'
MANIFEST=ROOT/'tests'/'ACTIVE_TEST_MANIFEST.json'


def discovered_test_names():
    names=[]
    for path in sorted(ACTIVE.glob('test_*.py')):
        tree=ast.parse(path.read_text(),filename=str(path))
        for node in tree.body:
            if isinstance(node,ast.ClassDef):
                for child in node.body:
                    if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef)) and child.name.startswith('test_'):
                        names.append(child.name)
            elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test_'):
                names.append(node.name)
    return sorted(names)


def main():
    manifest=json.loads(MANIFEST.read_text())
    expected=sorted(manifest['tests'])
    actual=discovered_test_names()
    if actual!=expected:
        print('ACTIVE TEST MANIFEST MISMATCH',file=sys.stderr)
        print('missing from files:',sorted(set(expected)-set(actual)),file=sys.stderr)
        print('missing from manifest:',sorted(set(actual)-set(expected)),file=sys.stderr)
        return 2
    loader=unittest.TestLoader()
    suite=loader.discover(str(ACTIVE),pattern='test_*.py',top_level_dir=str(ACTIVE))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    bad=(len(result.failures)+len(result.errors)+len(result.skipped)+len(result.expectedFailures))
    if bad or not result.wasSuccessful():
        print(f'RELEASE GATE FAILED: failures={len(result.failures)} errors={len(result.errors)} '
              f'skips={len(result.skipped)} expected_failures={len(result.expectedFailures)}',file=sys.stderr)
        return 1
    print(f'RELEASE GATE PASS: {result.testsRun}/{len(expected)} active tests passed; 0 failures/errors/skips/xfails.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
