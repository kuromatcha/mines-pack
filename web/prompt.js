import { app } from "../../scripts/app.js";
import { mountTextPresets, PRESET_CSS, PRESET_HEIGHT, FOOTER_HEIGHT } from "./presets.js";
import { splitPromptSections } from "./prompt_split.js";

const LINE_HEIGHT = 20;
const BOX_PADDING = 6;
// Fixed-height fields; the positive prompt ("prompt") is left free to absorb extra height.
const FIELDS = {
  quality: { label: "quality", lines: 1 },
  style_1: { label: "style 1", lines: 1 },
  style_2: { label: "style 2", lines: 1 },
  style_3: { label: "style 3", lines: 1 },
  negative_prompt: { label: "negative prompt", lines: 2 },
};
const PROMPT_LABEL = "positive prompt";
const OUTPUT_LABELS = ["style 1", "style 2", "style 3", "negative"];

// The Vue renderer creates its own textareas instead of using widget.element.
// Its grid uses an auto row for every textarea, which otherwise shares growth.
// Children: 1-4 one-line fields, 5 positive prompt (grows), 6 negative prompt
// (two lines), 7-8 preset rows, 9 import/export footer.
const COMPACT = 48;
const NEGATIVE = 64;
const SEL = `.lg-node-widgets:has([node-type="PromptSectionsCond"])`;
const CHILD = `${SEL} > :is(.lg-node-widget, div:has(> .lg-node-widget))`;
const VUE_LAYOUT = `
${SEL} {
  grid-template-columns: min-content minmax(0,0fr) minmax(80px,1fr) !important;
  grid-template-rows: repeat(4,${COMPACT}px) minmax(80px,1fr) ${NEGATIVE}px ${PRESET_HEIGHT}px ${PRESET_HEIGHT}px ${FOOTER_HEIGHT}px !important;
  flex: 1 1 0% !important;
  min-height: ${4 * COMPACT + 80 + NEGATIVE + 2 * PRESET_HEIGHT + FOOTER_HEIGHT + 8 * 4}px;
}
${CHILD} { min-height: 0; grid-column: 1 / -1 !important; }
${CHILD}:nth-child(-n+6) [node-type="PromptSectionsCond"] { grid-column:2/-1 !important; min-width:0; }
${[1, 2, 3, 4, 5, 6, 7, 8, 9].map(row => `${CHILD}:nth-child(${row}) { grid-row:${row}; }`).join("\n")}
${CHILD}:nth-child(-n+4) { height:${COMPACT}px; max-height:${COMPACT}px; }
${CHILD}:nth-child(-n+4) textarea {
  height:${COMPACT}px !important; min-height:${COMPACT}px !important; max-height:${COMPACT}px !important;
  box-sizing:border-box; padding-top:20px; padding-bottom:8px; line-height:16px;
  white-space:pre; overflow:hidden !important; resize:none;
}
${CHILD}:nth-child(5) { min-height:80px; }
${CHILD}:nth-child(5) textarea {
  height:100% !important; min-height:80px !important; max-height:none !important;
  box-sizing:border-box; resize:none;
}
${CHILD}:nth-child(6) { height:${NEGATIVE}px; max-height:${NEGATIVE}px; }
${CHILD}:nth-child(6) textarea {
  height:${NEGATIVE}px !important; min-height:${NEGATIVE}px !important; max-height:${NEGATIVE}px !important;
  box-sizing:border-box; padding-top:20px; padding-bottom:12px; line-height:16px;
  white-space:pre-wrap; overflow-x:hidden !important; overflow-y:auto !important; resize:none;
}
${CHILD}:nth-child(7), ${CHILD}:nth-child(8) {
  grid-column:2/-1 !important; display:block; align-self:start;
  height:${PRESET_HEIGHT}px !important; min-height:${PRESET_HEIGHT}px !important; max-height:${PRESET_HEIGHT}px !important;
}
${CHILD}:nth-child(9) {
  grid-column:2/-1 !important; display:block;
  height:${FOOTER_HEIGHT}px !important; min-height:${FOOTER_HEIGHT}px !important; max-height:${FOOTER_HEIGHT}px !important;
}
`;

/** Restore pre-v9 positional values by name, not by the new visual order. */
function restoreLegacySectionValues(node, saved) {
  const values = saved?.widgets_values;
  if (Array.isArray(values) && saved?.properties?.promptSectionsOrder !== 2) {
    const legacyNames = values.length >= 5
      ? ["quality", "style_1", "style_2", "prompt", "style_3"]
      : ["quality", "style_1", "style_2", "prompt"];
    for (const [index, name] of legacyNames.entries()) {
      const widget = node.widgets?.find(item => item.name === name);
      if (widget && typeof values[index] === "string") widget.value = values[index];
    }
    for (const name of values.length === 4 ? ["style_3", "negative_prompt"] : ["negative_prompt"]) {
      const widget = node.widgets?.find(item => item.name === name);
      if (widget) widget.value = "";
    }
  }
  node.properties = { ...node.properties, promptSectionsOrder: 2 };
}

function lockCompactFields(node) {
  // Restored workflows may have fewer outputs. Append, never reorder or
  // replace existing ports, so their links stay attached.
  while (node.outputs && node.outputs.length < OUTPUT_LABELS.length && typeof node.addOutput === "function") {
    node.addOutput(OUTPUT_LABELS[node.outputs.length], "CONDITIONING");
  }
  for (const [index, label] of OUTPUT_LABELS.entries()) {
    if (!node.outputs?.[index]) continue;
    node.outputs[index].name = label;
    node.outputs[index].label = label;
  }
  for (const widget of node.widgets || []) {
    if (widget.type === "hidden" || widget.hidden) continue;
    if (widget.name === "prompt") {
      // Leave its height alone so its native layout absorbs extra height.
      widget.label = PROMPT_LABEL;
      const textarea = findTextarea(widget);
      if (textarea) textarea.placeholder = PROMPT_LABEL;
      continue;
    }
    const field = FIELDS[widget.name];
    if (!field) continue;
    widget.label = field.label;
    widget.options = widget.options || {};
    const boxHeight = field.lines * LINE_HEIGHT + 2 * BOX_PADDING;
    // Reserve the renderer's top/bottom margins outside the visible lines.
    const margin = widget.margin ?? widget.options.margin ?? 10;
    const layoutHeight = boxHeight + margin * 2;
    widget.options.getMinHeight = () => layoutHeight;
    widget.options.getMaxHeight = () => layoutHeight;
    widget.options.getHeight = () => layoutHeight;

    const textarea = findTextarea(widget);
    if (!textarea) continue;
    const multiLine = field.lines > 1;
    textarea.placeholder = field.label;
    textarea.rows = field.lines;
    textarea.wrap = multiLine ? "soft" : "off";
    Object.assign(textarea.style, {
      resize: "none",
      boxSizing: "border-box",
      lineHeight: `${LINE_HEIGHT}px`,
      padding: `${BOX_PADDING}px 8px`,
      whiteSpace: multiLine ? "pre-wrap" : "pre",
      overflowX: "hidden",
      overflowY: multiLine ? "auto" : "hidden",
      flexGrow: "0",
      flexShrink: "0",
    });
    // Lock visible height even when a renderer assigns inline height.
    for (const property of ["height", "min-height", "max-height"]) {
      textarea.style.setProperty(property, `${boxHeight}px`, "important");
    }
  }
  for (const input of node.inputs || []) {
    const label = input.name === "prompt" ? PROMPT_LABEL : FIELDS[input.name]?.label;
    if (label) input.label = label;
  }
}

function findTextarea(widget) {
  const element = widget.element || widget.inputEl;
  return element?.tagName === "TEXTAREA" ? element : element?.querySelector?.("textarea");
}

app.registerExtension({
  name: "PromptSections.Sizing",
  setup() {
    const style = document.createElement("style");
    style.id = "prompt-sections-layout";
    style.textContent = VUE_LAYOUT + PRESET_CSS;
    document.head.appendChild(style);

    // Queue each output as its own text encode so editing one section only
    // re-runs the samplers that use it (see README).
    const graphToPrompt = app.graphToPrompt;
    app.graphToPrompt = async function (...args) {
      const result = await graphToPrompt.apply(this, args);
      try {
        if (result?.output) splitPromptSections(result.output);
      } catch (error) {
        console.warn("[mine's pack] prompt node left unsplit:", error);
      }
      return result;
    };
  },
  nodeCreated(node) {
    if (node.comfyClass !== "PromptSectionsCond") return;
    node.properties = { ...node.properties, promptSectionsOrder: 2 };
    lockCompactFields(node);
    const presets = mountTextPresets(node, () => node.graph?.change?.());
    const fitControls = () => {
      const minimum = node.computeSize();
      node.setSize([node.size[0], Math.max(node.size[1], minimum[1])]);
    };
    for (const hook of ["onResize", "onConfigure", "onConnectionsChange"]) {
      const previous = node[hook];
      node[hook] = function (...args) {
        const result = previous?.apply(this, args);
        if (hook === "onConfigure") restoreLegacySectionValues(this, args[0]);
        lockCompactFields(this);
        presets.refresh();
        if (hook === "onConfigure") fitControls();
        return result;
      };
    }
    fitControls();
  },
});
