"""Mask fixes for video cutouts (mines-ghost, github.com/kuromatcha/mines-ghost).

- mask temporal smooth: steadies a per-frame mask (background removal run frame by frame) over time, so edges
  stop flickering. Neighbouring frames are first lined up with this frame by their motion, so swaying or moving
  parts are smoothed too, without ghosting.

Needs torch and OpenCV (both come with ComfyUI).
"""
import numpy as np
import torch
import torch.nn.functional as F


def _device():
    try:
        import comfy.model_management
        return comfy.model_management.get_torch_device()
    except ImportError:  # outside ComfyUI (tests)
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")


FLOW_SIDE = 768  # longer side of the copy the motion is measured on


def _flow(dis, a, b):
    """Optical flow from gray frame a to gray frame b (uint8, small size): for each pixel of a, where it is in b."""
    return dis.calc(a, b, None)


def smooth_masks(images, masks, radius=2, match_threshold=0.06, loop=False, device=None):
    """images (N, H, W, C) 0..1, masks (N, h, w) 0..1 -> smoothed masks (N, h, w) on the CPU.

    For each frame, the frames up to `radius` away are warped onto it with optical flow, picture and mask together.
    The mask becomes a weighted average of this frame's mask and the warped ones. A warped neighbour counts fully
    where its warped picture matches this frame, and stops counting as the mean absolute RGB difference reaches
    `match_threshold`, so places the flow got wrong (fast motion, things appearing) keep this frame's own mask."""
    import cv2
    device = device or _device()
    n, h, w = masks.shape
    if n < 2 or radius < 1:
        return masks.clone()
    s = FLOW_SIDE / max(h, w)
    fh, fw = max(8, round(h * s)), max(8, round(w * s))
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)

    def small_gray(i):
        img = images[i, ..., :3].to(torch.float32).permute(2, 0, 1)[None]
        img = F.interpolate(img, size=(fh, fw), mode="area")[0]
        g = (0.299 * img[0] + 0.587 * img[1] + 0.114 * img[2]).clamp(0, 1)
        return (g * 255).round().to(torch.uint8).numpy()

    def full(i):
        img = images[i:i + 1, ..., :3].to(device, torch.float32).permute(0, 3, 1, 2)
        if img.shape[-2:] != (h, w):
            img = F.interpolate(img, size=(h, w), mode="area")
        return img, masks[i:i + 1].to(device, torch.float32)[:, None]

    gray = [small_gray(i) for i in range(n)]
    ys, xs = torch.meshgrid(torch.linspace(-1, 1, h, device=device), torch.linspace(-1, 1, w, device=device),
                            indexing="ij")
    base = torch.stack([xs, ys], -1)[None]
    out = torch.empty((n, h, w), dtype=masks.dtype)
    for t in range(n):
        img_t, m_t = full(t)
        acc, wsum = m_t.clone(), torch.ones_like(m_t)
        for off in range(-radius, radius + 1):
            k = t + off
            if off == 0:
                continue
            if loop:
                k %= n
            elif not 0 <= k < n:
                continue
            fl = torch.from_numpy(_flow(dis, gray[t], gray[k])).to(device).permute(2, 0, 1)[None]
            fl = F.interpolate(fl, size=(h, w), mode="bilinear", align_corners=False)
            grid = base + torch.stack([fl[:, 0] * 2 / max(fw - 1, 1), fl[:, 1] * 2 / max(fh - 1, 1)], -1)
            img_k, m_k = full(k)
            img_w = F.grid_sample(img_k, grid, mode="bilinear", padding_mode="border", align_corners=True)
            m_w = F.grid_sample(m_k, grid, mode="bilinear", padding_mode="border", align_corners=True)
            diff = F.avg_pool2d((img_w - img_t).abs().mean(1, keepdim=True), 5, stride=1, padding=2,
                                count_include_pad=False)
            wk = (1 - diff / match_threshold).clamp(0, 1) ** 2
            acc += wk * m_w
            wsum += wk
        out[t] = (acc / wsum)[0, 0].cpu().to(masks.dtype)
    return out


class _ChunkedBackgroundRemoval:
    """Wraps a built-in background removal model so a video is sent to the GPU a few frames at a time.

    The built-in Remove Background moves the whole batch to the GPU and resizes it there at once; for a few hundred
    full-size frames at 2048 that is far more than a 16 GB card holds."""

    def __init__(self, model, image_size, chunk):
        self._model, self.image_size, self.chunk = model, image_size, chunk

    def __getattr__(self, name):
        return getattr(self._model, name)

    def encode_image(self, image):
        import copy
        m = copy.copy(self._model)
        m.image_size = self.image_size
        try:
            from comfy.utils import ProgressBar
            pbar = ProgressBar(image.shape[0])
        except ImportError:
            pbar = None
        out = []
        for i in range(0, image.shape[0], self.chunk):
            out.append(m.encode_image(image[i:i + self.chunk]))
            if pbar is not None:
                pbar.update(min(self.chunk, image.shape[0] - i))
        return torch.cat(out)


class MinesBackgroundRemovalResolution:
    """ComfyUI's built-in background removal runs every BiRefNet model at 1024 x 1024. BiRefNet-HR is trained at
    2048 and sees thin hair and fine edges much better there (and they flicker much less in video)."""

    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                    "bg_model": ("BACKGROUND_REMOVAL", {"tooltip": "From Load Background Removal Model."}),
                    "resolution": ("INT", {"default": 2048, "min": 256, "max": 4096, "step": 32,
                                           "tooltip": "Size of the square the model works on. 2048 for "
                                                      "BiRefNet-HR, 1024 for the standard BiRefNet."}),
                }}

    RETURN_TYPES = ("BACKGROUND_REMOVAL",)
    RETURN_NAMES = ("bg_model",)
    FUNCTION = "set"
    CATEGORY = "image/background removal"
    DESCRIPTION = ("Sets the working resolution of a background removal model (the built-in loader always uses "
                   "1024). Use 2048 for BiRefNet-HR.")

    CHUNK = 4  # frames sent to the GPU at once

    def set(self, bg_model, resolution=2048):
        if isinstance(bg_model, _ChunkedBackgroundRemoval):
            bg_model = bg_model._model
        if not hasattr(bg_model, "image_size"):
            raise ValueError("This background removal model has no resolution setting.")
        # shares the loaded weights; only the resolution differs, and frames go to the GPU a few at a time
        return (_ChunkedBackgroundRemoval(bg_model, int(resolution), self.CHUNK),)


class MinesMaskTemporalSmooth:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                    "images": ("IMAGE", {"tooltip": "The frames the mask was made from."}),
                    "mask": ("MASK", {"tooltip": "One mask per frame, e.g. from Remove Background."}),
                    "radius": ("INT", {"default": 2, "min": 1, "max": 8, "step": 1,
                                       "tooltip": "How many frames before and after to average with. More is "
                                                  "steadier but slower."}),
                    "match_threshold": ("FLOAT", {"default": 0.06, "min": 0.01, "max": 0.3, "step": 0.01,
                                                  "tooltip": "How closely a neighbour frame, lined up by its motion, "
                                                             "must match this frame at a pixel to count there. Lower "
                                                             "is safer on fast motion; higher smooths more."}),
                    "loop": ("BOOLEAN", {"default": False,
                                         "tooltip": "On for looping clips: the first and last frames are "
                                                    "smoothed with each other."}),
                }}

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "smooth"
    CATEGORY = "mask"
    DESCRIPTION = ("Steadies a per-frame mask over time so its edges stop flickering. Neighbouring frames are lined "
                   "up by their motion first, so moving parts are smoothed without ghosting.")

    def smooth(self, images, mask, radius=2, match_threshold=0.06, loop=False):
        if mask.shape[0] != images.shape[0]:
            raise ValueError(f"mask has {mask.shape[0]} frames but images has {images.shape[0]}.")
        return (smooth_masks(images, mask, radius, match_threshold, loop),)
