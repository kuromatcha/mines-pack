"""Color fixes for generated video (Mine's video workflows, github.com/kuromatcha/mines-I2V).

- color drift fix: removes slow color drift over a clip so later frames keep the tone of the first frame; in a
  loop the end matches the start.
- keep source colors: gives upscaled frames back the exact colors of the frames before upscaling.

Needs torch and kornia (both come with ComfyUI).
"""
import torch


def _device():
    try:
        import comfy.model_management
        return comfy.model_management.get_torch_device()
    except ImportError:  # outside ComfyUI (tests)
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class MinesColorDriftFix:
    """Removes slow color drift over a clip while leaving real changes (motion, new objects, flashes) alone.

    Every frame is compared with frame 1 on the pixels that still match it (background, parts that did not move;
    pixels that moved disagree and are dropped). From those pixels a tone curve per Lab channel is measured: how
    much each brightness level, and each amount of red/green and yellow/blue, has shifted. A curve, not one gain and
    offset, because drift is rarely uniform: skin can get brighter and paler while a white wall turns grey. When too
    few pixels still match frame 1 (big motion, a camera move), the step from the previous frame is chained on
    instead. The curves are smoothed over time, so a short flash does not count, and each frame is mapped back.
    Frame 1 is unchanged. In a loop, the last frames return to the first pose, so they match frame 1 closely and
    get the most exact correction: the end has the tone of the start and the loop closes without a tone jump.
    With image_ref connected, frame 1 is also matched to that image the same way."""

    STAT_SIZE = 160  # longer side of the small copy the fits run on
    MIN_MATCH = 0.2  # share of pixels that must still match frame 1 to fit against it directly
    # tone curve knots per Lab channel: L 0..100, a and b -60..60
    KNOT_LO = (0.0, -60.0, -60.0)
    KNOT_STEP = (5.0, 5.0, 5.0)
    KNOT_COUNT = (21, 25, 25)
    PRIOR = 5.0  # pixels: a knot with few pixels leans toward the channel's overall shift
    SMOOTH = 50.0  # how strongly neighbouring knots are kept alike
    MAX_SHIFT = (20.0, 15.0, 15.0)  # largest correction per Lab channel

    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                    "images": ("IMAGE",),
                    "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.5, "step": 0.05,
                                           "tooltip": "1 removes the measured drift fully, 0 leaves the video unchanged."}),
                    "smooth_frames": ("INT", {"default": 16, "min": 1, "max": 241, "step": 1,
                                              "tooltip": "Changes shorter than about this many frames (flashes) are "
                                                         "kept; slower drift is removed."}),
                },
                "optional": {
                    "image_ref": ("IMAGE", {"tooltip": "Optional: also match the first frame to this image "
                                                       "(the start image)."}),
                }}

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "fix"
    CATEGORY = "image/postprocessing"
    DESCRIPTION = ("Removes slow color drift (brightness, warmth, saturation, skin tone) over a video so later frames "
                   "keep the tone of the first frame; in a loop the end matches the start. Motion, new objects and "
                   "short flashes are left alone.")

    @classmethod
    def _small_lab(cls, frames, device):
        """Small Lab copies of the frames, shape (N, 3, h, w)."""
        import kornia
        out = []
        for i in range(frames.shape[0]):
            x = frames[i:i + 1, ..., :3].to(device).movedim(-1, 1).float().clamp(0, 1)
            h, w = x.shape[-2:]
            scale = cls.STAT_SIZE / max(h, w)
            if scale < 1:
                x = torch.nn.functional.interpolate(x, size=(max(8, round(h * scale)), max(8, round(w * scale))), mode="area")
            out.append(kornia.color.rgb_to_lab(x))
        return torch.cat(out)

    @classmethod
    def _knots(cls, device):
        lo = torch.tensor(cls.KNOT_LO, device=device)
        step = torch.tensor(cls.KNOT_STEP, device=device)
        return lo, step

    @classmethod
    def _apply_curve(cls, x, curve):
        """x (3, ...) Lab values, curve: list of 3 tensors (K_c,) with the shift at each knot. Returns the shifts."""
        lo, step = cls._knots(x.device)
        out = torch.empty_like(x)
        for c in range(3):
            k = curve[c]
            pos = ((x[c] - lo[c]) / step[c]).clamp(0, len(k) - 1)
            i0 = pos.floor().long().clamp(max=len(k) - 2)
            f = pos - i0
            out[c] = k[i0] * (1 - f) + k[i0 + 1] * f
        return out

    @classmethod
    def _fit_curve(cls, src, dst):
        """Shift curve per channel so that src + curve(src) ~ dst on the pixels that agree. src/dst (3, P).
        Returns the curves (3 tensors) and the share of pixels used (0..1)."""
        device = src.device
        lo, step = cls._knots(device)
        keep = (src[0] > 1) & (dst[0] > 1)  # black pixels say nothing (white ones do: a white wall turning grey)
        # first pass: drift is a few Lab units, motion and new content are far more; keep what is close
        r = dst - src
        if keep.sum() < 64:
            return [torch.zeros(k, device=device) for k in cls.KNOT_COUNT], 0.0
        med = r[:, keep].median(dim=1).values.view(3, 1)
        m = keep & ((r - med).abs() <= torch.tensor([8.0, 6.0, 6.0], device=device).view(3, 1)).all(dim=0)
        curves = None
        for _ in range(2):
            if m.sum() < 64:
                return [torch.zeros(k, device=device) for k in cls.KNOT_COUNT], 0.0
            curves = []
            for c in range(3):
                s, d = src[c, m], (dst[c, m] - src[c, m])
                K = cls.KNOT_COUNT[c]
                overall = d.median()
                # least squares with the same linear blend between knots that _apply_curve uses, so fitting and
                # applying agree (a white wall sitting between two knots is matched exactly), plus a pull toward
                # the overall shift for knots with few pixels and toward neighbours to keep the curve smooth
                pos = ((s - lo[c]) / step[c]).clamp(0, K - 1)
                i0 = pos.floor().long().clamp(max=K - 2)
                f = pos - i0
                A = torch.zeros(K, K, device=device)
                rhs = torch.zeros(K, device=device)
                w0, w1 = 1 - f, f
                A.index_put_((i0, i0), w0 * w0, accumulate=True)
                A.index_put_((i0 + 1, i0 + 1), w1 * w1, accumulate=True)
                A.index_put_((i0, i0 + 1), w0 * w1, accumulate=True)
                A.index_put_((i0 + 1, i0), w0 * w1, accumulate=True)
                rhs.index_put_((i0,), w0 * d, accumulate=True)
                rhs.index_put_((i0 + 1,), w1 * d, accumulate=True)
                eye = torch.eye(K, device=device)
                A += cls.PRIOR * eye
                rhs += cls.PRIOR * overall
                D = eye[1:] - eye[:-1]  # first differences
                A += cls.SMOOTH * (D.T @ D)
                curves.append(torch.linalg.solve(A, rhs))
            # second pass: keep the pixels the curve explains
            res = dst - (src + cls._apply_curve(src, curves))
            mad = res[:, m].abs().median(dim=1).values.view(3, 1) * 1.4826
            thr = torch.maximum(3 * mad + torch.tensor([1.0, 0.6, 0.6], device=device).view(3, 1),
                                torch.tensor([3.0, 2.0, 2.0], device=device).view(3, 1))
            m = keep & (res.abs() <= thr).all(dim=0)
        return curves, m.float().mean().item()

    @staticmethod
    def _smooth(v, window):
        """Gaussian smoothing over time (dim 0) with edge padding; window is about 5 sigma wide."""
        n = v.shape[0]
        if window <= 1 or n < 2:
            return v
        sigma = window / 5.0
        r = min(int(round(2.5 * sigma)), n - 1)
        t = torch.arange(-r, r + 1, device=v.device, dtype=v.dtype)
        k = torch.exp(-0.5 * (t / sigma) ** 2)
        k = k / k.sum()
        padded = torch.cat([v[:1].expand(r, -1), v, v[-1:].expand(r, -1)], dim=0)
        return torch.nn.functional.conv1d(padded.T.unsqueeze(1), k.view(1, 1, -1)).squeeze(1).T

    def fix(self, images, strength, smooth_frames, image_ref=None):
        import kornia
        if strength == 0 or images.shape[0] < 2:
            return (images,)
        device = _device()
        small = self._small_lab(images, device)
        if not torch.isfinite(small).all():
            raise ValueError("Color Drift Fix: the video contains broken (NaN) frames, usually an all-black clip. "
                             "Change the seed or lower the motion amplitude.")
        n = small.shape[0]
        flat = small.view(n, 3, -1)
        lo, step = self._knots(device)
        knot_vals = [lo[c] + step[c] * torch.arange(self.KNOT_COUNT[c], device=device) for c in range(3)]

        # back[t][c]: shift at each knot that maps frame t's colors back to frame 1's
        zero = [torch.zeros(k, device=device) for k in self.KNOT_COUNT]
        back = [zero]
        for t in range(1, n):
            curves, share = self._fit_curve(flat[t], flat[0])
            if share < self.MIN_MATCH:
                # chain: frame t -> frame t-1 (step), then frame t-1 -> frame 1 (previous back curve)
                stepc, _ = self._fit_curve(flat[t], flat[t - 1])
                curves = []
                for c in range(3):
                    moved = knot_vals[c] + stepc[c]
                    pts = torch.stack([moved if i == c else torch.full_like(moved, 0.0) for i in range(3)])
                    curves.append(stepc[c] + self._apply_curve(pts, back[t - 1])[c])
            back.append(curves)

        # smooth each knot over time, keep frame 1 unchanged, cap
        max_shift = torch.tensor(self.MAX_SHIFT, device=device)
        sm = []
        for c in range(3):
            v = torch.stack([b[c] for b in back])  # (n, K)
            v = self._smooth(v, smooth_frames)
            v = (v - v[:1]) * strength
            sm.append(v.clamp(-max_shift[c], max_shift[c]))

        ref_curve = None
        if image_ref is not None:
            ref = image_ref[:1, ..., :3].to(device).movedim(-1, 1).float()
            ref = torch.nn.functional.interpolate(ref, size=small.shape[-2:], mode="area")
            ref_curve, _ = self._fit_curve(flat[0], kornia.color.rgb_to_lab(ref.clamp(0, 1)).view(3, -1))
            ref_curve = [k * strength for k in ref_curve]

        out = torch.empty_like(images)
        for i in range(n):
            x = images[i:i + 1].to(device).float()
            lab = kornia.color.rgb_to_lab(x[..., :3].movedim(-1, 1).clamp(0, 1))[0]
            lab = lab + self._apply_curve(lab, [sm[c][i] for c in range(3)])
            if ref_curve is not None:
                lab = lab + self._apply_curve(lab, ref_curve)
            lab[0].clamp_(0, 100)
            rgb = kornia.color.lab_to_rgb(lab[None]).clamp(0, 1).movedim(1, -1)
            if images.shape[-1] > 3:
                rgb = torch.cat([rgb, x[..., 3:]], dim=-1)
            out[i:i + 1] = rgb.to(out.device, out.dtype)
        return (out,)


class MinesKeepSourceColors:
    """An upscaler should only add detail, but RTX Video Super Resolution also shifts colors a little, and by a
    different amount on each frame (measured on a white background: 0.1 to 0.4 dE, frame to frame). Next to each
    other in a video, and especially at a loop point, that reads as a small color flicker. This node gives each
    upscaled frame back the colors of the same frame before upscaling, pixel by pixel: the two are the same
    picture, so the upscaled frame keeps only its fine detail (what a small blur removes) and takes everything
    coarser, colors included, from the source frame enlarged to the same size (detail transfer, as in StableSR's
    color fix). No fitting, so nothing can vary from frame to frame. A first version fitted a tone curve per Lab
    channel; that could not tell a white background from a grey of the same tint and left the white half corrected
    (measured 0.22 dE left, with more frame-to-frame jitter than RTX alone; detail transfer: 0.01 dE, no jitter)."""

    BLUR_PER_SCALE = 1.0  # blur sigma in upscaled pixels per unit of upscale factor (2 at 2x)

    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "images": ("IMAGE", {"tooltip": "The upscaled frames."}),
            "source": ("IMAGE", {"tooltip": "The same frames before upscaling."}),
        }}

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "keep"
    CATEGORY = "image/postprocessing"
    DESCRIPTION = ("Gives upscaled frames back the exact colors of the frames before upscaling (RTX upscaling shifts "
                   "them slightly, differently per frame). Detail from the upscaler is kept.")

    def keep(self, images, source):
        import kornia
        if images.shape[0] != source.shape[0]:
            raise ValueError(f"Keep source colors: {images.shape[0]} upscaled frames but {source.shape[0]} source frames.")
        device = _device()
        out = torch.empty_like(images)
        h, w = images.shape[1:3]
        scale = max(h / source.shape[1], w / source.shape[2])
        sigma = max(1.0, self.BLUR_PER_SCALE * scale)
        k = int(sigma * 3) * 2 + 1

        def blur(t):
            return kornia.filters.gaussian_blur2d(t, (k, k), (sigma, sigma), border_type="reflect")

        for i in range(images.shape[0]):
            x = images[i:i + 1].to(device).float()
            up = x[..., :3].movedim(-1, 1).clamp(0, 1)
            src = source[i:i + 1, ..., :3].to(device).movedim(-1, 1).float().clamp(0, 1)
            if src.shape[-2:] != up.shape[-2:]:
                src = torch.nn.functional.interpolate(src, size=up.shape[-2:], mode="bicubic", align_corners=False).clamp(0, 1)
            rgb = (up - blur(up) + blur(src)).clamp(0, 1).movedim(1, -1)
            if images.shape[-1] > 3:
                rgb = torch.cat([rgb, x[..., 3:]], dim=-1)
            out[i:i + 1] = rgb.to(out.device, out.dtype)
        return (out,)
