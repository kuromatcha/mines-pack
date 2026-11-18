# Setup

## Requirements

- **ComfyUI 0.45.3 or newer.** Tested on 0.45.4 (Comfy Desktop, Python 3.13, PyTorch 2.12.1).
  Only **H3 frame guides** needs a version that recent: it uses ComfyUI's built-in MiniMax H3 nodes. The other nodes are not tied to a version.
- No extra Python packages. The pack uses `torch`, `kornia`, `Pillow`, `numpy` and `aiohttp`, which all come with ComfyUI.
- No other node pack. **SVIPro end frame** carries its own copy of the KJNodes logic, so KJNodes is not needed for it.

## Install

1. Open a terminal in `ComfyUI/custom_nodes/`.
2. Clone the pack:
   ```sh
   git clone https://github.com/kuromatcha/mines-pack.git
   ```
3. Restart ComfyUI.

The pack is not listed in ComfyUI-Manager. In Manager you can still use **Install via Git URL** with the address above.

## Check that it works

1. Double-click the canvas and search for `mine's pack`, or open the node menu: the nine nodes are under **mine's pack → prompt / image / inpaint / video**.
2. A **Save** button appears in the top bar. It is dimmed until a workflow with a **save on click** node has run.

## Update

```sh
cd ComfyUI/custom_nodes/mines-pack
git pull
```

Restart ComfyUI, and reload the browser tab so the new front-end files are loaded.

## Run the tests (optional)

The tests need only ComfyUI's Python, not a running ComfyUI. From the pack's folder:

```sh
python tests/test_color.py
python tests/test_inpaint.py
python tests/test_png.py
python tests/test_prompt.py
python tests/test_video.py
```

Use the Python that ComfyUI runs on (for Comfy Desktop: `ComfyUI/.venv/Scripts/python.exe`).

## Remove

Delete the `mines-pack` folder from `ComfyUI/custom_nodes/` and restart ComfyUI. Prompt presets are stored in the browser (see [Nodes](nodes.md#presets)), so export them first if you want to keep them.
