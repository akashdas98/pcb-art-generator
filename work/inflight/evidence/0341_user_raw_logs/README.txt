Raw logs from pcb-art-generator_V48_CLEAN_2026-08-25_0341IST(1).zip
Request: 2 samples, aspect ratio 1:6, scale 0.35

These attempts did NOT raise a Python exception before being terminated / hitting the execution boundary.
Therefore the raw stderr files are empty, and no renderer JSON summary was flushed to stdout before termination, so the captured stdout-summary files are also empty.

Included attempts:
- initial_count2: exact CLI --aspect-ratio 1:6 --scale 0.35 --count 2
- seed_0: exact CLI --aspect-ratio 1:6 --scale 0.35 --count 1 --seed 0
- seed_1: exact CLI --aspect-ratio 1:6 --scale 0.35 --count 1 --seed 1
- seed_1_foreground: earlier exact seed-1 foreground attempt, where present

No SVG or *_report.json was emitted by these attempts before termination.
