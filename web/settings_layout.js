import { app } from "../../scripts/app.js";

// Settings (subgraph) nodes: multiline text fields with the prompt node's names keep its layout. Quality and the
// styles take one line, the negative prompt two, and the other multiline fields get the remaining height instead
// of sharing it equally.
const ONE_LINE = 48;
const TWO_LINES = 64;
const HEIGHTS = { quality: ONE_LINE, style: ONE_LINE, style_1: ONE_LINE, style_2: ONE_LINE, style_3: ONE_LINE, negative_prompt: TWO_LINES };
const styles = new Map(); // subgraph id -> <style>

function fixTextHeights(node) {
  if (!node.subgraph) return;
  const widgets = (node.widgets || []).filter(widget => widget.type !== "hidden" && !widget.hidden);
  const heightOf = widget => (widget.type === "customtext" ? HEIGHTS[widget.name] : undefined);
  if (!widgets.some(heightOf)) return;

  // Vue renderer: one grid row per widget, in widget order.
  const SEL = `.lg-node-widgets:has([node-type="${node.type}"])`;
  const rows = [];
  let css = "";
  for (const [index, widget] of widgets.entries()) {
    const height = heightOf(widget);
    rows.push(height ? `${height}px` : widget.type === "customtext" ? "minmax(80px,1fr)" : "min-content");
    if (!height) continue;

    // Legacy renderer.
    widget.options = widget.options || {};
    for (const key of ["getMinHeight", "getMaxHeight", "getHeight"]) widget.options[key] = () => height;

    const CHILD = `${SEL} > :nth-child(${index + 1})`;
    const oneLine = height === ONE_LINE;
    css += `
${CHILD} { height:${height}px; min-height:0; max-height:${height}px; }
${CHILD} textarea {
  height:${height}px !important; min-height:${height}px !important; max-height:${height}px !important;
  box-sizing:border-box; padding-top:20px; padding-bottom:${oneLine ? 8 : 12}px; line-height:16px; resize:none;
  white-space:${oneLine ? "pre" : "pre-wrap"}; overflow-x:hidden !important;
  overflow-y:${oneLine ? "hidden" : "auto"} !important;
}`;
  }
  let style = styles.get(node.type);
  if (!style) {
    style = document.createElement("style");
    document.head.appendChild(style);
    styles.set(node.type, style);
  }
  style.textContent = `${SEL} { grid-template-rows: ${rows.join(" ")} !important; }${css}\n`;
}

app.registerExtension({
  name: "MinesPack.SettingsLayout",
  nodeCreated(node) {
    // A subgraph node gets its widgets after creation.
    queueMicrotask(() => fixTextHeights(node));
  },
  loadedGraphNode(node) {
    fixTextHeights(node);
  },
});
