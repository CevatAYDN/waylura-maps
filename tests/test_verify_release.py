"""Offline tests for public release verification. No network, credentials or CI."""
import importlib.util
import pathlib
import unittest

script = pathlib.Path(__file__).resolve().parents[1] / "tools" / "verify_release.py"
spec = importlib.util.spec_from_file_location("verify_release", script)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class ReleaseVerifierTests(unittest.TestCase):
    def setUp(self):
        self.lock = {"tag": "v1.0.0", "assets": {
            "map.pmtiles": {"size": 4, "sha256": "a" * 64},
        }}
        self.asset = {
            "name": "map.pmtiles", "size": 4, "digest": "sha256:" + "a" * 64,
            "state": "uploaded",
            "browser_download_url": f"https://github.com/{verifier.REPO}/releases/download/v1.0.0/map.pmtiles",
        }
        self.release = {
            "tag_name": "v1.0.0", "draft": False, "prerelease": False,
            "assets": [self.asset.copy()],
        }

    def test_valid_release(self):
        self.assertEqual(verifier.validate_release(self.release, self.lock), [self.asset])

    def test_missing_asset_rejected(self):
        self.release["assets"] = []
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_release(self.release, self.lock)

    def test_digest_mismatch_rejected(self):
        self.release["assets"][0]["digest"] = "sha256:" + "b" * 64
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_release(self.release, self.lock)

    def test_unexpected_asset_rejected(self):
        self.release["assets"].append({"name": "unexpected.txt"})
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_release(self.release, self.lock)

    def test_draft_release_rejected(self):
        self.release["draft"] = True
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_release(self.release, self.lock)

    def test_untrusted_url_rejected(self):
        self.release["assets"][0]["browser_download_url"] = "https://evil.invalid/file"
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_release(self.release, self.lock)

    def test_pack_contract_and_bad_hash(self):
        lock = {"assets": {"istanbul.pmtiles": {"size": 100, "sha256": "a" * 64}}}
        index = {"schemaVersion": 1, "packs": [{
            "packId": "istanbul", "packVersion": 2,
            "manifestAsset": "content/packs/istanbul.pack.json",
        }]}
        manifest = {"packId": "istanbul", "packVersion": 2, "components": [{
            "kind": "map", "fileName": "istanbul.pmtiles",
            "sha256": "a" * 64, "sizeBytes": 100,
        }]}
        versions = {"schemaVersion": 1, "packs": {
            "istanbul": {"packVersion": 2},
        }}
        verifier.validate_manifest_contract(
            index, {"istanbul.pack.json": manifest}, lock, versions)
        manifest["components"][0]["sha256"] = "b" * 64
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_manifest_contract(
                index, {"istanbul.pack.json": manifest}, lock, versions)


if __name__ == "__main__":
    unittest.main()
