import { app } from "../../scripts/app.js";
import { mountTextPresets, PRESET_CSS, PRESET_HEIGHT, FOOTER_HEIGHT } from "./presets.js";

const BOX_HEIGHT = 36;
const LABELS = { quality: "quality", style_1: "style", style_2: "selective style", style_3: "selective style 2" };

// The Vue renderer creates its own textareas instead of using widget.element.
// Its grid uses an auto row for every textarea, which otherwise shares growth.
const VUE_LAYOUT = `
.lg-node-widgets:has([node-type="PromptSectionsCond"]) {
  grid-template-columns: min-content minmax(0,0fr) minmax(80px,1fr) !important;
  grid-template-rows: repeat(4,48px) minmax(80px,1fr) ${PRESET_HEIGHT}px ${PRESET_HEIGHT}px ${FOOTER_HEIGHT}px !important;
  flex: 1 1 0% !important;
  min-height: ${4 * 48 + 80 + 2 * PRESET_HEIGHT + FOOTER_HEIGHT + 7 * 4}px;
}
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)) {
  min-height: 0;
  grid-column: 1 / -1 !important;
}
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(-n+5) [node-type="PromptSectionsCond"] {
  grid-column:2/-1 !important;
  min-width:0;
}
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(1) { grid-row:1; }
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(2) { grid-row:2; }
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(3) { grid-row:3; }
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(4) { grid-row:4; }
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(5) { grid-row:5; }
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(-n+4) {
  height: 48px;
  max-height: 48px;
}
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(-n+4) textarea {
  height: 48px !important;
  min-height: 48px !important;
  max-height: 48px !important;
  box-sizing: border-box;
  padding-top: 20px;
  padding-bottom: 8px;
  line-height: 16px;
  white-space: pre;
  overflow: hidden !important;
  resize: none;
}
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(5) {
  min-height: 80px;
}
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(5) textarea {
  height: 100% !important;
  min-height: 80px !important;
  max-height: none !important;
  box-sizing: border-box;
  resize: none;
}
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(6),
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(7) {
  grid-column:2/-1 !important;
  display:block;
  align-self:start;
  height:${PRESET_HEIGHT}px !important;
  min-height:${PRESET_HEIGHT}px !important;
  max-height:${PRESET_HEIGHT}px !important;
}
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(6) { grid-row:6; }
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(7) { grid-row:7; }
.lg-node-widgets:has([node-type="PromptSectionsCond"]) > :is(.lg-node-widget, div:has(> .lg-node-widget)):nth-child(8) {
  grid-column:2/-1 !important;
  grid-row:8;
  display:block;
  height:${FOOTER_HEIGHT}px !important;
  min-height:${FOOTER_HEIGHT}px !important;
  max-height:${FOOTER_HEIGHT}px !important;
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
    if (values.length === 4) {
      const addedStyle = node.widgets?.find(widget => widget.name === "style_3");
      if (addedStyle) addedStyle.value = "";
    }
  }
  node.properties = { ...node.properties, promptSectionsOrder: 2 };
}

function lockCompactFields(node) {
  // Restored workflows may have only the original two outputs. Append, never
  // reorder or replace those ports, so their existing links stay attached.
  if (node.outputs?.length === 2 && typeof node.addOutput === "function") {
    node.addOutput("selective 2", "CONDITIONING");
  }
  for (const [index, label] of ["main", "selective", "selective 2"].entries()) {
    if (!node.outputs?.[index]) continue;
    node.outputs[index].name = label;
    node.outputs[index].label = label;
  }
  for (const widget of node.widgets || []) {
    const label = LABELS[widget.name];
    if (!label || widget.type === "hidden" || widget.hidden) continue;
    widget.label = label;
    widget.options = widget.options || {};
    // Reserve the renderer's top/bottom margins outside the visible line.
    const margin = widget.margin ?? widget.options.margin ?? 10;
    const layoutHeight = BOX_HEIGHT + margin * 2;
    widget.options.getMinHeight = () => layoutHeight;
    widget.options.getMaxHeight = () => layoutHeight;
    widget.options.getHeight = () => layoutHeight;

    const element = widget.element || widget.inputEl;
    const textarea = element?.tagName === "TEXTAREA"
      ? element
      : element?.querySelector?.("textarea");
    if (!textarea) continue;
    textarea.placeholder = label;
    textarea.rows = 1;
    textarea.wrap = "off";
    Object.assign(textarea.style, {
      resize: "none",
      boxSizing: "border-box",
      lineHeight: "20px",
      padding: "6px 8px",
      whiteSpace: "pre",
      overflowX: "hidden",
      overflowY: "hidden",
      flexGrow: "0",
      flexShrink: "0",
    });
    // Lock visible height even when a renderer assigns inline height.
    for (const property of ["height", "min-height", "max-height"]) {
      textarea.style.setProperty(property, `${BOX_HEIGHT}px`, "important");
    }
  }
  for (const input of node.inputs || []) {
    if (LABELS[input.name]) input.label = LABELS[input.name];
  }
  // Leave Prompt untouched so its native layout absorbs extra height.
}

app.registerExtension({
  name: "PromptSections.Sizing",
  setup() {
    const style = document.createElement("style");
    style.id = "prompt-sections-layout";
    style.textContent = VUE_LAYOUT + PRESET_CSS;
    document.head.appendChild(style);
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
