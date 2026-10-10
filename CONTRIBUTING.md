# Contributing

Issues, reproducible bug reports, license corrections, and PRs are welcome.

## Quality and privacy rules

1. Never commit credentials, private Waylura application code, user records, location histories or unpublished editorial evidence.
2. Make each new public release a **new tag** and a new pinned `releases/<tag>.lock.json`. Do not replace already released assets.
3. Document upstream snapshots, clipping bounds, command lines, tool versions, fonts, license obligations, and acknowledgments. If the original inputs are unavailable, label the builder **not reproducible**.
4. Keep `index.json`, `version_lock.json`, all `*.pack.json`, actual maps and fonts consistent. Pin SHA-256 and exact sizes.
5. Run `python -m unittest discover -s tests -v` locally; for online release verification run `python tools/verify_release.py --download`.
6. A green metadata or unit test is not proof of mobile readiness. For that, test download, interruption/resume, map labels, touch gestures, airplane mode and cold restart on an actual device.
7. Verification should not need GitHub Actions, access to the private app repository, or paid services.

The [MIT code license](LICENSE) does not cover third-party map data or fonts. Review [DATA_ATTRIBUTION.md](DATA_ATTRIBUTION.md).
