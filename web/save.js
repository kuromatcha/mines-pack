import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "NumberedPNGSaver.ManualExport",
    setup() {
        const style = document.createElement("style");
        style.textContent = `
            .lg-node:has(.numbered-png-saver-panel):not([data-collapsed]) {
                min-height: 0 !important;
                height: fit-content !important;
            }
            .lg-node:has(.numbered-png-saver-panel) > [data-corner="NE"],
            .lg-node:has(.numbered-png-saver-panel) > [data-corner="NW"] {
                display: none;
            }
            .lg-node:has(.numbered-png-saver-panel) > [data-corner="SE"],
            .lg-node:has(.numbered-png-saver-panel) > [data-corner="SW"] {
                cursor: ew-resize;
            }
        `;
        document.head.append(style);
    },
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "NumberedPNGSaver") return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            originalCreated?.apply(this, arguments);
            const node = this;
            let batch = null;
            let busy = false;
            let savedRequest = null;
            const pane = document.createElement("div");
            pane.className = "numbered-png-saver-panel";
            pane.style.cssText = "display:flex;flex-direction:column;gap:8px;padding:10px;box-sizing:border-box;width:100%;height:100%;background:var(--comfy-input-bg,#202024);color:var(--input-text,#ddd);font:12px sans-serif;border-radius:8px;overflow:hidden;";
            function button(text) {
                const element = document.createElement("button");
                element.type = "button";
                element.textContent = text;
                element.style.cssText = "padding:8px 12px;border:1px solid #555;border-radius:5px;background:#34343a;color:#eee;cursor:pointer;font:inherit;";
                return element;
            }
            const save = button("Save");
            const status = document.createElement("div");
            status.setAttribute("role", "status");
            status.style.cssText = "white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.4;";
            status.hidden = true;
            pane.append(save, status);
            // DOM widgets are rendered by Nodes 2.0 as well as the classic renderer.
            node.addDOMWidget("numbered_png_panel", "div", pane, {
                serialize: false,
                getMinHeight: () => 55,
                getHeight: () => 55,
            });
            for (const [name, label] of Object.entries({filename_prefix: "Prefix", number_padding: "Digits", include_metadata: "Metadata", folder: "Folder"})) {
                const widget = node.widgets?.find(w => w.name === name);
                if (widget) widget.label = label;
            }
            node.setSize([340, 280]);
            const originalResize = node.onResize;
            node.onResize = function (size) {
                originalResize?.apply(this, arguments);
                size[1] = node.computeSize()[1];
            };
            function currentRequest() {
                if (!batch) return null;
                const settings = {};
                for (const name of ["folder", "filename_prefix", "number_padding", "include_metadata"]) {
                    const widget = node.widgets?.find(w => w.name === name);
                    const input = node.inputs?.find(i => i.name === name);
                    settings[name] = input?.link != null ? batch.settings[name] : (widget?.value ?? batch.settings[name]);
                }
                return { token: batch.token, index: 0, settings };
            }
            function update() {
                const ready = batch && batch.count > 0;
                const saved = savedRequest !== null && savedRequest === JSON.stringify(currentRequest());
                save.disabled = !ready || busy;
                save.style.opacity = save.disabled ? ".45" : "1";
                save.style.background = saved && !busy ? "#286c56" : "#a13d43";
                save.setAttribute("aria-label", saved && !busy ? "Save (saved)" : "Save");
                status.hidden = !status.textContent;
            }
            for (const widget of node.widgets ?? []) {
                if (!["folder", "filename_prefix", "number_padding", "include_metadata"].includes(widget.name)) continue;
                const callback = widget.callback;
                widget.callback = function () {
                    const result = callback?.apply(this, arguments);
                    update();
                    return result;
                };
            }
            save.onclick = async () => {
                if (!batch || busy) return;
                const request = currentRequest();
                const requestKey = JSON.stringify(request);
                savedRequest = null;
                busy = true;
                save.textContent = "Saving…";
                status.textContent = "";
                update();
                try {
                    const response = await api.fetchApi("/numbered-png-saver/save", {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(request),
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || `Save failed (${response.status}).`);
                    savedRequest = requestKey;
                } catch (error) {
                    status.textContent = error.message;
                } finally {
                    busy = false;
                    save.textContent = "Save";
                    update();
                }
            };
            const originalExecuted = node.onExecuted;
            node.onExecuted = function (message) {
                originalExecuted?.apply(this, arguments);
                if (!message.numbered_png?.[0]) return;
                batch = message.numbered_png[0];
                savedRequest = null;
                status.textContent = batch.metadata_disabled ? "Metadata disabled globally" : "";
                update();
            };
            const originalRemoved = node.onRemoved;
            node.onRemoved = function () {
                batch = null;
                pane.remove();
                originalRemoved?.apply(this, arguments);
            };
            update();
        };
    },
});
