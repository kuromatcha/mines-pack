import importlib.util
import pathlib
import unittest

import torch

spec = importlib.util.spec_from_file_location("mask", pathlib.Path(__file__).parents[1] / "mask.py")
mask = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mask)


def scene(n=12, h=96, w=128, step=0):
    """A bright square on a dark background, moving `step` pixels right per frame, and its exact mask."""
    images = torch.full((n, h, w, 3), 0.1)
    masks = torch.zeros(n, h, w)
    for t in range(n):
        x = 30 + step * t
        images[t, 30:66, x:x + 40] = 0.9
        masks[t, 30:66, x:x + 40] = 1.0
    return images, masks


class MaskTemporalSmoothTest(unittest.TestCase):
    def test_still_flicker_is_reduced(self):
        images, clean = scene()
        torch.manual_seed(0)
        noisy = (clean + 0.3 * torch.randn_like(clean) * (clean.roll(1, 2) != clean).float()).clamp(0, 1)
        out = mask.smooth_masks(images, noisy, radius=3, device=torch.device("cpu"))
        before = (noisy[1:] - noisy[:-1]).abs().mean()
        after = (out[1:] - out[:-1]).abs().mean()
        self.assertLess(after, before * 0.6)

    def test_moving_edge_does_not_ghost(self):
        images, clean = scene(step=3)
        out = mask.smooth_masks(images, clean, radius=2, device=torch.device("cpu"))
        self.assertLess((out - clean).abs().mean().item(), 0.01)

    def test_shape_and_single_frame(self):
        images, clean = scene(n=1)
        out = mask.smooth_masks(images, clean, device=torch.device("cpu"))
        self.assertEqual(out.shape, clean.shape)
        self.assertTrue(torch.equal(out, clean))

    def test_frame_count_mismatch(self):
        images, clean = scene(n=4)
        with self.assertRaises(ValueError):
            mask.MinesMaskTemporalSmooth().smooth(images, clean[:3])


class BackgroundRemovalResolutionTest(unittest.TestCase):
    def test_sets_size_and_runs_in_chunks(self):
        calls = []

        class Model:
            image_size = 1024

            def encode_image(self, image):
                calls.append((image.shape[0], self.image_size))
                return torch.zeros(image.shape[0], 8, 8)
        m = Model()
        (out,) = mask.MinesBackgroundRemovalResolution().set(m, 2048)
        res = out.encode_image(torch.zeros(10, 8, 8, 3))
        self.assertEqual(out.image_size, 2048)
        self.assertEqual(m.image_size, 1024)
        self.assertEqual(res.shape[0], 10)
        self.assertEqual(calls, [(4, 2048), (4, 2048), (2, 2048)])

    def test_rejects_model_without_size(self):
        with self.assertRaises(ValueError):
            mask.MinesBackgroundRemovalResolution().set(object(), 2048)


if __name__ == "__main__":
    unittest.main()
