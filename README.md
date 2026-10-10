# Waylura Offline Maps — Open Verification & Extraction Tools

Public distribution assets, open-source verification tools, and reproducible PMTiles extraction utilities for offline city maps.

> **Privacy Notice:** The **Waylura application repository remains private**. This repository does not contain application code, private configurations, user data, or editorial approval receipts.

---

## 1. Published Assets

- **[v1.0.0 Release](https://github.com/CevatAYDN/waylura-maps/releases/tag/v1.0.0):** İstanbul, Antalya, Tokyo, and Kyoto PMTiles extracts, pack manifests, index/version lock, and a Japanese map font.
- Public Git source contains pinned release hashes, unit tests, and verifier source. Map binaries are distributed via GitHub Releases assets, not committed into Git history.
- **Pinning Contract:** Downstream consumers must pin both the release tag and artifact SHA-256 digests. Never mutate an existing published tag.

---

## 2. Verification (Python 3.10+, Standard Library Only)

### Fast Offline Unit Tests
```bash
python -m unittest discover -s tests -v
```
Runs 30 offline tests covering valid releases, missing/unexpected assets, hash mismatches, draft/prerelease rejections, path traversal attacks, insecure redirect blocks, URL credential stripping, manifest version drift, and PMTiles bounding-box extraction rules.

### Public Release Verification (Live Metadata)
```bash
# Unauthenticated (subject to GitHub IP rate limits)
python tools/verify_release.py --tag v1.0.0

# Authenticated (recommended for CI or frequent runs)
python tools/verify_release.py --tag v1.0.0 --token $GITHUB_TOKEN
```
Queries public GitHub Release metadata and validates all 11 asset names, byte sizes, URLs, uploaded states, and SHA-256 digests against [`releases/v1.0.0.lock.json`](releases/v1.0.0.lock.json).

### Full Asset Download & Manifest Check (Live Byte Rehash ~86 MB)
```bash
python tools/verify_release.py --tag v1.0.0 --download
```
Downloads each asset over HTTPS, verifies exact byte sizes and SHA-256 digests, and validates the cross-contract integrity of `index.json` ⇄ `*.pack.json` ⇄ `version_lock.json`.

---

## 3. Reproducible PMTiles Extraction (`tools/extract_pmtiles.py`)

Extract a geographic slice from an upstream PMTiles archive (requires `go-pmtiles 1.31.2`):

```bash
# Dry-run plan (prints bounding box and draft manifest without downloading)
python tools/extract_pmtiles.py --output build/antalya-z14.pmtiles --bbox 30.3012,36.6818,30.9770,37.2792 --city antalya --dry-run

# Execute extraction and manifest generation
python tools/extract_pmtiles.py --source https://build.protomaps.com/20260928.pmtiles --output build/antalya-z14.pmtiles --bbox 30.3012,36.6818,30.9770,37.2792 --city antalya
```

The script extracts the requested bounding box, runs `pmtiles verify`, reads headers, and writes a companion `.manifest.json` recording CRS (`EPSG:4326` / `EPSG:3857`), tool versions, source timestamp, and SHA-256.

---

## 4. Source Status and Licensing

- **Repository Tooling:** Licensed under [MIT](LICENSE).
- **Japanese Map Font:** Derived from Google/Adobe **Noto Sans JP** v2.004 under the [SIL Open Font License 1.1](licenses/NotoSansJP-OFL.txt).
- **Map Vector Data:** Derived from OpenStreetMap under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), ESA WorldCover ([CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)), and Natural Earth (Public Domain).
- See [DATA_ATTRIBUTION.md](DATA_ATTRIBUTION.md) for full lineage, checksums, and reproducibility boundaries.
