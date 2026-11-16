"""Inpaint crop and stitch for the Mine's Anima Inpaint workflow.

- inpaint crop: cuts the painted area out with some of its surroundings and scales the cut to the model's working
  size, so a small area is redrawn at full detail instead of at its size in the picture.
- inpaint stitch: scales the redrawn cut back and blends it into the original picture with a soft edge. Everything
  outside the blend keeps the original pixels exactly.

Needs torch only.
"""
import math

import torch
import torch.nn.functional as F

STEP = 16        # the cut's width and height are multiples of this
MIN_SIDE = 256   # smallest cut, so a tiny mask still comes with enough surroundings to match
MAX_ASPECT = 2   # longest side : shortest side of the cut


def _grow(mask, pixels):
    """mask (N, 1, H, W) -> the mask widened by `pixels` on every side."""
    if pixels <= 0:
        return mask
    mask = F.max_pool2d(mask, (1, 2 * pixels + 1), stride=1, padding=(0, pixels))
    return F.max_pool2d(mask, (2 * pixels + 1, 1), stride=1, padding=(pixels, 0))


def _blur(mask, radius):
    """mask (N, 1, H, W) -> Gaussian blur reaching `radius` pixels."""
    if radius <= 0:
        return mask
    k = torch.arange(-radius, radius + 1, dtype=mask.dtype)
    k = torch.exp(-k ** 2 / (2 * (radius / 2) ** 2))
    k = k / k.sum()
    mask = F.conv2d(F.pad(mask, (radius, radius, 0, 0), mode="replicate"), k.view(1, 1, 1, -1))
    return F.conv2d(F.pad(mask, (0, 0, radius, radius), mode="replicate"), k.view(1, 1, -1, 1))


def _fit(start, size, limit):
    """Move a span of `size` starting at `start` so it lies inside 0..limit."""
    return max(0, min(round(start), limit - size))


def crop_box(mask, megapixels=1.0, context=2.0, margin=0):
    """mask (H, W) bool -> (x, y, w, h) of the cut and its (width, height) at the working size.

    The cut is the mask's bounding box times `context`, at least `margin` pixels wider than the mask on each side,
    kept inside the picture. Its shape is nudged to the working size's shape so scaling does not stretch it."""
    H, W = mask.shape
    xs, ys = mask.any(0).nonzero().flatten(), mask.any(1).nonzero().flatten()
    if xs.numel() == 0:
        raise ValueError("The mask is empty. Right-click the image, open the mask editor and paint the area to redraw.")
    x0, x1, y0, y1 = xs[0].item(), xs[-1].item() + 1, ys[0].item(), ys[-1].item() + 1
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    w = max((x1 - x0) * context, x1 - x0 + 2 * margin, MIN_SIDE)
    h = max((y1 - y0) * context, y1 - y0 + 2 * margin, MIN_SIDE)
    w, h = max(w, h / MAX_ASPECT), max(h, w / MAX_ASPECT)
    w, h = min(round(w), W), min(round(h), H)

    scale = math.sqrt(megapixels * 1024 * 1024 / (w * h))
    tw = max(STEP, round(w * scale / STEP) * STEP)
    th = max(STEP, round(h * scale / STEP) * STEP)
    if w <= round(h * tw / th) <= W:
        w = round(h * tw / th)
    elif h <= round(w * th / tw) <= H:
        h = round(w * th / tw)
    return (_fit(cx - w / 2, w, W), _fit(cy - h / 2, h, H), w, h), (tw, th)


def inpaint_crop(image, mask, megapixels=1.0, context=2.0, grow=8, blend=16):
    """image (N, H, W, C) 0..1, mask (n, h, w) 0..1 -> cut (N, th, tw, 3), its mask (n, th, tw) 0 or 1, stitch data.

    The mask is widened by `grow` pixels; that is the area the model redraws. The stitch blend is that area widened
    and blurred by another `blend` pixels, so the seam falls on pixels the model was told to keep."""
    image = image[..., :3].float().cpu()
    H, W = image.shape[1:3]
    mask = mask.reshape(-1, 1, *mask.shape[-2:]).float().cpu()
    if mask.shape[-2:] != (H, W):
        mask = F.interpolate(mask, size=(H, W), mode="bilinear")
    area = _grow((mask >= 0.5).float(), grow)
    soft = torch.maximum(_blur(_grow(area, blend), blend), area)

    (x, y, w, h), (tw, th) = crop_box(area.amax(dim=(0, 1)) > 0, megapixels, context, 2 * blend + grow)
    cut = F.interpolate(image[:, y:y + h, x:x + w].movedim(-1, 1), size=(th, tw), mode="bicubic", antialias=True)
    cut_mask = F.interpolate(area[:, :, y:y + h, x:x + w], size=(th, tw), mode="bilinear")
    stitch = {"image": image, "box": (x, y, w, h), "blend": soft[:, :, y:y + h, x:x + w].clone()}
    return cut.clamp(0, 1).movedim(1, -1), (cut_mask[:, 0] >= 0.5).float(), stitch


def inpaint_stitch(stitch, image):
    """Scale the redrawn cut (N, th, tw, C) back to its box and blend it into the original picture."""
    x, y, w, h = stitch["box"]
    out = stitch["image"].clone()
    patch = F.interpolate(image[..., :3].float().cpu().movedim(-1, 1), size=(h, w), mode="bicubic", antialias=True)
    if out.shape[0] == 1 and patch.shape[0] > 1:
        out = out.repeat(patch.shape[0], 1, 1, 1)
    region = out[:, y:y + h, x:x + w].movedim(-1, 1)
    out[:, y:y + h, x:x + w] = torch.lerp(region, patch.clamp(0, 1), stitch["blend"]).movedim(1, -1)
    return out


class MinesInpaintCrop:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "mask": ("MASK", {"tooltip": "White = the area to redraw."}),
            "megapixels": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 4.0, "step": 0.05,
                                     "tooltip": "Working size of the cut. Anima: 1.0, up to about 2.3."}),
            "context": ("FLOAT", {"default": 2.0, "min": 1.0, "max": 8.0, "step": 0.1,
                                  "tooltip": "Size of the cut as a multiple of the masked area. Higher: the model sees "
                                             "more of the picture and matches it better. Lower: more detail."}),
            "grow": ("INT", {"default": 8, "min": 0, "max": 256, "tooltip": "Widen the mask by this many pixels."}),
            "blend": ("INT", {"default": 16, "min": 0, "max": 256,
                              "tooltip": "Width in pixels of the soft edge when the cut is put back."}),
        }}

    RETURN_TYPES = ("IMAGE", "MASK", "MINES_STITCH")
    RETURN_NAMES = ("image", "mask", "stitch")
    FUNCTION = "crop"
    DESCRIPTION = "Cuts the masked area out with its surroundings and scales it to the model's working size."

    def crop(self, image, mask, megapixels, context, grow, blend):
        return inpaint_crop(image, mask, megapixels, context, grow, blend)


class MinesInpaintStitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "stitch": ("MINES_STITCH",),
            "image": ("IMAGE", {"tooltip": "The redrawn cut."}),
        }}

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "stitch"
    DESCRIPTION = "Blends the redrawn cut back into the original picture. Pixels outside the blend are unchanged."

    def stitch(self, stitch, image):
        return (inpaint_stitch(stitch, image),)
