# Recovery checkpoint — 2026-08-25 16:28 IST

- Authoritative production renderer SHA-256: `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`.
- No renderer candidate is promoted or currently active.
- Cached joint-future branch remains evidence only and is NOT ACCEPTED (`1.3843x` normalized CPU/work vs production `1.3752x`).
- Current-host rerun of unchanged cached control at `0.5 / seed 104` failed to complete even after expanding the foreground command boundary. Do not reinterpret this as a renderer regression; earlier durable formal records remain authoritative for the branch.
- No renderer process survived the interrupted turn.
- Resume MAIN-1 with a deterministic smaller MAIN-only recovery-topology proxy. Proxy results may guide candidate design only; governing 0.75/0.5 seeds 102+104 qualification is still mandatory before promotion.
