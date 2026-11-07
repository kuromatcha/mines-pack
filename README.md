# mine's pack

Two simple nodes for **ComfyUI Nodes 2.0**.

![prompt and save](assets/showcase.jpg)

## Install

Run inside your ComfyUI `custom_nodes` folder:

```sh
git clone https://github.com/kuromatcha/mine-pack.git
```

Restart ComfyUI and refresh the frontend. Find **prompt** and **save** under **mine's pack**.

Updating? Run `git pull` in the pack folder. Disable old `prompt_sections`, `mines_pack`, or standalone saver copies before restarting. Existing workflow IDs and browser presets remain compatible.

## prompt

Connect CLIP. Write your quality, styles and prompt in separate fields.

| Output | Text |
| --- | --- |
| main | Quality + Style + Prompt |
| selective | Quality + Selective Style + Prompt |
| selective 2 | Quality + Selective Style 2 + Prompt |

Empty sections are skipped. Quality and Prompt each have named presets with JSON import/export. Presets stay in the browser; only the Prompt field grows vertically.

## save

Connect an IMAGE output, run the workflow, then click **Save**. Saves the **first image** as PNG without rerunning generation.

- **Folder:** blank uses ComfyUI output; relative and absolute paths work.
- **Prefix:** blank gives `00001.png`; `character_` gives `character_00001.png`.
- **Digits:** minimum number width, default **5**.
- **Metadata:** include or omit the ComfyUI prompt and workflow.

Numbering continues after the highest matching PNG: `00046.png` → `00047.png`. Existing files are never overwritten. Change the folder or prefix before saving to use another destination; connected string values update when the workflow runs.

**Save** turns red → green on success. New images or changed settings reset it. Height stays fixed; width can resize. Images expire after 24 hours or a server restart—run the workflow again to refresh them. PNGs use ComfyUI's standard 8-bit conversion; its global metadata-disable setting takes priority.

## Tests

Using ComfyUI's Python:

```sh
python tests/test_png.py
```

Verified with ComfyUI **0.44.2**, frontend **1.57.6**, Python **3.13.12**, Windows.
