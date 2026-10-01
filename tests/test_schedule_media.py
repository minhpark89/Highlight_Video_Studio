import hashlib
import tempfile
import unittest
from pathlib import Path

from src.publisher.schedule_media import selected_video, stage_video


class ScheduleMediaTests(unittest.TestCase):
    def test_selection_rejects_traversal_and_foreign_absolute_same_basename(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'selected'
            folder.mkdir()
            (folder / 'clip.mp4').write_bytes(b'correct')
            foreign = root / 'clip.mp4'
            foreign.write_bytes(b'wrong')
            self.assertEqual(selected_video(folder, 'clip.mp4'), folder / 'clip.mp4')
            for value in ('../clip.mp4', str(foreign), 'sub/clip.mp4', 'sub\\clip.mp4'):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    selected_video(folder, value)

    def test_symlink_escape_is_rejected_where_supported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'selected'
            folder.mkdir()
            foreign = root / 'secret.mp4'
            foreign.write_bytes(b'secret')
            link = folder / 'clip.mp4'
            try:
                link.symlink_to(foreign)
            except (OSError, NotImplementedError):
                self.skipTest('symlink creation not available')
            with self.assertRaises(ValueError):
                selected_video(folder, 'clip.mp4')

    def test_digest_collision_and_repeat_are_safe(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'output'
            output.mkdir()
            folder = root / 'selected'
            folder.mkdir()
            source = folder / 'clip.mp4'
            source.write_bytes(b'expected')
            name, digest, identity = stage_video(selected_video(folder, 'clip.mp4'), output)
            self.assertEqual(digest, hashlib.sha256(b'expected').hexdigest())
            self.assertEqual((output / name).read_bytes(), b'expected')
            self.assertEqual(stage_video(source, output), (name, digest, identity))
            (output / name).write_bytes(b'poison')
            with self.assertRaisesRegex(ValueError, 'collision'):
                stage_video(source, output)
            self.assertEqual((output / name).read_bytes(), b'poison')
            self.assertEqual(list(output.glob('.stage-*')), [])

    def test_same_basename_different_folder_produces_distinct_media(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'output'
            output.mkdir()
            for folder_name in ('a', 'b'):
                folder = root / folder_name
                folder.mkdir()
                (folder / 'clip.mp4').write_bytes(folder_name.encode())
            a, _, _ = stage_video(root / 'a' / 'clip.mp4', output)
            b, _, _ = stage_video(root / 'b' / 'clip.mp4', output)
            self.assertNotEqual(a, b)
            self.assertEqual((output / a).read_bytes(), b'a')
            self.assertEqual((output / b).read_bytes(), b'b')
