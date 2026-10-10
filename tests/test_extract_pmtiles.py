"""Offline tests for PMTiles extraction helper."""
import importlib.util
import json
import pathlib
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

    def test_parse_bbox_zero_area_width(self):
        with self.assertRaises(extractor.ExtractionError):
            extractor.parse_bbox("28.0,40.0,28.0,41.0")

    def test_parse_bbox_zero_area_height(self):
        with self.assertRaises(extractor.ExtractionError):
            extractor.parse_bbox("28.0,40.0,29.0,40.0")

    def test_parse_bbox_exceeds_web_mercator_lat(self):
        with self.assertRaises(extractor.ExtractionError):
            extractor.parse_bbox("28.0,86.0,29.0,87.0")
        with self.assertRaises(extractor.ExtractionError):
            extractor.parse_bbox("28.0,-88.0,29.0,-86.0")

    def test_validate_maxzoom(self):
        self.assertEqual(extractor.validate_maxzoom(14), 14)
        with self.assertRaises(extractor.ExtractionError):
            extractor.validate_maxzoom(20)
        with self.assertRaises(extractor.ExtractionError):
            extractor.validate_maxzoom(-1)

    def test_dry_run_execution(self):
        code = extractor.main([
            "--output", "test-city-z14.pmtiles",
            "--bbox", "28.0,40.0,29.0,41.0",
            "--city", "test-city",
            "--dry-run"
        ])
        self.assertEqual(code, 0)

    def test_build_manifest_record_is_deterministic(self):
        record1 = extractor.build_manifest_record(
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
        record2 = extractor.build_manifest_record(
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
        self.assertEqual(record1, record2)
        self.assertNotIn("builtAt", record1)
        self.assertEqual(record1["sha256"], "b" * 64)
        self.assertEqual(record1["provenance"]["reproducibilityClassification"], "REPRODUCIBILITY_UNVERIFIED")

    def test_tool_version_detection_fails_honestly_without_fabrication(self):
        version = extractor.get_tool_version("non_existent_binary_xyz_12345")
        self.assertEqual(version, "UNKNOWN / NOT_DETECTED")

    def test_manifest_header_is_none_when_unavailable_not_fabricated(self):
        record = extractor.build_manifest_record(
            city="tokyo",
            file_name="tokyo-z14.pmtiles",
            size_bytes=5000,
            sha256="c" * 64,
            requested_bbox=[139.0, 35.0, 140.0, 36.0],
            header=None,
            source_archive="https://example.com/source.pmtiles",
            source_snapshot="2026-09-28",
            tool_version="UNKNOWN / NOT_DETECTED",
        )
        self.assertIsNone(record["header"])
        self.assertEqual(record["status"], "EXTRACT_UNVERIFIED")
        self.assertEqual(record["provenance"]["reproducibilityClassification"], "REPRODUCIBILITY_UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
