"""Offline provenance checks for Preview26 CMS source-video metadata."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from src.publisher import website_publisher as publisher


class ForeignSourceMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.local = self.base / "isolated"
        self.foreign = self.base / "original"
        for root in (self.local, self.foreign):
            (root / "output").mkdir(parents=True)
        self.source = self.foreign / "output" / "original_clip.mp4"
        self.source.write_bytes(b"the exact source clip")
        self.other = self.base / "other" / "output" / self.source.name
        self.other.parent.mkdir(parents=True)
        self.other.write_bytes(b"different clip with same basename")
        self.video_id = "aBcD1234_XY"
        self.jobs = [{"id": "original_job", "video_title": "Original verifiable source story",
                      "youtube_url": f"https://www.youtube.com/watch?v={self.video_id}",
                      "clips": [{"filename": self.source.name, "clip_index": 1}]}]
        (self.foreign / "jobs.json").write_text(json.dumps(self.jobs), encoding="utf-8")
        (self.other.parent.parent / "jobs.json").write_text(json.dumps([{
            "id": "wrong", "youtube_url": "https://youtu.be/wrongID1234",
            "clips": [{"filename": self.other.name}]}]), encoding="utf-8")
        self.root_patch = mock.patch.object(publisher, "_runtime_data_root", return_value=self.local)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def stage(self):
        sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        identity = os.path.normcase(str(self.source.resolve()))
        key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
        name = f"source-{key}-{sha}.mp4"
        (self.local / "output" / name).write_bytes(self.source.read_bytes())
        (self.local / "posts.json").write_text(json.dumps([{
            "media_file": name, "source_video_path": identity, "source_sha256": sha,
        }]), encoding="utf-8")
        return name

    def test_verified_stage_imports_original_youtube_id_without_network(self):
        name = self.stage()
        meta = publisher.get_clip_metadata(name)
        self.assertEqual(meta["youtube_id"], self.video_id)
        self.assertEqual(meta["job_id"], "original_job")
        self.assertEqual(meta["clip_index"], 1)
        self.assertEqual(meta["video_title"], "Original Verifiable Source Story")

    def test_verified_stage_publish_prefers_embed_over_video_transport(self):
        name = self.stage()
        service = mock.Mock()
        service.publish_article.return_value = {
            "status": "success", "article_url": "https://example.test/blog/source"
        }
        with mock.patch.object(publisher, "get_website_config", return_value=(
            {"base_url": "https://example.test"}, mock.Mock(exists=mock.Mock(return_value=True))
        )), mock.patch.object(publisher.requests, "get", return_value=mock.Mock(status_code=404)), mock.patch.object(publisher, "upload_long_video_to_public_stream") as upload, mock.patch.object(
            publisher, "extract_and_upload_article_assets", return_value=("https://img.test/hero.jpg", ["https://img.test/one.jpg", "https://img.test/two.jpg"])
        ), mock.patch.object(publisher, "WebsiteArticleService", return_value=service):
            url, _ = publisher.publish_clip_to_website_cms(name)
        self.assertEqual(url, "https://example.test/blog/source")
        upload.assert_not_called()
        self.assertIn(f"youtube-nocookie.com/embed/{self.video_id}",
                      service.publish_article.call_args.kwargs["body_html"])

    def test_selected_foreign_path_uses_its_own_ledger_not_same_basename(self):
        meta = publisher.get_clip_metadata(str(self.source))
        self.assertEqual(meta["youtube_id"], self.video_id)
        self.assertEqual(publisher.get_clip_metadata(str(self.other))["youtube_id"], "wrongID1234")

    def test_same_basename_unverified_or_tampered_stage_does_not_import(self):
        name = self.stage()
        posts = self.local / "posts.json"
        posts.unlink()
        self.assertEqual(publisher.get_clip_metadata(name)["youtube_id"], "")
        self.stage()
        (self.local / "output" / name).write_bytes(b"tampered")
        self.assertEqual(publisher.get_clip_metadata(name)["youtube_id"], "")

    def test_source_changed_or_ledger_tampered_does_not_import(self):
        name = self.stage()
        self.source.write_bytes(b"changed after staging")
        self.assertEqual(publisher.get_clip_metadata(name)["youtube_id"], "")
        self.source.write_bytes(b"the exact source clip")
        posts = self.local / "posts.json"
        records = json.loads(posts.read_text(encoding="utf-8"))
        records[0]["source_video_path"] = str(self.other)
        posts.write_text(json.dumps(records), encoding="utf-8")
        self.assertEqual(publisher.get_clip_metadata(name)["youtube_id"], "")

    def test_local_job_must_match_local_clip_not_foreign_basename(self):
        (self.local / "jobs.json").write_text(json.dumps(self.jobs), encoding="utf-8")
        (self.local / "output" / self.source.name).write_bytes(self.source.read_bytes())
        self.assertEqual(publisher.get_clip_metadata(self.source.name)["youtube_id"], self.video_id)
        self.assertEqual(publisher.get_clip_metadata(str(self.other))["youtube_id"], "wrongID1234")

    def test_missing_local_clip_and_ambiguous_job_fail_closed(self):
        (self.local / "jobs.json").write_text(json.dumps(self.jobs), encoding="utf-8")
        self.assertEqual(publisher.get_clip_metadata(self.source.name)["youtube_id"], "")
        name = self.stage()
        (self.foreign / "jobs.json").write_text(json.dumps(self.jobs * 2), encoding="utf-8")
        self.assertEqual(publisher.get_clip_metadata(name)["youtube_id"], "")


if __name__ == "__main__":
    unittest.main()
