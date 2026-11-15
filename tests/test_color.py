"""Run directly with ComfyUI's Python; needs torch and kornia, both included with ComfyUI."""
import importlib.util
import unittest
from pathlib import Path

import kornia
import torch

spec = importlib.util.spec_from_file_location("color", Path(__file__).parents[1] / "color.py")
color = importlib.util.module_from_spec(spec)
spec.loader.exec_module(color)


def scene(n=49, h=96, w=72):
    """A still picture with a red box sliding in from frame 20 and a 2-frame flash at frame 30."""
    g = torch.Generator().manual_seed(0)
    base = torch.rand(h // 8, w // 8, 3, generator=g).repeat_interleave(8, 0).repeat_interleave(8, 1) * 0.6 + 0.2
    frames = []
    for t in range(n):
        f = base.clone()
        if t >= 20:
            x0 = max(0, w - (t - 20) * 3)
            f[30:60, x0:x0 + 24] = torch.tensor([0.9, 0.1, 0.1])
        if t in (30, 31):
            f = (f * 1.2).clamp(0, 1)
        frames.append(f)
    return torch.stack(frames)


def drift(video):
    """Darker, warmer and more saturated toward the end."""
    lab = kornia.color.rgb_to_lab(video.permute(0, 3, 1, 2))
    p = torch.linspace(0, 1, len(video)).view(-1, 1, 1)
    lab[:, 0] -= 8 * p
    lab[:, 2] += 10 * p
    lab[:, 1:] *= (1 + 0.15 * p).unsqueeze(1)
    return kornia.color.lab_to_rgb(lab).permute(0, 2, 3, 1).clamp(0, 1)


def lab_error(a, b):
    la = kornia.color.rgb_to_lab(a.permute(0, 3, 1, 2))
    lb = kornia.color.rgb_to_lab(b.permute(0, 3, 1, 2))
    return (la - lb).abs().mean(dim=(1, 2, 3))


class ColorDriftFixTests(unittest.TestCase):
    def test_removes_drift_keeps_motion_and_flash(self):
        clean = scene()
        fixed = color.MinesColorDriftFix().fix(drift(clean), 1.0, 16)[0]
        before, after = lab_error(drift(clean), clean), lab_error(fixed, clean)
        self.assertLess(after[-1], before[-1] * 0.25)
        self.assertLess(after.mean(), before.mean() * 0.25)
        self.assertLess(after[0], 0.05)

    def test_strength_zero_is_unchanged(self):
        video = drift(scene())
        self.assertTrue(torch.equal(color.MinesColorDriftFix().fix(video, 0.0, 16)[0], video))

    def test_nan_frames_raise(self):
        video = drift(scene())
        video[5] = float("nan")
        with self.assertRaises(ValueError):
            color.MinesColorDriftFix().fix(video, 1.0, 16)


class KeepSourceColorsTests(unittest.TestCase):
    def test_restores_colors_after_upscale(self):
        source = scene(n=6)
        up = torch.nn.functional.interpolate(source.permute(0, 3, 1, 2), scale_factor=2, mode="bicubic").permute(0, 2, 3, 1).clamp(0, 1)
        shifted = drift(up)
        kept = color.MinesKeepSourceColors().keep(shifted, source)[0]
        self.assertEqual(kept.shape, shifted.shape)
        self.assertLess(lab_error(kept, up)[-1], lab_error(shifted, up)[-1] * 0.25)

    def test_frame_count_must_match(self):
        with self.assertRaises(ValueError):
            color.MinesKeepSourceColors().keep(scene(n=4), scene(n=3))


if __name__ == "__main__":
    unittest.main()
