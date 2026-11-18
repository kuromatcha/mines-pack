# Nodes

All nodes are under **mine's pack** in the node menu.

- [prompt](#prompt) · [pick style](#pick-style) · [save on click](#save-on-click)
- [inpaint crop](#inpaint-crop) · [inpaint stitch](#inpaint-stitch)
- [SVIPro end frame](#svipro-end-frame) · [H3 frame guides](#h3-frame-guides) · [color drift fix](#color-drift-fix) · [keep source colors](#keep-source-colors)
- [Extras](#extras)

## prompt

One node for the whole prompt, split into fields.

| Input | Notes |
|---|---|
| `clip` | The text encoder. |
| `quality` | Shared by all three styles. One line. |
| `style 1`, `style 2`, `style 3` | One line each. Style 3 is optional. |
| `positive prompt` | Shared by all three styles. Takes the remaining height of the node. |
| `negative prompt` | Two lines. |

| Output | Text that is encoded |
|---|---|
| `style 1` | quality, style 1, positive prompt |
| `style 2` | quality, style 2, positive prompt |
| `style 3` | quality, style 3, positive prompt |
| `negative` | negative prompt |

Empty fields and trailing commas are dropped, so there are no doubled commas.

**Only what changed runs again.** When you queue, each used output is sent as its own text encode. Editing style 2 therefore re-runs only the samplers fed by style 2, and outputs that are not connected are not encoded at all. The saved workflow is unchanged. This does not apply when one of the text fields is fed by a link: the text is then only known at run time.

### Presets

The **Quality preset** and **Positive prompt preset** rows save, load, rename and delete texts for those two fields.

- Presets are stored in the browser (local storage), not in the workflow and not on disk. Another browser or a cleared browser profile does not have them.
- **Export** writes all presets to a JSON file. **Import** reads such a file; it is checked completely before anything is changed.
- Limits: 1000 presets, names up to 100 characters.

## pick style

Passes on one of the prompt node's styles.

| Input | Notes |
|---|---|
| `style` | 1, 2 or 3. The number only goes up to the highest connected style. |
| `style_1`, `style_2`, `style_3` | Connect the prompt node's style outputs. |

The styles that are not picked are not encoded. Picking a style that is not connected gives an error.

## save on click

Keeps the result of a run in a temporary folder and saves it only when you ask.

| Input | Notes |
|---|---|
| `images` | The first image of the batch is the one that is saved. |
| `Folder` | Empty: ComfyUI's output folder. Also accepts a subfolder of it, or a full path. |
| `Prefix` | Empty gives `00001.png`. `character_` gives `character_00001.png`. No path separators. |
| `Digits` | Number padding, 1 to 12. Default 5. |
| `Metadata` | On: the workflow is stored in the PNG, as ComfyUI's own save node does. |

- Press **Save** in the top bar (also available as the command *Save latest image (mine's pack)*). The button is red while the latest image is unsaved and green once it is saved. Changing a setting after saving turns it back to unsaved.
- The number is the highest existing number in the folder plus one. Existing files are never overwritten.
- Saving does not re-run the workflow.
- Unsaved images are kept for 24 hours in ComfyUI's temp folder, and only the latest run of each node is kept.
- If ComfyUI was started with `--disable-metadata`, images are saved without metadata.

## inpaint crop

Cuts the masked area out with some of its surroundings and scales the cut to the model's working size, so a small area is redrawn at full detail.

| Input | Default | Notes |
|---|---|---|
| `image`, `mask` | | White in the mask is the area to redraw. |
| `megapixels` | 1.0 | Working size of the cut. |
| `context` | 2.0 | Size of the cut as a multiple of the masked area. Higher: the model sees more of the picture and matches it better. Lower: more detail. |
| `grow` | 8 | Widens the mask by this many pixels. |
| `blend` | 16 | Width in pixels of the soft edge when the cut is put back. |

Outputs: `image` (the cut), `mask` (the cut's mask) and `stitch` (for inpaint stitch).

The cut is at least 256 px on each side, at most 2:1 in shape, and its size is a multiple of 16. An empty mask gives an error.

## inpaint stitch

Scales the redrawn cut back and blends it into the original picture.

| Input | Notes |
|---|---|
| `stitch` | From inpaint crop. |
| `image` | The redrawn cut. |

Pixels outside the blend are exactly the original pixels.

## SVIPro end frame

KJNodes' *Wan Image To Video SVIPro* with one extra input.

| Input | Notes |
|---|---|
| `positive`, `negative`, `vae`, `length`, `anchor_samples`, `motion_latent_count`, `prev_samples` | As in the KJNodes node. |
| `end_image` | Optional. Placed on the last frame, the same way ComfyUI's Wan First-Last-Frame node does it. |

Without an end image the result is the same as the KJNodes node. Used by the Long workflow in [mines-I2V](https://github.com/kuromatcha/mines-I2V).

## H3 frame guides

Pins a first frame, a last frame, or both onto MiniMax H3 conditioning, using ComfyUI's own *Add Guide for MiniMax H3*. It works on Reference to Video conditioning, so references and fixed frames can be used in one clip.

| Input | Notes |
|---|---|
| `positive`, `vae`, `latent` | |
| `first_frame` | Optional. Pinned at frame 0. |
| `last_frame` | Optional. Pinned at the last frame. |

A frame that is not connected, or whose Load Image node is bypassed (Ctrl+B), is skipped. Used by the Hybrid workflow in mines-I2V.

## color drift fix

Video models slowly drift in brightness, warmth, saturation and skin tone over a clip. This node removes that slow change and leaves motion and short flashes alone.

| Input | Default | Notes |
|---|---|---|
| `images` | | The video frames. |
| `strength` | 1.0 | 1 removes the measured drift, 0 leaves the video unchanged. Above 1 overcorrects. |
| `smooth_frames` | 16 | Changes shorter than about this many frames (flashes) are kept. Slower drift is removed. |
| `image_ref` | | Optional. Also matches the first frame to this image, e.g. the start image. |

How it works: every frame is compared with the first frame on the pixels that still match it (background, parts that did not move). From those pixels it fits a tone curve per color channel, smooths the curves over time and maps each frame back. The first frame is unchanged. In a loop the last frames return to the first pose, so the end gets the tone of the start and the loop point does not jump.

Measured on a loop test: background drift before the loop point 1.32 → 0.16 ΔE.

If the video contains broken (NaN) frames, the node stops with an error that says so. That is a sampling problem, not a color problem.

## keep source colors

RTX Video Super Resolution shifts colors slightly, and by a different amount on each frame. In a video that shows as a small flicker, most of all at a loop point.

| Input | Notes |
|---|---|
| `images` | The upscaled frames. |
| `source` | The same frames before upscaling. The frame counts must match. |

The upscaled frame keeps its fine detail and takes everything coarser, colors included, from the source frame. Nothing is fitted, so nothing can vary from frame to frame.

Measured on an 81-frame clip: color error 0.19 → 0.05 ΔE, white background 0.08 → 0.00 ΔE, fine detail kept (−1%).

## Extras

- **Subgraph settings layout.** When the prompt node's fields are promoted to a subgraph's settings node, they keep their layout: `quality`, `style` and `style_1`–`style_3` take one line, `negative_prompt` two, and other text fields share the rest.
- **WinError 10054.** On Windows, ComfyUI logs a *ConnectionResetError [WinError 10054]* traceback when a browser tab closes or reloads. It is harmless. The pack hides that one traceback; every other error is still shown.
