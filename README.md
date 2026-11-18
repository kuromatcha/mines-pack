# mines-pack

A small ComfyUI node pack: a sectioned prompt node with presets, a save-on-click image saver, inpaint crop and stitch, and the video helpers used by the [mines-I2V](https://github.com/kuromatcha/mines-I2V) workflows. Shows as **mine's pack** in the node menu.

![prompt and save on click nodes](assets/showcase.jpg)

## Nodes

| Node | Group | What it does |
|---|---|---|
| **prompt** | prompt | Quality, three styles, a positive and a negative prompt in one node, with presets. One output per style, plus the negative. |
| **pick style** | prompt | Passes on style 1, 2 or 3 by number. The styles not picked are never encoded. |
| **save on click** | image | Nothing is written to disk until you press **Save** in the top bar. Saves numbered PNGs (`00001.png`, …). |
| **inpaint crop** | inpaint | Cuts the masked area out with its surroundings and scales it to the model's working size. |
| **inpaint stitch** | inpaint | Blends the redrawn cut back into the original picture with a soft edge. |
| **SVIPro end frame** | video | KJNodes' Wan Image To Video SVIPro with an optional end image. |
| **H3 frame guides** | video | Pins an optional first and last frame onto MiniMax H3 conditioning. |
| **color drift fix** | video | Removes slow color drift, so later frames keep the tone of the first frame. |
| **keep source colors** | video | Gives upscaled frames back the colors they had before upscaling. |

On Windows the pack also hides the harmless *WinError 10054* traceback that ComfyUI logs when a browser tab closes.

## Install

```sh
cd ComfyUI/custom_nodes
git clone https://github.com/kuromatcha/mines-pack.git
```

Restart ComfyUI. No extra Python packages are needed. Full steps, updating and checks: [docs/setup.md](docs/setup.md).

## Docs

- [Setup](docs/setup.md): requirements, install, update, check that it works, remove
- [Nodes](docs/nodes.md): every input and output, presets, how saving works, the measurements behind the color nodes
