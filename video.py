"""Image-to-video helpers for the Mine's video workflows (github.com/kuromatcha/mines-img2vid).

- load image (optional): like Load Image, plus a "none" choice that outputs nothing, so a node that takes an
  optional image (Wan First-Last-Frame to Video, SVIPro end frame) simply skips it.
- SVIPro end frame: KJNodes' Wan Image To Video SVIPro, plus an optional end image that is placed on the last
  frame the same way the core Wan First-Last-Frame to Video node does it.
"""
import torch

import comfy.latent_formats
import comfy.model_management
import comfy.utils
import node_helpers
import nodes

NONE = "none"


class MinesLoadImageOptional(nodes.LoadImage):
    @classmethod
    def INPUT_TYPES(s):
        files = nodes.LoadImage.INPUT_TYPES()["required"]["image"][0]
        return {"required": {"image": ([NONE] + files, {"image_upload": True, "default": NONE})}}

    CATEGORY = "image"
    DESCRIPTION = 'Load Image with a "none" choice. At "none" it outputs nothing and the image is skipped.'

    def load_image(self, image):
        if image == NONE:
            return (None, None)
        return super().load_image(image)

    @classmethod
    def IS_CHANGED(s, image):
        return NONE if image == NONE else nodes.LoadImage.IS_CHANGED(image)

    @classmethod
    def VALIDATE_INPUTS(s, image):
        return True if image == NONE else nodes.LoadImage.VALIDATE_INPUTS(image)


class MinesSVIProEndFrame:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                    "positive": ("CONDITIONING",),
                    "negative": ("CONDITIONING",),
                    "vae": ("VAE",),
                    "length": ("INT", {"default": 81, "min": 1, "max": nodes.MAX_RESOLUTION, "step": 4}),
                    "anchor_samples": ("LATENT",),
                    "motion_latent_count": ("INT", {"default": 1, "min": 0, "max": 128, "step": 1}),
                },
                "optional": {
                    "prev_samples": ("LATENT",),
                    "end_image": ("IMAGE",),
                }}

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT")
    RETURN_NAMES = ("positive", "negative", "latent")
    FUNCTION = "build"
    CATEGORY = "conditioning/video_models"
    DESCRIPTION = ("Wan Image To Video SVIPro (KJNodes) with an optional end image on the last frame. "
                   "Without an end image it is the same as Wan Image To Video SVIPro.")

    def build(self, positive, negative, vae, length, anchor_samples, motion_latent_count, prev_samples=None, end_image=None):
        # --- same as KJNodes WanImageToVideoSVIPro ---
        anchor_latent = anchor_samples["samples"].clone()
        B, C, T, H, W = anchor_latent.shape
        empty_latent = torch.zeros([B, 16, ((length - 1) // 4) + 1, H, W], device=comfy.model_management.intermediate_device())
        total_latents = (length - 1) // 4 + 1
        device, dtype = anchor_latent.device, anchor_latent.dtype
        if prev_samples is None or motion_latent_count == 0:
            padding_size = total_latents - anchor_latent.shape[2]
            image_cond_latent = anchor_latent
        else:
            motion_latent = prev_samples["samples"][:, :, -motion_latent_count:].clone()
            padding_size = total_latents - anchor_latent.shape[2] - motion_latent.shape[2]
            image_cond_latent = torch.cat([anchor_latent, motion_latent], dim=2)
        padding = torch.zeros(1, C, padding_size, H, W, dtype=dtype, device=device)
        padding = comfy.latent_formats.Wan21().process_out(padding)
        image_cond_latent = torch.cat([image_cond_latent, padding], dim=2)
        mask = torch.ones((1, 1, empty_latent.shape[2], H, W), device=device, dtype=dtype)
        mask[:, :, :1] = 0.0

        # --- end frame: only the last pixel frame is marked known, as in core WanFirstLastFrameToVideo. The 3 frames
        # before it are filled with the end image too, not grey: with the SVI LoRA, grey there was copied into the
        # video (grey noisy flash on the last frames, measured). ---
        if end_image is not None and padding_size >= 1:
            s = vae.spacial_compression_encode()
            img = comfy.utils.common_upscale(end_image[-1:].movedim(-1, 1), W * s, H * s, "bilinear", "center").movedim(1, -1)
            end_latent = vae.encode(img[..., :3].repeat(5, 1, 1, 1))[:, :, -1:]
            image_cond_latent[:, :, -1:] = end_latent.to(device=device, dtype=dtype)
            mask = mask.repeat(1, 4, 1, 1, 1)
            mask[:, 3, -1] = 0.0

        positive = node_helpers.conditioning_set_values(positive, {"concat_latent_image": image_cond_latent, "concat_mask": mask})
        negative = node_helpers.conditioning_set_values(negative, {"concat_latent_image": image_cond_latent, "concat_mask": mask})
        return (positive, negative, {"samples": empty_latent})
