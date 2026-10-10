# Map and font provenance / rights checklist

The [MIT license](LICENSE) applies to **repository-authored code**, not automatically to third-party map databases, data, font files, or assets.

## Maps

Published manifests identify an upstream Protomaps PMTiles archive (`https://build.protomaps.com/20260928.pmtiles`), a 2026-09-28 source snapshot, a `go-pmtiles` 1.31.2 verifier, clipping bounds and artifact hashes. OpenStreetMap data is provided under the [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Provide **© OpenStreetMap contributors** attribution and comply with applicable ODbL attribution and share-alike requirements. Independently check Protomaps/style/tool licensing; ODbL is not a blanket license for every bundled work.

A bit-for-bit reproducible build additionally needs complete public source inputs, clipping commands, geometry locks, exact tool versions and regeneration checks. Those are **not yet included here**. No claim of complete reproducibility is made.

## Fonts

The public release includes a Japanese map font (`waylura-map-sans-japanese-*.otf`). Before redistribution or adaptation, identify the exact upstream family, modified/subset status, and corresponding license texts and notices. SIL OFL and Apache 2.0 are examples of possible licenses, **not verification of this specific compiled font**. Font lineage and license packaging remain open documentation checks.

## Publication review

Do not put private data, internal workspace paths, authentication tokens or unapproved reviewer receipts in public source or release assets. Independently review manifests and binaries before new releases.
