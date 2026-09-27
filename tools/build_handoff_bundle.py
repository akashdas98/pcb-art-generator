#!/usr/bin/env python3
"""Build and verify a lean replacement-ready repository handoff ZIP.

The builder deliberately does not write benchmark metadata, checksum manifests, or other
handoff artifacts back into the canonical repository. Canonical source should remain source.
"""
from __future__ import annotations

from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = ROOT / '.pcb_repo_identity.json'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def include(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith('.git/') or rel.endswith('.pyc') or '/__pycache__/' in '/' + rel:
        return False
    return path.is_file()


def main() -> int:
    subprocess.run(
        [sys.executable, str(ROOT / 'tools' / 'assert_single_canonical_repo.py')],
        check=True,
        cwd=ROOT,
    )
    identity = json.loads(IDENTITY.read_text(encoding='utf-8'))
    root_name = identity.get('bundle_root_name', 'pcb_v48_repo')
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
    stamp = now.strftime('%Y-%m-%d_%H%MIST')
    bundle_dir = Path(tempfile.gettempdir()) if os.name == 'nt' else Path('/mnt/data')
    out = bundle_dir / f'pcb-art-generator_V48_CLEAN_{stamp}.zip'

    files = [p for p in sorted(ROOT.rglob('*')) if include(p)]
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for p in files:
            z.write(p, arcname=f'{root_name}/{p.relative_to(ROOT).as_posix()}')

    critical = {
        f'{root_name}/.pcb_repo_identity.json',
        f'{root_name}/AGENTS.md',
        f'{root_name}/CONTEXT.md',
        f'{root_name}/README.md',
        f'{root_name}/CHANGELOG.md',
        f'{root_name}/chip_design_language.md',
        f'{root_name}/pcb_v48_renderer.py',
        f'{root_name}/generate_pcb.py',
        f'{root_name}/docs/PRODUCTION_USE.md',
        f'{root_name}/tools/assert_single_canonical_repo.py',
        f'{root_name}/tests/ACTIVE_TEST_MANIFEST.json',
        f'{root_name}/work/inflight/README.md',
        f'{root_name}/docs/LINE_MURDER_PROMOTION_HISTORY.md',
    }
    with zipfile.ZipFile(out) as z:
        bad = z.testzip()
        if bad:
            raise SystemExit(f'FAIL: corrupt ZIP member: {bad}')
        names = set(z.namelist())
        missing = sorted(critical - names)
        if missing:
            raise SystemExit(f'FAIL: handoff missing critical files: {missing}')
        leaked = [n for n in names if any(part in n for part in (
            '/bench_results/', '/bench_variants/', '/forensics/', '/experiments/', '/acceptance_'
        ))]
        if leaked:
            raise SystemExit(f'FAIL: transient optimization debris leaked into handoff: {leaked[:5]}')

    receipt = {
        'zip_path': str(out),
        'zip_sha256': sha256(out),
        'zip_bytes': out.stat().st_size,
        'repository_file_count': len(files),
        'renderer_sha256': sha256(ROOT / 'pcb_v48_renderer.py'),
        # Active candidate authority is recorded explicitly in work/inflight/README.md.
        # Do not infer activity merely from the presence of retained rejected/probe sources.
        'inflight_renderer_candidate': None,
        'line_murder_promotion_history_sha256': sha256(ROOT / 'docs/LINE_MURDER_PROMOTION_HISTORY.md'),
        'single_canonical_repo_check': 'PASS',
    }
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
