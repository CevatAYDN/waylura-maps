"""Offline tests for PMTiles extraction helper."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

script = pathlib.Path(__file__).resolve().parents[1] / "tools" / "extract_pmtiles.py"
spec = importlib.util.spec_from_file_location("extract_pmtiles", script)
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)


class ExtractPmtilesTests(unittest.TestCase):
    def test_parse_bbox_valid(self):
        bbox = extractor.parse_bbox("28.0,40.5,29.5,41.5")
        self.assertEqual(bbox, [28.0, 40.5, 29.5, 41.5])

    def test_parse_bbox_invalid_parts(self):
        with self.assertRaises(extractor.ExtractionError):
            extractor.parse_bbox("28.0,40.5,29.5")

    def test_parse_bbox_out_of_range(self):
        with self.assertRaises(extractor.ExtractionError):
            extractor.parse_bbox("185.0,40.5,29.5,41.5")

    def test_parse_bbox_inverted_min_max(self):
        with self.assertRaises(extractor.ExtractionError):
            extractor.parse_bbox("30.0,40.5,20.0,41.5")

    def test_dry_run_execution(self):
        code = extractor.main([
            "--output", "test-city-z14.pmtiles",
            "--bbox", "28.0,40.0,29.0,41.0",
            "--city", "test-city",
            "--dry-run"
        ])
        self.assertEqual(code, 0)

    def test_build_manifest_record(self):
        record = extractor.build_manifest_record(
            city="istanbul",
            file_name="istanbul-z14.pmtiles",
            size_bytes=12345,
            sha256="b" * 64,
            requested_bbox=[28.0, 40.0, 29.0, 41.0],
            header={"maxzoom": 14},
            source_archive="https://build.protomaps.com/20260928.pmtiles",
            source_snapshot="2026-09-28",
            tool_version="go-pmtiles 1.31.2",
        )
        self.assertEqual(record["city"], "istanbul")
        self.assertEqual(record["sha256"], "b" * 64)
        self.assertEqual(record["crs"]["geographicCoordinates"], "EPSG:4326 (WGS84)")
        self.assertIn("NOT_REPRODUCIBLE_WITHOUT_UPSTREAM_CLUSTER", record["provenance"]["rawPlanetPbfGeneration"])
        self.assertIn("ARCHIVE_EXTRACT_REPRODUCIBLE", record["provenance"]["reproducibilityClassification"])


if __name__ == "__main__":
    unittest.main()
