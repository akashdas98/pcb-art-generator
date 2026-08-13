# CHANGELOG V12 PATHWAY COVERAGE AND CONNECTIONS

- Increased pathway coverage by pushing branches to travel longer before termination.
- Increased turn frequency so pathways explore the board more actively.
- Added stronger **parallel emergence / early exploration** behavior: freshly emerging bundles are not immediately blocked by existing pathway occupancy during their early travel phase.
- Strengthened pathway-to-pathway near-connection behavior, including denser anchor sampling and a larger near-connection envelope.
- Added `escape` behavior so a substantial fraction of pathway descendants continue toward an off-canvas exit instead of terminating on-board.
- Reduced split eagerness so individual traces can run farther before subdividing again.
- Increased maximum route length and reduced direct termination bias.
