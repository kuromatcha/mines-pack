# mines-pack

Shows as **mine's pack** in ComfyUI.

![prompt and save](assets/showcase.jpg)

- **prompt** — quality, style 1–3, a positive prompt and a two-line negative prompt, with presets. Outputs **style 1**, **style 2** and **style 3** (quality + that style + positive prompt) and **negative**.
- **pick style** — passes on style 1, 2 or 3 of the prompt node by number; the styles not picked are not encoded. The number only goes up to the highest connected style.
- **save on click** — adds a **Save** button to the top bar: a run is only kept until you click it, then the picked image is saved as a numbered PNG (00001.png…), with optional metadata.

For the [Mine's video workflows](https://github.com/kuromatcha/mines-img2vid):

- **SVIPro end frame** — KJNodes' Wan Image To Video SVIPro with an optional end image on the last frame.
- **H3 frame guides** — pins an optional first frame and an optional last frame onto MiniMax H3 conditioning (ComfyUI's Add Guide for MiniMax H3), so a Reference to Video clip can also start and end on given pictures. A frame whose Load Image is bypassed (Ctrl+B) is skipped.
- **color drift fix** — removes slow color drift (brightness, warmth, saturation, skin tone) so later frames keep the tone of the first frame; in a loop the end matches the start. Motion and short flashes are left alone.
- **keep source colors** — gives upscaled frames back the exact colors of the frames before upscaling (RTX upscaling shifts them slightly, differently per frame). Keeps the upscaler's fine detail and takes the colors pixel by pixel from the source frame.

For the Mine's Anima Inpaint workflow:

- **inpaint crop** — cuts the masked area out with its surroundings and scales it to the model's working size, so a small area is redrawn at full detail.
- **inpaint stitch** — scales the redrawn cut back and blends it into the original picture with a soft edge. Pixels outside the blend are unchanged.
- On a subgraph's settings node, the prompt node's fields keep its layout when promoted: `quality`, `style` and `style_1`–`style_3` one line, `negative_prompt` two lines.

On Windows the pack also hides the harmless *WinError 10054* traceback ComfyUI logs when a browser tab closes.

Clone into ComfyUI's `custom_nodes` folder, then restart ComfyUI:

```sh
git clone https://github.com/kuromatcha/mines-pack.git
```

Each output is encoded separately when you queue, so editing one style only re-runs the samplers that use it. This doesn't apply if a text box is fed by a link.
