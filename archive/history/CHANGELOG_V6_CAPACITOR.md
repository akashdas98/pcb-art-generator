# V6 Capacitor Entity Update

- Replaced the former collection-only `ring_circle` treatment with a distinct `capacitor_circle` entity.
- Increased continuous radius range to 4.2U–10.0U before collection scaling.
- Rendering states: filled 0.32, hollow 0.28, concentric-ring 0.40.
- Concentric inner-ring count is derived from a continuous driver; no ring-count lookup table.
- Collection-family sampling weight raised to 1.30 so the entity is visibly represented in the mix.
- Added independent isolated occurrence path: 0.72 probability per sample; count 1–3 derived from a continuous intensity driver.
- Isolated capacitors use the same secondary spread-biased placement logic and the same 18U/12U pair clearances.
- Reports now expose isolated capacitor count/states/radii plus collection capacitor group/entity counts.
- Regression suite expanded to 10 tests.
