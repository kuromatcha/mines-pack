"""Run directly with Python; needs Pillow, already included with ComfyUI."""
import importlib.util
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from PIL import Image

spec = importlib.util.spec_from_file_location("png", Path(__file__).parents[1] / "png.py")
png = importlib.util.module_from_spec(spec)
spec.loader.exec_module(png)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.png"
        Image.new("RGB", (16, 16), (12, 34, 56)).save(self.source)
        self.dest = self.root / "exports"

    def save(self, **kwargs):
        return png.export_png(self.source, self.dest, kwargs.pop("prefix", ""),
                                   kwargs.pop("padding", 5), **kwargs)

    def test_empty_and_gaps(self):
        self.assertEqual(self.save().name, "00001.png")
        Image.new("RGB", (1, 1)).save(self.dest / "00046.png")
        (self.dest / "unrelated99999.png").touch()
        (self.dest / "99999.txt").touch()
        self.assertEqual(self.save().name, "00047.png")

    def test_prefix_padding_and_overflow(self):
        self.save(prefix="face_", padding=2)
        (self.dest / "face_00046.PNG").touch()
        self.assertEqual(self.save(prefix="face_", padding=2).name, "face_47.png")
        (self.dest / "face_99999.png").touch()
        self.assertEqual(self.save(prefix="face_").name, "face_100000.png")
        self.assertEqual(self.save(prefix="other_").name, "other_00001.png")

    def test_metadata_and_pixels(self):
        a = self.save(metadata={"prompt": {"seed": 42}, "workflow": {"nodes": []}})
        b = self.save()
        with Image.open(a) as first, Image.open(b) as second:
            self.assertIn("prompt", first.info)
            self.assertIn("workflow", first.info)
            self.assertEqual(second.info, {})
            self.assertEqual(first.tobytes(), second.tobytes())
            self.assertEqual(second.getpixel((0, 0)), (12, 34, 56))

    def test_concurrent_saves(self):
        self.dest.mkdir()
        with ThreadPoolExecutor(max_workers=8) as executor:
            paths = list(executor.map(lambda _: self.save(), range(24)))
        self.assertEqual(len(set(paths)), 24)
        self.assertEqual(sorted(int(p.stem) for p in paths), list(range(1, 25)))
        for path in paths:
            with Image.open(path) as image:
                image.verify()

    def test_validation(self):
        for prefix in ["../escape", "a\\b", "bad:", "a\x00b"]:
            with self.assertRaises(ValueError):
                self.save(prefix=prefix)
        for padding in [0, 13, True, "5"]:
            with self.assertRaises(ValueError):
                self.save(padding=padding)

    def test_write_failure_removes_partial(self):
        with patch.object(png.os, "fsync", side_effect=OSError("Disk full")):
            with self.assertRaises(OSError):
                self.save()
        self.assertEqual(list(self.dest.glob("*.png")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
