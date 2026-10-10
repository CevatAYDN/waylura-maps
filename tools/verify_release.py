#!/usr/bin/env python3
"""Verify a Waylura maps GitHub Release against a pinned asset lock.

Standard-library only. By default checks GitHub-published metadata; with
--download hashes actual bytes and validates manifest/version-lock contracts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "CevatAYDN/waylura-maps"
VALID_SHA = re.compile(r"^[0-9a-f]{64}$")

ALLOWED_REDIRECT_HOSTS = {
    "api.github.com",
    "github.com",
    "objects.githubusercontent.com",
    "raw.githubusercontent.com",
}


class VerificationError(Exception):
    pass


def redact_sensitive(text: str) -> str:
    """Ensure tokens never appear in logs, tracebacks, or output."""
    return re.sub(
        r"(gh[pousr]_[A-Za-z0-9_]{16,}|Bearer\s+[A-Za-z0-9_\-\.]+)",
        "[REDACTED]",
        str(text),
    )


def get_auth_token() -> str | None:
    """Retrieve GitHub token securely from environment or gh CLI.
    
    Avoids passing tokens via CLI arguments which leak into process tables (ps).
    """
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and token.strip():
        return token.strip()
    gh_bin = shutil.which("gh")
    if gh_bin:
        try:
            res = subprocess.run(
                [gh_bin, "auth", "token"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
    return None


class HttpsOnlyRedirects(urllib.request.HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        if target.scheme != "https" or not target.netloc or target.username or target.password:
            raise VerificationError("Unsafe redirect destination blocked")
        if target.netloc.lower() not in ALLOWED_REDIRECT_HOSTS:
            raise VerificationError(f"Untrusted redirect host blocked: {target.netloc}")

        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is None:
            return None

        # SECURITY: Strip Authorization header whenever redirecting outside api.github.com
        if target.netloc.lower() != "api.github.com":
            for k in list(new_req.headers.keys()):
                if k.lower() == "authorization":
                    del new_req.headers[k]
            if hasattr(new_req, "unredirected_hdrs"):
                for k in list(new_req.unredirected_hdrs.keys()):
                    if k.lower() == "authorization":
                        del new_req.unredirected_hdrs[k]

        return new_req


def fetch(url: str, *, max_bytes: int | None = None) -> bytes:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise VerificationError("Only HTTPS URLs without credentials are accepted")
    opener = urllib.request.build_opener(HttpsOnlyRedirects)
    headers = {
        "User-Agent": "waylura-maps-verifier/1.0",
        "Accept": "application/vnd.github+json",
    }
    token = get_auth_token()
    if token and parsed.netloc == "api.github.com":
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with opener.open(request, timeout=45) as response:
            data = response.read(None if max_bytes is None else max_bytes + 1)
    except Exception as e:
        raise VerificationError(redact_sensitive(str(e))) from None

    if max_bytes is not None and len(data) > max_bytes:
        raise VerificationError(f"Response exceeded {max_bytes} bytes")
    return data


def fetch_json(url: str) -> dict:
    data = json.loads(fetch(url, max_bytes=2_000_000))
    if not isinstance(data, dict):
        raise VerificationError("Expected JSON object")
    return data


def validate_release(release: dict, lock: dict) -> list[dict]:
    if release.get("tag_name") != lock.get("tag"):
        raise VerificationError("Release tag does not match lock")
    if release.get("draft") or release.get("prerelease"):
        raise VerificationError("Release must be published and stable")
    expected = lock.get("assets")
    actual = release.get("assets")
    if not isinstance(expected, dict) or not expected or not isinstance(actual, list):
        raise VerificationError("Invalid release metadata or lock")
    by_name = {}
    for asset in actual:
        name = asset.get("name")
        if not isinstance(name, str) or name in by_name or "/" in name or "\\" in name:
            raise VerificationError(f"Duplicate or unsafe filename: {name!r}")
        by_name[name] = asset
    if set(by_name) != set(expected):
        missing, extra = set(expected) - set(by_name), set(by_name) - set(expected)
        raise VerificationError(f"Asset drift: missing={sorted(missing)}, extra={sorted(extra)}")
    for name, pinned in expected.items():
        sha = pinned.get("sha256")
        size = pinned.get("size")
        published = by_name[name]
        if not isinstance(sha, str) or not VALID_SHA.fullmatch(sha):
            raise VerificationError(f"Invalid SHA-256 lock: {name}")
        if not isinstance(size, int) or size <= 0:
            raise VerificationError(f"Invalid size lock: {name}")
        if published.get("size") != size or published.get("digest") != f"sha256:{sha}":
            raise VerificationError(f"Digest/size drift: {name}")
        if published.get("state") != "uploaded":
            raise VerificationError(f"Asset upload incomplete: {name}")
        expected_url = f"https://github.com/{REPO}/releases/download/{lock['tag']}/{name}"
        if published.get("browser_download_url") != expected_url:
            raise VerificationError(f"Unexpected asset URL: {name}")
    return [by_name[name] for name in sorted(expected)]


def validate_manifest_contract(index: dict, manifests: dict[str, dict],
                               lock: dict, version_lock: dict) -> None:
    if index.get("schemaVersion") != 1 or version_lock.get("schemaVersion") != 1:
        raise VerificationError("Unsupported index/version lock schema")
    entries = index.get("packs")
    if not isinstance(entries, list) or not entries:
        raise VerificationError("Missing pack index")
    ids = set()
    for entry in entries:
        pack_id = entry.get("packId")
        if pack_id in ids or not isinstance(pack_id, str):
            raise VerificationError(f"Duplicate/invalid pack ID: {pack_id}")
        ids.add(pack_id)
        name = f"{pack_id}.pack.json"
        if entry.get("manifestAsset", "").split("/")[-1] != name:
            raise VerificationError(f"Index path mismatch: {pack_id}")
        manifest = manifests.get(name)
        if not manifest or manifest.get("packId") != pack_id or manifest.get("packVersion") != entry.get("packVersion"):
            raise VerificationError(f"Manifest version drift: {pack_id}")
        expected_version = version_lock.get("packs", {}).get(pack_id, {}).get("packVersion")
        if expected_version != entry.get("packVersion"):
            raise VerificationError(f"Version lock mismatch: {pack_id}")
        maps = [c for c in manifest.get("components", []) if c.get("kind") == "map"]
        if len(maps) != 1:
            raise VerificationError(f"Missing/duplicate map component: {pack_id}")
        component = maps[0]
        pinned = lock["assets"].get(component.get("fileName"))
        if not pinned or component.get("sha256") != pinned["sha256"] or component.get("sizeBytes") != pinned["size"]:
            raise VerificationError(f"Map component mismatch: {pack_id}")
    if ids != set(version_lock.get("packs", {})):
        raise VerificationError("Index differs from version lock IDs")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="v1.0.0")
    parser.add_argument("--lock", default=str(Path(__file__).resolve().parents[1] / "releases" / "v1.0.0.lock.json"))
    parser.add_argument("--download", action="store_true",
                        help="Download/hash all assets and verify manifests (about 86 MB)")
    args = parser.parse_args()
    try:
        lock = json.loads(Path(args.lock).read_text(encoding="utf-8"))
        if args.tag != lock.get("tag"):
            raise VerificationError("--tag and lock.tag mismatch")
        release = fetch_json(f"https://api.github.com/repos/{REPO}/releases/tags/{args.tag}")
        assets = validate_release(release, lock)
        print(f"PASS: {len(assets)} pinned public assets in {args.tag}")
        if args.download:
            parsed = {}
            for asset in assets:
                name = asset["name"]
                body = fetch(asset["browser_download_url"], max_bytes=lock["assets"][name]["size"])
                if len(body) != lock["assets"][name]["size"] or hashlib.sha256(body).hexdigest() != lock["assets"][name]["sha256"]:
                    raise VerificationError(f"Downloaded bytes mismatch: {name}")
                if name.endswith(".json"):
                    parsed[name] = json.loads(body)
                print(f"PASS sha256: {name}")
            manifests = {name: data for name, data in parsed.items() if name.endswith(".pack.json")}
            validate_manifest_contract(parsed["index.json"], manifests,
                                       lock, parsed["version_lock.json"])
            print("PASS: index/manifest/version-lock contract")
        return 0
    except (VerificationError, OSError, ValueError, KeyError, urllib.error.URLError) as error:
        safe_msg = redact_sensitive(str(error))
        print(f"FAIL: {safe_msg}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
