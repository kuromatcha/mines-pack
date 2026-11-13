# mine's pack

![prompt and save](assets/showcase.jpg)

- **prompt** — quality, style 1–3, a positive prompt and a two-line negative prompt, with presets. Outputs **style 1**, **style 2** and **style 3** (quality + that style + positive prompt) and **negative**.
- **save** — save the first image as a numbered PNG, with optional metadata. Click **Save** in the top bar to save the latest run.

Clone into ComfyUI's `custom_nodes` folder, then restart ComfyUI:

```sh
git clone https://github.com/kuromatcha/mine-pack.git
```

Each output is encoded separately when you queue, so editing one style only re-runs the samplers that use it. This doesn't apply if a text box is fed by a link.
