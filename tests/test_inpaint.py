import importlib.util
import pathlib
import unittest

import torch

spec = importlib.util.spec_from_file_location("inpaint", pathlib.Path(__file__).parents[1] / "inpaint.py")
inpaint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inpaint)


def scene(h=1200, w=1600, box=(700, 400, 200, 120)):
    """A noisy picture and a mask over `box` (x, y, w, h)."""
    torch.manual_seed(0)
    image = torch.rand(1, h, w, 3)
    mask = torch.zeros(1, h, w)
    x, y, bw, bh = box
    mask[:, y:y + bh, x:x + bw] = 1.0
    return image, mask


class InpaintCropTest(unittest.TestCase):
    def test_cut_size_and_shape(self):
        image, mask = scene()
        cut, cut_mask, stitch = inpaint.inpaint_crop(image, mask, megapixels=1.0)
        th, tw = cut.shape[1:3]
        self.assertEqual((th % 16, tw % 16), (0, 0))
        self.assertAlmostEqual(th * tw / 1024 ** 2, 1.0, delta=0.06)
        self.assertEqual(cut_mask.shape, (1, th, tw))
        self.assertEqual(set(cut_mask.unique().tolist()), {0.0, 1.0})
        x, y, w, h = stitch["box"]
        self.assertAlmostEqual(w / h, tw / th, delta=0.01)  # no stretching

    def test_cut_contains_mask_and_stays_inside(self):
        for box in [(0, 0, 50, 50), (1500, 1100, 100, 100), (100, 500, 1400, 40), (0, 0, 1600, 1200)]:
            image, mask = scene(box=box)
            _, _, stitch = inpaint.inpaint_crop(image, mask, grow=8, blend=16)
            x, y, w, h = stitch["box"]
            self.assertTrue(0 <= x and 0 <= y and x + w <= 1600 and y + h <= 1200, box)
            outside = mask.clone()
            outside[:, y:y + h, x:x + w] = 0
            self.assertEqual(outside.sum().item(), 0, box)
            self.assertLessEqual(max(w / h, h / w), 2.05, box)

    def test_blend_is_zero_at_cut_edges_inside_the_picture(self):
        image, mask = scene()
        _, _, stitch = inpaint.inpaint_crop(image, mask, grow=8, blend=32)
        blend = stitch["blend"][0, 0]
        edges = torch.cat([blend[0], blend[-1], blend[:, 0], blend[:, -1]])
        self.assertLess(edges.max().item(), 0.01)

    def test_empty_mask_raises(self):
        image, mask = scene()
        with self.assertRaises(ValueError):
            inpaint.inpaint_crop(image, torch.zeros_like(mask))

    def test_mask_of_another_size_is_resized(self):
        image, mask = scene()
        small = torch.nn.functional.interpolate(mask[None], scale_factor=0.5)[0]
        _, _, a = inpaint.inpaint_crop(image, mask)
        _, _, b = inpaint.inpaint_crop(image, small)
        self.assertEqual(a["box"], b["box"])


class InpaintStitchTest(unittest.TestCase):
    def test_outside_is_untouched_and_inside_replaced(self):
        image, mask = scene()
        cut, _, stitch = inpaint.inpaint_crop(image, mask, grow=8, blend=16)
        out = inpaint.inpaint_stitch(stitch, torch.ones_like(cut))
        self.assertEqual(out.shape, image.shape)
        self.assertTrue(torch.equal(image, stitch["image"]))  # the original is not written to
        x, y, w, h = stitch["box"]
        keep = torch.ones(1, 1200, 1600, dtype=torch.bool)
        keep[:, y:y + h, x:x + w] = False
        self.assertTrue(torch.equal(out[keep], image[keep]))
        self.assertTrue(torch.allclose(out[mask > 0.5], torch.ones(1), atol=1e-4))

    def test_round_trip_keeps_the_picture(self):
        image, mask = scene()
        image = torch.nn.functional.avg_pool2d(image.movedim(-1, 1), 9, 1, 4).movedim(1, -1)  # smooth picture
        cut, _, stitch = inpaint.inpaint_crop(image, mask)
        out = inpaint.inpaint_stitch(stitch, cut)
        self.assertLess((out - image).abs().max().item(), 0.02)

    def test_batch_of_results(self):
        image, mask = scene()
        cut, _, stitch = inpaint.inpaint_crop(image, mask)
        out = inpaint.inpaint_stitch(stitch, cut.repeat(3, 1, 1, 1))
        self.assertEqual(out.shape[0], 3)


if __name__ == "__main__":
    unittest.main()
