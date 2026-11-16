import { app } from "../../scripts/app.js";

// pick style: the number only goes up to the highest connected style, so a workflow that wires two styles offers 1-2.
function capStyle(node) {
  const widget = node.widgets?.find(item => item.name === "style");
  if (!widget) return;
  const connected = (node.inputs || []).filter(input => input.link != null && /^style_\d$/.test(input.name));
  const max = connected.length ? Math.max(...connected.map(input => Number(input.name.slice(6)))) : 3;
  widget.options = { ...widget.options, max };
  if (widget.value > max) widget.value = max;
}

app.registerExtension({
  name: "MinesPack.PickStyle",
  nodeCreated(node) {
    if (node.comfyClass !== "MinesPickStyle") return;
    for (const hook of ["onConfigure", "onConnectionsChange"]) {
      const previous = node[hook];
      node[hook] = function (...args) {
        const result = previous?.apply(this, args);
        capStyle(this);
        return result;
      };
    }
    capStyle(node);
  },
});
