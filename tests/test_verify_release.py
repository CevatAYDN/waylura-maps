"""Offline tests for public release verification. No network, credentials or CI."""
import importlib.util
import pathlib
import unittest
import urllib.request

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

    def test_tag_mismatch_rejected(self):
        self.release["tag_name"] = "v1.0.1"
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_release(self.release, self.lock)

    def test_prerelease_rejected(self):
        self.release["prerelease"] = True
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_release(self.release, self.lock)

    def test_path_traversal_asset_name_rejected(self):
        self.release["assets"] = [{"name": "../evil.pmtiles"}]
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_release(self.release, self.lock)

    def test_backslash_asset_name_rejected(self):
        self.release["assets"] = [{"name": "evil\\path.pmtiles"}]
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_release(self.release, self.lock)

    def test_invalid_sha_format_in_lock_rejected(self):
        self.lock["assets"]["map.pmtiles"]["sha256"] = "not_a_valid_64_hex_string"
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_release(self.release, self.lock)

    def test_invalid_size_in_lock_rejected(self):
        self.lock["assets"]["map.pmtiles"]["size"] = -5
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_release(self.release, self.lock)

    def test_asset_state_not_uploaded_rejected(self):
        self.release["assets"][0]["state"] = "in_progress"
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_release(self.release, self.lock)

    def test_size_mismatch_rejected(self):
        self.release["assets"][0]["size"] = 9999
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_release(self.release, self.lock)

    def test_http_redirect_rejected(self):
        handler = verifier.HttpsOnlyRedirects()
        with self.assertRaises(verifier.VerificationError):
            handler.redirect_request(None, None, 302, "Found", {}, "http://insecure.test/file")

    def test_credential_redirect_rejected(self):
        handler = verifier.HttpsOnlyRedirects()
        with self.assertRaises(verifier.VerificationError):
            handler.redirect_request(None, None, 302, "Found", {}, "https://user:pass@secure.test/file")

    def test_fetch_rejects_credentials_in_url(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.fetch("https://user:pass@example.com/asset")

    def test_fetch_rejects_non_https_url(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.fetch("http://example.com/asset")

    def test_manifest_contract_duplicate_pack_id(self):
        lock = {"assets": {"p1.pmtiles": {"size": 10, "sha256": "a" * 64}}}
        index = {"schemaVersion": 1, "packs": [
            {"packId": "p1", "packVersion": 1, "manifestAsset": "p1.pack.json"},
            {"packId": "p1", "packVersion": 1, "manifestAsset": "p1.pack.json"},
        ]}
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_manifest_contract(index, {}, lock, {"schemaVersion": 1, "packs": {"p1": {"packVersion": 1}}})

    def test_manifest_contract_version_drift(self):
        lock = {"assets": {"p1.pmtiles": {"size": 10, "sha256": "a" * 64}}}
        index = {"schemaVersion": 1, "packs": [
            {"packId": "p1", "packVersion": 2, "manifestAsset": "p1.pack.json"}
        ]}
        manifest = {"packId": "p1", "packVersion": 1, "components": [
            {"kind": "map", "fileName": "p1.pmtiles", "sha256": "a" * 64, "sizeBytes": 10}
        ]}
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_manifest_contract(index, {"p1.pack.json": manifest}, lock, {"schemaVersion": 1, "packs": {"p1": {"packVersion": 2}}})

    def test_manifest_contract_missing_map(self):
        lock = {"assets": {}}
        index = {"schemaVersion": 1, "packs": [
            {"packId": "p1", "packVersion": 1, "manifestAsset": "p1.pack.json"}
        ]}
        manifest = {"packId": "p1", "packVersion": 1, "components": [
            {"kind": "poi", "fileName": "p1.poi.json", "sha256": "a" * 64, "sizeBytes": 10}
        ]}
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_manifest_contract(index, {"p1.pack.json": manifest}, lock, {"schemaVersion": 1, "packs": {"p1": {"packVersion": 1}}})

    def test_manifest_contract_size_mismatch(self):
        lock = {"assets": {"p1.pmtiles": {"size": 10, "sha256": "a" * 64}}}
        index = {"schemaVersion": 1, "packs": [
            {"packId": "p1", "packVersion": 1, "manifestAsset": "p1.pack.json"}
        ]}
        manifest = {"packId": "p1", "packVersion": 1, "components": [
            {"kind": "map", "fileName": "p1.pmtiles", "sha256": "a" * 64, "sizeBytes": 999}
        ]}
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_manifest_contract(index, {"p1.pack.json": manifest}, lock, {"schemaVersion": 1, "packs": {"p1": {"packVersion": 1}}})

    def test_manifest_contract_version_lock_id_mismatch(self):
        lock = {"assets": {"p1.pmtiles": {"size": 10, "sha256": "a" * 64}}}
        index = {"schemaVersion": 1, "packs": [
            {"packId": "p1", "packVersion": 1, "manifestAsset": "p1.pack.json"}
        ]}
        manifest = {"packId": "p1", "packVersion": 1, "components": [
            {"kind": "map", "fileName": "p1.pmtiles", "sha256": "a" * 64, "sizeBytes": 10}
        ]}
        versions = {"schemaVersion": 1, "packs": {
            "p1": {"packVersion": 1},
            "p2_extra": {"packVersion": 1},
        }}
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_manifest_contract(index, {"p1.pack.json": manifest}, lock, versions)

    def test_authorization_header_stripped_on_cross_host_redirect(self):
        handler = verifier.HttpsOnlyRedirects()
        req = urllib.request.Request(
            "https://api.github.com/repos/test/releases",
            headers={"Authorization": "Bearer ghp_secret1234567890abcdef"},
        )
        new_req = handler.redirect_request(
            req, None, 302, "Found", {}, "https://objects.githubusercontent.com/asset.pmtiles"
        )
        self.assertIsNotNone(new_req)
        headers_lower = {k.lower(): v for k, v in new_req.headers.items()}
        self.assertNotIn("authorization", headers_lower)
        if hasattr(new_req, "unredirected_hdrs"):
            unred_lower = {k.lower(): v for k, v in new_req.unredirected_hdrs.items()}
            self.assertNotIn("authorization", unred_lower)

    def test_authorization_header_stripped_on_release_assets_redirect(self):
        handler = verifier.HttpsOnlyRedirects()
        req = urllib.request.Request(
            "https://api.github.com/repos/test/releases",
            headers={"Authorization": "Bearer ghp_secret1234567890abcdef"},
        )
        new_req = handler.redirect_request(
            req, None, 302, "Found", {}, "https://release-assets.githubusercontent.com/asset.pmtiles"
        )
        self.assertIsNotNone(new_req)
        headers_lower = {k.lower(): v for k, v in new_req.headers.items()}
        self.assertNotIn("authorization", headers_lower)

    def test_untrusted_redirect_host_blocked(self):
        handler = verifier.HttpsOnlyRedirects()
        req = urllib.request.Request("https://api.github.com/test")
        with self.assertRaises(verifier.VerificationError):
            handler.redirect_request(req, None, 302, "Found", {}, "https://evil.invalid/download")

    def test_redact_sensitive_tokens(self):
        msg = "Failed with ghp_1234567890abcdef1234 and Bearer token123"
        redacted = verifier.redact_sensitive(msg)
        self.assertNotIn("ghp_1234567890abcdef1234", redacted)
        self.assertNotIn("Bearer token123", redacted)
        self.assertIn("[REDACTED]", redacted)


if __name__ == "__main__":
    unittest.main()

