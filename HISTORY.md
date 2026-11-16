# Design history

How 4D-VODS evolved from hand-drawn glyphs to the simulated architecture in this
repository. Earlier notes contained claims that the simulation later disproved;
they are summarised here, not published, so the reasoning stays visible without
spreading wrong numbers.

## Prototype 1 – four oriented triangles (variable-length code)

Four orientations of a triangle mapped to bit strings of length 2 or 3
(`01`, `10`, `001`, `100`), about 2.5 bits per symbol on average.

- **Incomplete code:** the Kraft–McMillan sum is 0.25 + 0.25 + 0.125 + 0.125 = 0.75 < 1,
  so some bit sequences cannot be written at all.
- **Not uniquely decodable:** `10001` parses both as `10|001` and `100|01`.

## Prototype 2 – nine planar glyphs

Adding a square, a rhombus, a pentagon and two diagonal bars gave 9 glyphs
(enough for 3 bits per symbol), but closed polygons round off when engraved at
sub-micron scale and the rhombus is just a square rotated by 45°, which halves
the tolerance to reader rotation.

## The Voxel-Wedge concept (initial notes)

One asymmetric engraving per byte: azimuth (3 bits), depth and slope (2 bits),
tail curvature (2 bits), floor reflectance (1 bit), plus

- differential angular readout (DARP),
- on-media run-length glyphs (• doubles the previous symbol, ◦ inverts it),
- sub-nanometre centroid offsets as geometric parity.

The notes assumed 8 bits in a 150 nm cell (356 bits/µm²).

## What the simulation showed (this repository)

| Idea | Outcome |
| --- | --- |
| 8 bits in 150 nm | Not readable: 0.01 bits/symbol recovered; the optics resolve about 225 nm |
| Voxel-Wedge at 500–600 nm | Works: about 27 bits/µm², roughly one Blu-ray layer |
| Shape-based bits (azimuth, curvature) | First to disappear as the pitch shrinks |
| Isotropic multi-level dots (APSK-16) | Best data-layer alphabet: about 43 bits/µm² at 300 nm |
| DARP | Rotation-proof but about 3× more errors than pilot symbols |
| On-media run-length glyphs | Beaten 4–6× by ordinary software compression on real data |
| Radial glyphs | Kept, as rotation-invariant finders in the SAMM low-cost code |

The current design, "phase carries the data, geometry carries the structure",
is described in `docs/`.
