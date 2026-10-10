# Waylura Offline Maps — open verification tools

Public distribution assets and open-source verification tools for offline city maps. The **Waylura application repository remains private**. This repository does not contain its application source, private configuration, user data, or editorial approval receipts.

## Published assets

- [v1.0.0 release](https://github.com/CevatAYDN/waylura-maps/releases/tag/v1.0.0): İstanbul, Antalya, Tokyo and Kyoto PMTiles, pack manifests, index/version lock and a Japanese map font.
- Public Git source contains pinned release hashes, tests, and verifier source. Large map binaries remain in Releases, not Git history.
- Consumers must pin both release tag and SHA-256. Create a new tag for any changes instead of replacing previously published assets.

## Verify (Python 3.10+, standard library only)

```bash
python -m unittest discover -s tests -v
python tools/verify_release.py --tag v1.0.0
python tools/verify_release.py --tag v1.0.0 --download
```

The first command runs fast **offline unit tests**. The second queries public GitHub Release metadata and checks all 11 asset names, sizes, URLs, states and GitHub-computed SHA-256 hashes against [the public release lock](releases/v1.0.0.lock.json). The `--download` command downloads and rehashes the actual bytes (about 86 MB) and validates index ⇄ pack-manifest ⇄ version-lock consistency. Live checks require network access and are not automated CI.

A passing verifier **does not certify** geographic coverage, currency of source data, font/map redistribution rights or Android device compatibility. Download and offline rendering require separate physical-device acceptance.

## Public download contract

```text
https://github.com/CevatAYDN/waylura-maps/releases/download/v1.0.0/istanbul-z14.pmtiles
```

Download over HTTPS, handle redirects and byte range/resume safely, check full file size and manifest SHA-256, then activate. GitHub Releases is not a guaranteed CDN SLA for commercial traffic.

## Source status and licensing

**Available open source:** release verifier, negative tests, immutable artifact lock, contributor guidelines. **Not yet available:** complete independently reproducible PMTiles clipping/build pipeline, exact upstream font source transformations, and complete verified font license package. Do not claim these are already open or reproducible.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [DATA_ATTRIBUTION.md](DATA_ATTRIBUTION.md). The [MIT license](LICENSE) covers repository-authored code only; map data and fonts have distinct upstream terms.
