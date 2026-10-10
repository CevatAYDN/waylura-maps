#!/usr/bin/env python3
"""Reproducible PMTiles city extract, verification, and manifest builder.

Standard-library + go-pmtiles 1.31.2 tool chain.

Extracts a bounding-box slice from an upstream PMTiles archive, verifies
structural tile integrity, and emits an immutable manifest with SHA-256,
CRS, clipping bounds, source timestamps, and reproducibility provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

DEFAULT_SOURCE = "https://build.protomaps.com/20260928.pmtiles"
DEFAULT_SOURCE_SNAPSHOT = "2026-09-28"
DEFAULT_OSM_REPLICATION_TIMESTAMP = "2026-09-28T04:00:00Z"
EXPECTED_TOOL_VERSION = "go-pmtiles 1.31.2"
DEFAULT_MAXZOOM = 14
CRS_COORDINATES = "EPSG:4326 (WGS84)"
CRS_TILES = "EPSG:3857 (Web Mercator)"
WEB_MERCATOR_MAX_LAT = 85.05112878


class ExtractionError(Exception):
    pass


def parse_bbox(bbox_str: str) -> list[float]:
    parts = bbox_str.strip().split(",")
    if len(parts) != 4:
        raise ExtractionError(
            f"Bounding box must contain 4 comma-separated numbers: min_lon,min_lat,max_lon,max_lat. Got {bbox_str!r}"
        )
    try:
        min_lon, min_lat, max_lon, max_lat = map(float, parts)
    except ValueError as e:
        raise ExtractionError(f"Bounding box coordinates must be numeric: {e}") from e

    if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
        raise ExtractionError(f"Longitude must be in [-180, 180]: min_lon={min_lon}, max_lon={max_lon}")
    if not (-WEB_MERCATOR_MAX_LAT <= min_lat <= WEB_MERCATOR_MAX_LAT and -WEB_MERCATOR_MAX_LAT <= max_lat <= WEB_MERCATOR_MAX_LAT):
        raise ExtractionError(
            f"Latitude exceeds Web Mercator projection bounds [{-WEB_MERCATOR_MAX_LAT}, {WEB_MERCATOR_MAX_LAT}]: "
            f"min_lat={min_lat}, max_lat={max_lat}"
        )
    if min_lon >= max_lon:
        raise ExtractionError(f"Bounding box width must be positive (min_lon < max_lon): {bbox_str}")
    if min_lat >= max_lat:
        raise ExtractionError(f"Bounding box height must be positive (min_lat < max_lat): {bbox_str}")

    return [min_lon, min_lat, max_lon, max_lat]


def validate_maxzoom(maxzoom: int) -> int:
    if not isinstance(maxzoom, int) or not (0 <= maxzoom <= 16):
        raise ExtractionError(f"Invalid maxzoom {maxzoom}; must be an integer in range [0, 16]")
    return maxzoom


def compute_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_tool(user_tool: str | None = None) -> str:
    if user_tool and os.path.isfile(user_tool) and os.access(user_tool, os.X_OK):
        return user_tool
    discovered = shutil.which("pmtiles")
    if discovered:
        return discovered
    # Fallback to local .tools path if present
    repo_root = Path(__file__).resolve().parents[1]
    candidate = repo_root / ".tools" / "pmtiles" / ("pmtiles.exe" if sys.platform == "win32" else "pmtiles")
    if candidate.is_file():
        return str(candidate)
    return "pmtiles"


def get_tool_version(tool_path: str) -> str:
    """Query actual tool version via command line.
    
    If query fails or binary is missing, returns UNKNOWN / NOT_DETECTED.
    Never fabricates expected version if actual execution fails.
    """
    try:
        res = subprocess.run([tool_path, "version"], capture_output=True, text=True, timeout=5)
        out = (res.stdout or res.stderr).strip()
        if res.returncode == 0 and out:
            return out
    except Exception:
        pass
    return "UNKNOWN / NOT_DETECTED"


def build_manifest_record(
    *,
    city: str,
    file_name: str,
    size_bytes: int,
    sha256: str,
    requested_bbox: list[float],
    header: dict | None,
    source_archive: str,
    source_snapshot: str,
    tool_version: str,
    status: str = "EXTRACT_UNVERIFIED",
    reproducibility_classification: str = "REPRODUCIBILITY_UNVERIFIED",
    dual_run_verification: dict | None = None,
) -> dict:
    """Build deterministic manifest record.
    
    Variable runtime timestamps (builtAt) are omitted from this deterministic artifact record.
    If header extraction fails, header is None; fake metadata is NEVER fabricated.
    Reproducibility status defaults to UNVERIFIED unless backed by verified dual-run proof.
    """
    record = {
        "city": city,
        "fileName": file_name,
        "sizeBytes": size_bytes,
        "sha256": sha256,
        "crs": {
            "geographicCoordinates": CRS_COORDINATES,
            "vectorTileSchema": CRS_TILES,
        },
        "requestedBbox": requested_bbox,
        "header": header,
        "sourceArchive": source_archive,
        "sourceSnapshot": source_snapshot,
        "osmReplicationTimestamp": DEFAULT_OSM_REPLICATION_TIMESTAMP,
        "toolVersion": tool_version,
        "license": "ODbL-1.0 (OpenStreetMap); CC-BY-4.0 (ESA WorldCover); Public Domain (Natural Earth)",
        "attribution": "OpenStreetMap contributors; Protomaps; ESA WorldCover; Natural Earth",
        "status": status,
        "provenance": {
            "reproducibilityClassification": reproducibility_classification,
            "rawPlanetPbfGeneration": "NOT_REPRODUCIBLE_WITHOUT_UPSTREAM_CLUSTER",
            "note": (
                "Extracting this bounding box requires identical source bytes, tool version, and bounds. "
                "Reproducibility defaults to UNVERIFIED unless validated by dual independent runs."
            ),
        },
    }
    if dual_run_verification is not None:
        record["provenance"]["dualRunVerification"] = dual_run_verification
    return record


def execute_extract(
    tool: str,
    source: str,
    output_path: Path,
    bbox: list[float],
    maxzoom: int,
) -> tuple[int, str, dict | None]:
    """Execute pmtiles extract, verify, and show --header-json.
    
    Returns (size, sha256, header). Header is None if header query fails.
    """
    cmd_extract = [
        tool,
        "extract",
        source,
        str(output_path),
        f"--bbox={','.join(map(str, bbox))}",
        f"--maxzoom={maxzoom}",
    ]
    res = subprocess.run(cmd_extract, capture_output=True, text=True)
    if res.returncode != 0:
        raise ExtractionError(f"pmtiles extract failed (code {res.returncode}):\n{res.stderr or res.stdout}")

    cmd_verify = [tool, "verify", str(output_path)]
    res_verify = subprocess.run(cmd_verify, capture_output=True, text=True)
    if res_verify.returncode != 0:
        raise ExtractionError(f"pmtiles verify failed:\n{res_verify.stderr or res_verify.stdout}")

    header = None
    cmd_show = [tool, "show", str(output_path), "--header-json"]
    res_show = subprocess.run(cmd_show, capture_output=True, text=True)
    if res_show.returncode == 0 and res_show.stdout.strip():
        try:
            header = json.loads(res_show.stdout)
        except json.JSONDecodeError:
            header = None

    sha = compute_sha256(output_path)
    size = output_path.stat().st_size
    return size, sha, header


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Upstream PMTiles source URL or file")
    parser.add_argument("--output", required=True, help="Path to output .pmtiles file")
    parser.add_argument("--bbox", required=True, help="Bounding box as min_lon,min_lat,max_lon,max_lat")
    parser.add_argument("--city", default="custom", help="City or region identifier")
    parser.add_argument("--maxzoom", type=int, default=DEFAULT_MAXZOOM, help="Max zoom level (default: 14)")
    parser.add_argument("--tool-path", default=None, help="Explicit path to pmtiles binary")
    parser.add_argument("--verify-reproducible", action="store_true", help="Execute two independent runs and compare bitwise hashes")
    parser.add_argument("--dry-run", action="store_true", help="Print plan and draft manifest without executing")
    args = parser.parse_args(argv)

    try:
        bbox = parse_bbox(args.bbox)
        maxzoom = validate_maxzoom(args.maxzoom)
        output_path = Path(args.output).resolve()

        if args.dry_run:
            print(f"[DRY-RUN] Source:        {args.source}")
            print(f"[DRY-RUN] Output:        {output_path}")
            print(f"[DRY-RUN] City:          {args.city}")
            print(f"[DRY-RUN] BBox:          {bbox}")
            print(f"[DRY-RUN] Maxzoom:       {maxzoom}")
            manifest_draft = build_manifest_record(
                city=args.city,
                file_name=output_path.name,
                size_bytes=0,
                sha256="0" * 64,
                requested_bbox=bbox,
                header=None,
                source_archive=args.source,
                source_snapshot=DEFAULT_SOURCE_SNAPSHOT,
                tool_version=EXPECTED_TOOL_VERSION,
                status="DRY_RUN_PLAN",
                reproducibility_classification="REPRODUCIBILITY_UNVERIFIED",
            )
            print("\n[DRY-RUN] Draft Manifest:")
            print(json.dumps(manifest_draft, indent=2, ensure_ascii=False))
            return 0

        tool = find_tool(args.tool_path)
        actual_tool_version = get_tool_version(tool)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if args.verify_reproducible:
            print(f"Executing Dual-Run Reproducibility Verification with {actual_tool_version}...")
            with tempfile.TemporaryDirectory() as tmpdir:
                p1 = Path(tmpdir) / "run1.pmtiles"
                p2 = Path(tmpdir) / "run2.pmtiles"

                print("  -> Run 1/2...")
                size1, sha1, header1 = execute_extract(tool, args.source, p1, bbox, maxzoom)
                print(f"     Run 1 SHA-256: {sha1} ({size1} bytes)")

                print("  -> Run 2/2...")
                size2, sha2, header2 = execute_extract(tool, args.source, p2, bbox, maxzoom)
                print(f"     Run 2 SHA-256: {sha2} ({size2} bytes)")

                if sha1 != sha2 or size1 != size2:
                    raise ExtractionError(
                        f"NON-DETERMINISTIC EXTRACTION DETECTED:\n"
                        f"Run 1: {sha1} ({size1} bytes)\n"
                        f"Run 2: {sha2} ({size2} bytes)\n"
                        f"Cannot declare REPRODUCIBLE PASS."
                    )

                # Move verified artifact to final output path
                shutil.copy2(p1, output_path)
                status = "REPRODUCIBLE_PASS"
                repro_class = "VERIFIED_BITWISE_REPRODUCIBLE"
                dual_proof = {
                    "verified": True,
                    "runsCount": 2,
                    "matchingSha256": sha1,
                    "matchingSizeBytes": size1,
                    "toolVersion": actual_tool_version,
                }
                header = header1
                sha = sha1
                size = size1
        else:
            # Single run: reproducibility remains UNVERIFIED
            size, sha, header = execute_extract(tool, args.source, output_path, bbox, maxzoom)
            status = "EXTRACT_COMPLETED_UNVERIFIED"
            repro_class = "REPRODUCIBILITY_UNVERIFIED"
            dual_proof = None

        manifest = build_manifest_record(
            city=args.city,
            file_name=output_path.name,
            size_bytes=size,
            sha256=sha,
            requested_bbox=bbox,
            header=header,
            source_archive=args.source,
            source_snapshot=DEFAULT_SOURCE_SNAPSHOT,
            tool_version=actual_tool_version,
            status=status,
            reproducibility_classification=repro_class,
            dual_run_verification=dual_proof,
        )

        manifest_path = output_path.with_suffix(".manifest.json")
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"SUCCESS: Extracted {output_path.name} ({size} bytes, sha256={sha})")
        print(f"Status: {status} ({repro_class})")
        print(f"Manifest written to: {manifest_path.name}")
        return 0

    except (ExtractionError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
