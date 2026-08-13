# CHANGELOG V8 PATHWAYS

- Added variance-driven pathway generation.
- Pathways originate from main chips as tightly packed bundles.
- Routing is quantized to 8 directions with 45-degree incremental turns.
- Bundles can split into sub-bundles, connect to other pathways, or terminate with filled/hollow circular endpoints.
- Pathways are generated after board placement so they are occupancy-aware.
- Pathways are rendered beneath the other entities in SVG export.
