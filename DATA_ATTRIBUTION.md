# Map and Font Provenance & Rights Checklist

The [MIT license](LICENSE) applies to **repository-authored code** (such as verification and extraction tools), not automatically to third-party map databases, geographic vector data, or font software.

---

## 1. Maps (Vector Tiles)

### Provenance and Source Archives
- **Upstream Source Archive:** `https://build.protomaps.com/20260928.pmtiles`
- **Source Snapshot Date:** `2026-09-28`
- **OSM Replication Timestamp:** `2026-09-28T04:00:00Z`
- **Upstream Source Index Blake3:** `8d2d48dfc2524c5f0071acb5a7bc5e7eb5cd481915bc5b1cfc80fe2e7398fdf7`
- **Extraction Tooling:** `go-pmtiles 1.31.2` (`a658baa4d7e55020aef6ca17bd9ff9faa1582671266b36f58c52db0ac8e785a1` for Windows x86_64)
- **Coordinate Reference Systems:**
  - Bounding Box / Geographic: `EPSG:4326` (WGS84, `[minLon, minLat, maxLon, maxLat]`)
  - Tile Coordinate System: `EPSG:3857` (Web Mercator MVT)
- **Clipping Bounds:**
  - İstanbul: `[27.9708481, 40.7376735, 29.9588048, 41.6710000]` (maxzoom 14)
  - Antalya: `[30.3012421, 36.6818585, 30.9770747, 37.2792435]` (maxzoom 14)
  - Tokyo: `[139.5628986, 35.4816556, 139.9189004, 35.8174937]` (maxzoom 14)
  - Kyoto: `[135.5590060, 34.8749160, 135.8784420, 35.3212207]` (maxzoom 14)

### Reproducibility Status
- **Archive-to-Slice Extraction:** `REPRODUCIBLE`. Given `go-pmtiles 1.31.2` and the `20260928.pmtiles` archive, running `python tools/extract_pmtiles.py` produces the exact byte-identical PMTiles city slice.
- **Wholesale Planet Generation from Raw OSM Planet PBF:** `NOT REPRODUCIBLE WITHOUT UPSTREAM CLUSTER`. Generation of the 138 GB planet PMTiles base archive requires the Protomaps build cluster and pipeline.

### Map Licensing and Attribution
- OpenStreetMap data is provided under the [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
- Landcover data: [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) (ESA WorldCover).
- Physical / boundaries: Public Domain (Natural Earth).
- **Mandatory Attribution:** *© OpenStreetMap contributors, Protomaps, ESA WorldCover, Natural Earth*.

---

## 2. Fonts (Map Label Typography)

### Japanese Map Font
- **Upstream Font Family:** **Noto Sans JP** (SubsetOTF / JP Regular)
- **Upstream Project:** [Google / Adobe Noto CJK](https://github.com/notofonts/noto-cjk)
- **Upstream Version:** `2.004`
- **Upstream Source URL:** `https://raw.githubusercontent.com/notofonts/noto-cjk/Sans2.004/Sans/SubsetOTF/JP/NotoSansJP-Regular.otf`
- **Upstream SHA-256:** `dff723ba59d57d136764a04b9b2d03205544f7cd785a711442d6d2d085ac5073`
- **License:** [SIL Open Font License (OFL), Version 1.1](licenses/NotoSansJP-OFL.txt)
- **Compiled Derivative:** `waylura-map-sans-japanese-f1c6a8815f25bc4fc4ebd9bc155055557e3154af11266a02c25835e426c1fe74.otf`
- **Derivative SHA-256:** `f1c6a8815f25bc4fc4ebd9bc155055557e3154af11266a02c25835e426c1fe74`
- **Derivative Size:** `569,552 bytes`
- **Subset Scope:** Subsetted with `fontTools==4.60.1` targeting kanji, hiragana, katakana, and punctuation required for Tokyo and Kyoto offline navigation corpus.

### Latin Map Font
- **Upstream Font Family:** **Noto Sans** (hinted Regular)
- **Upstream Project:** [Google Fonts Noto Sans](https://github.com/notofonts/latin-greek-cyrillic)
- **Upstream Version:** `2.015`
- **Upstream Source URL:** `https://github.com/notofonts/latin-greek-cyrillic/releases/download/NotoSans-v2.015/NotoSans-v2.015.zip`
- **Upstream SHA-256:** `478c558ea716033cd60c03438f628dfa75694dcf6b5f6d505a2f05fd2b4f3823`
- **License:** SIL Open Font License (OFL), Version 1.1.

---

## 3. Publication and Security Boundaries

1. **Private Code Segregation:** The core Waylura application source, private configurations, and internal credentials remain strictly private.
2. **No Fake Receipts:** Do not forge human review receipts, test signatures, or artificial audit records.
3. **Immutable Releases:** Do not overwrite or mutate existing public release tags or assets. New revisions must be published under a new semantic tag with an updated release lock.
