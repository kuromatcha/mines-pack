# mines-pack

Shows as **mine's pack** in ComfyUI.

![prompt and save](assets/showcase.jpg)

- **prompt** — quality, style 1–3, a positive prompt and a two-line negative prompt, with presets. Outputs **style 1**, **style 2** and **style 3** (quality + that style + positive prompt) and **negative**.
- **save** — save the first image as a numbered PNG, with optional metadata. Click **Save** in the top bar to save the latest run.

For the [Mine's video workflows](https://github.com/kuromatcha/mines-img2vid):

- **load image (optional)** — Load Image with a "none" choice that outputs nothing, for optional end images.
- **SVIPro end frame** — KJNodes' Wan Image To Video SVIPro with an optional end image on the last frame.
- **H3 frame guides** — pins an optional first frame and an optional last frame onto MiniMax H3 conditioning (ComfyUI's Add Guide for MiniMax H3), so a Reference to Video clip can also start and end on given pictures. A frame set to *none* is skipped.
- **color drift fix** — removes slow color drift (brightness, warmth, saturation, skin tone) so later frames keep the tone of the first frame; in a loop the end matches the start. Motion and short flashes are left alone.
- **keep source colors** — gives upscaled frames back the exact colors of the frames before upscaling (RTX upscaling shifts them slightly, differently per frame). Keeps the upscaler's fine detail and takes the colors pixel by pixel from the source frame.

For [mines-ghost](https://github.com/kuromatcha/mines-ghost) video cutouts:

- **background removal resolution** — sets the working size of ComfyUI's built-in background removal model, which always uses 1024. BiRefNet-HR is trained at 2048 and keeps thin hair much steadier there.
- **mask temporal smooth** — steadies a per-frame mask (Remove Background run frame by frame) so its edges stop flickering. Neighbouring frames are lined up by their motion first (optical flow), so swaying and moving parts are smoothed without ghosting. Turn **loop** on for looping clips.

On Windows the pack also hides the harmless *WinError 10054* traceback ComfyUI logs when a browser tab closes.

Clone into ComfyUI's `custom_nodes` folder, then restart ComfyUI:

```sh
git clone https://github.com/kuromatcha/mines-pack.git
```

Each output is encoded separately when you queue, so editing one style only re-runs the samplers that use it. This doesn't apply if a text box is fed by a link.
