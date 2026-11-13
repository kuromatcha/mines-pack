import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const SETTINGS = ["folder", "filename_prefix", "number_padding", "include_metadata"];
const BUTTON_CLASS = "mines-pack-save-button";

// The latest run of any save node; the top bar button saves its image.
let latest = null;
let busy = false;
let savedKey = null;

function toast(severity, summary, detail) {
    app.extensionManager?.toast?.add({ severity, summary, detail, life: severity === "error" ? 6000 : 3000 });
}

function currentRequest() {
    if (!latest) return null;
    const { node, batch } = latest;
    const settings = {};
    for (const name of SETTINGS) {
        const widget = node.widgets?.find(w => w.name === name);
        const input = node.inputs?.find(i => i.name === name);
        settings[name] = input?.link != null ? batch.settings[name] : (widget?.value ?? batch.settings[name]);
    }
    return { token: batch.token, index: 0, settings };
}

// Action bar buttons are plain objects, so state is shown through a root attribute.
function update() {
    let state = "empty";
    if (busy) state = "busy";
    else if (latest?.batch.count > 0) {
        state = savedKey !== null && savedKey === JSON.stringify(currentRequest()) ? "saved" : "ready";
    }
    document.documentElement.dataset.minesPackSave = state;
}

async function save() {
    if (busy) return;
    const request = currentRequest();
    if (!request || !latest.batch.count) {
        toast("warn", "Nothing to save", "Run a workflow with a save node first.");
        return;
    }
    const key = JSON.stringify(request);
    savedKey = null;
    busy = true;
    update();
    try {
        const response = await api.fetchApi("/numbered-png-saver/save", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify(request),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || `Save failed (${response.status}).`);
        savedKey = key;
        toast("success", "Saved", result.filename);
    } catch (error) {
        toast("error", "Save failed", error.message);
    } finally {
        busy = false;
        update();
    }
}

app.registerExtension({
    name: "NumberedPNGSaver.ManualExport",
    actionBarButtons: [{
        icon: "pi pi-save",
        label: "Save",
        tooltip: "Save the latest image as a numbered PNG",
        class: BUTTON_CLASS,
        onClick: save,
    }],
    commands: [{ id: "MinesPack.SaveImage", label: "Save latest image (mine's pack)", icon: "pi pi-save", function: save }],
    setup() {
        const style = document.createElement("style");
        style.textContent = `
            .${BUTTON_CLASS} { transition: color .15s, opacity .15s; }
            :root[data-mines-pack-save="empty"] .${BUTTON_CLASS},
            :root[data-mines-pack-save="busy"] .${BUTTON_CLASS} { opacity: .45; }
            :root[data-mines-pack-save="busy"] .${BUTTON_CLASS} { pointer-events: none; }
            :root[data-mines-pack-save="ready"] .${BUTTON_CLASS} { color: #e0646b !important; }
            :root[data-mines-pack-save="saved"] .${BUTTON_CLASS} { color: #3fb28a !important; }
        `;
        document.head.append(style);
        update();
    },
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "NumberedPNGSaver") return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            originalCreated?.apply(this, arguments);
            const node = this;
            for (const [name, label] of Object.entries({ filename_prefix: "Prefix", number_padding: "Digits", include_metadata: "Metadata", folder: "Folder" })) {
                const widget = node.widgets?.find(w => w.name === name);
                if (widget) widget.label = label;
            }
            // Changing a setting after saving turns the button back to unsaved.
            for (const widget of node.widgets ?? []) {
                if (!SETTINGS.includes(widget.name)) continue;
                const callback = widget.callback;
                widget.callback = function () {
                    const result = callback?.apply(this, arguments);
                    if (latest?.node === node) update();
                    return result;
                };
            }
            const originalExecuted = node.onExecuted;
            node.onExecuted = function (message) {
                originalExecuted?.apply(this, arguments);
                const batch = message?.numbered_png?.[0];
                if (!batch) return;
                latest = { node, batch };
                savedKey = null;
                if (batch.metadata_disabled) toast("info", "Metadata disabled globally", "Images will be saved without metadata.");
                update();
            };
            const originalRemoved = node.onRemoved;
            node.onRemoved = function () {
                if (latest?.node === node) {
                    latest = null;
                    savedKey = null;
                    update();
                }
                originalRemoved?.apply(this, arguments);
            };
        };
    },
});
