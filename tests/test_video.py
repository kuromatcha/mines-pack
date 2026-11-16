import importlib.util
import pathlib
import sys
import types
import unittest

import torch

# video.py imports ComfyUI modules; stub the few names it touches only while it loads, then put sys.modules back
# so the other test files see the real (or their own) modules.
STUBS = ("comfy", "comfy.latent_formats", "comfy.model_management", "comfy.utils", "node_helpers", "nodes")
saved = {name: sys.modules.get(name) for name in STUBS}
try:
    for name in STUBS:
        sys.modules[name] = types.ModuleType(name)
    sys.modules["nodes"].LoadImage = type("LoadImage", (), {})
    sys.modules["nodes"].MAX_RESOLUTION = 16384
    spec = importlib.util.spec_from_file_location("video", pathlib.Path(__file__).parents[1] / "video.py")
    video = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(video)
finally:
    for name, module in saved.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


class FakeAddGuide:
    """Records each call and appends the frame index to the conditioning, like the real node appends a keyframe."""
    calls = []

    @classmethod
    def execute(cls, positive, latent, frame_idx, vae=None, image=None):
        cls.calls.append((frame_idx, tuple(image.shape), vae, latent))
        return (positive + [frame_idx],)


class H3FrameGuidesTest(unittest.TestCase):
    def setUp(self):
        FakeAddGuide.calls = []
        video._h3_add_guide = lambda: FakeAddGuide
        self.node = video.MinesH3FrameGuides()

    def test_first_and_last(self):
        first, last = torch.zeros(1, 64, 48, 3), torch.ones(2, 64, 48, 3)
        (out,) = self.node.guide(["cond"], "vae", "latent", first_frame=first, last_frame=last)
        self.assertEqual(out, ["cond", 0, -1])
        self.assertEqual([c[0] for c in FakeAddGuide.calls], [0, -1])
        self.assertEqual(FakeAddGuide.calls[1][1], (1, 64, 48, 3))  # only the first image of a batch is pinned
        self.assertEqual(FakeAddGuide.calls[0][2:], ("vae", "latent"))

    def test_missing_frames_are_skipped(self):
        (out,) = self.node.guide(["cond"], "vae", "latent", first_frame=torch.zeros(1, 8, 8, 3), last_frame=None)
        self.assertEqual(out, ["cond", 0])
        (out,) = self.node.guide(["cond"], "vae", "latent")
        self.assertEqual(out, ["cond"])

    def test_last_only(self):
        (out,) = self.node.guide(["cond"], "vae", "latent", last_frame=torch.zeros(1, 8, 8, 3))
        self.assertEqual(out, ["cond", -1])


if __name__ == "__main__":
    unittest.main()
