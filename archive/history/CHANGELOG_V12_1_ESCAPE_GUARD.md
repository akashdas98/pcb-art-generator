# CHANGELOG V12.1 ESCAPE GUARD

- Fixed a control-flow bug in pathway escape handling where `gkind` could be read before assignment when `goal` was `None`.
- The fix adds only the missing `goal is not None` guard.
- No generation probabilities, geometry rules, seed derivation, or pathway behavior were otherwise changed.
