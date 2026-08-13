# v7 — Capacitor singleton correction

- `capacitor_circle` no longer uses ordinary entity-count or lattice generation.
- One capacitor-family occurrence inside a collection now produces exactly one capacitor entity.
- Capacitors are forbidden from strip, chain, orthogonal-grid, diagonal-grid, and staggered-grid generation.
- Multiple isolated capacitors remain allowed, but each is placed independently with full secondary-component clearance.
- Added regression coverage for singleton collection capacitors and non-overlapping multiple isolated capacitors.
- Five-sample smoke audit confirmed collection capacitor entity count equals collection capacitor group count and zero reported clearance violations.
