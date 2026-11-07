/** Browser-local, text-only library shared by every Prompt Sections node. */
export const STORAGE_KEY = "prompt-sections.text-presets.v1";
const FORMAT = "prompt-sections-text-presets";
const MAX_BYTES = 4 * 1024 * 1024;
const MAX_PRESETS = 1000;
const listeners = new Set();

/** Validate an entire library before changing any saved data. */
export function validateLibrary(data) {
  if (!data || data.format !== FORMAT || data.version !== 1 || !Array.isArray(data.presets)) {
    throw new Error("Not a supported Prompt Sections preset file.");
  }
  if (data.presets.length > MAX_PRESETS) throw new Error("Maximum 1000 presets per library.");
  const names = new Set();
  const identifiers = new Set();
  const presets = data.presets.map(preset => {
    if (!preset || typeof preset.id !== "string" || !preset.id || preset.id.length > 100 ||
        typeof preset.name !== "string" || !preset.name.trim() || preset.name.trim().length > 100 ||
        typeof preset.text !== "string" || preset.text.length > 200000) {
      throw new Error("Each preset needs an ID, a name (1–100 characters), and text (up to 200000 characters).");
    }
    const name = preset.name.trim();
    const section = preset.section ?? "both";
    if (!["quality", "prompt", "both"].includes(section)) throw new Error("Invalid preset category.");
    const sections = section === "both" ? ["quality", "prompt"] : [section];
    for (const category of sections) {
      const key = `${category}:${name.toLowerCase()}`;
      if (names.has(key)) throw new Error("Duplicate preset names in this category.");
      names.add(key);
    }
    if (identifiers.has(preset.id)) throw new Error("Duplicate preset IDs in file.");
    identifiers.add(preset.id);
    return { id: preset.id, name, text: preset.text, section };
  });
  const library = { format: FORMAT, version: 1, presets };
  if (new Blob([JSON.stringify(library)]).size > MAX_BYTES) throw new Error("Preset library exceeds 4 MB.");
  return library;
}

/** Read, validate and atomically persist presets without storing workflow layout. */
export class PresetLibrary {
  constructor(storage, createId = () => crypto.randomUUID()) {
    this.storage = storage;
    this.createId = createId;
  }

  /** Never silently discard an unreadable library. */
  read() {
    const saved = this.storage.getItem(STORAGE_KEY);
    return validateLibrary(saved === null
      ? { format: FORMAT, version: 1, presets: [] }
      : JSON.parse(saved));
  }

  /** Writes complete validated data; storage failures leave the old library intact. */
  write(data) {
    const library = validateLibrary(data);
    this.storage.setItem(STORAGE_KEY, JSON.stringify(library));
    for (const listener of listeners) listener();
    return library;
  }

  /** Save new text or explicitly update an existing named preset. */
  save(name, text, existingId = null, section = "prompt") {
    if (!["quality", "prompt"].includes(section)) throw new Error("Choose Quality or Prompt.");
    const library = this.read();
    const existing = existingId && library.presets.find(preset => preset.id === existingId);
    if (existingId && !existing) throw new Error("Preset no longer exists.");
    if (existing && existing.section !== section && existing.section !== "both") throw new Error("Preset belongs to another category.");
    // Old untyped presets stay in both lists. Editing one category splits it,
    // preserving the other category's name and text without duplicating on load.
    const split = existing?.section === "both";
    const preset = { id: split ? this.createId() : existing?.id ?? this.createId(), name, text, section };
    if (split) {
      existing.section = section === "quality" ? "prompt" : "quality";
      library.presets.push(preset);
    } else if (existing) library.presets[library.presets.indexOf(existing)] = preset;
    else library.presets.push(preset);
    this.write(library);
    return preset.id;
  }

  /** Rename without modifying the saved prompt text. */
  rename(id, name, section = null) {
    const preset = this.read().presets.find(item => item.id === id);
    if (!preset) throw new Error("Preset no longer exists.");
    return this.save(name, preset.text, id, section ?? (preset.section === "both" ? "prompt" : preset.section));
  }

  /** Delete a library entry, never text already applied to a node. */
  remove(id, section = "prompt") {
    if (!["quality", "prompt"].includes(section)) throw new Error("Choose Quality or Prompt.");
    const library = this.read();
    const existing = library.presets.find(preset => preset.id === id);
    if (existing?.section === "both") existing.section = section === "quality" ? "prompt" : "quality";
    else library.presets = library.presets.filter(preset => preset.id !== id || preset.section !== section);
    this.write(library);
  }

  /** Merge backups without overwriting local names or trusting imported identifiers. */
  importText(text) {
    if (new Blob([text]).size > MAX_BYTES) throw new Error("Preset file exceeds 4 MB.");
    const incoming = validateLibrary(JSON.parse(text));
    const library = this.read();
    let added = 0;
    for (const preset of incoming.presets) {
      if (library.presets.some(item => item.name.toLowerCase() === preset.name.toLowerCase() && item.text === preset.text &&
          (item.section === "both" || item.section === preset.section))) continue;
      let name = preset.name;
      let suffix = 2;
      while (library.presets.some(item => item.name.toLowerCase() === name.toLowerCase() &&
          (item.section === preset.section || item.section === "both" || preset.section === "both"))) {
        const ending = ` (imported ${suffix++})`;
        name = preset.name.slice(0, 100 - ending.length) + ending;
      }
      library.presets.push({ id: this.createId(), name, text: preset.text, section: preset.section });
      added++;
    }
    this.write(library);
    return added;
  }

  /** Export a portable library containing names and text only, plus format metadata. */
  exportText() { return JSON.stringify(this.read(), null, 2); }
}

export const PRESET_HEIGHT = 48;
export const FOOTER_HEIGHT = 36;
export const PRESET_CSS = `
.ps-presets { width:100%; box-sizing:border-box; background:transparent;
  color:#ddd; font:12px sans-serif; position:relative; }
.ps-section-presets { height:48px; min-height:48px; max-height:48px; }
.ps-prompt-presets::before { content:""; position:absolute; top:-3px; left:0; right:0; height:1px; background:#444; }
.ps-preset-row { display:grid; grid-template-columns:minmax(0,1fr) auto auto auto; grid-template-rows:16px 28px; gap:4px; }
.ps-section-label { grid-column:1/-1; color:#aaa; font-size:11px; line-height:16px; }
.ps-presets select,.ps-presets button,.ps-presets input[type=text] { min-width:0; min-height:26px; border:1px solid #484848;
  border-radius:3px; background:#292929; color:#eee; font:inherit; }
.ps-section-presets select { height:28px; min-height:28px; font-size:11px; }
.ps-presets.ps-section-presets button { height:28px; min-height:28px; font-size:11px; padding:0 5px; }
.ps-presets select { width:100%; text-overflow:ellipsis; }
.ps-presets button { padding:2px 6px; cursor:pointer; }
.ps-presets button:hover:not(:disabled) { background:#233957; }
.ps-presets :focus-visible { outline:2px solid #6c8caf; outline-offset:1px; }
.ps-presets :disabled { opacity:.4; cursor:default; }
.ps-preset-footer { display:flex; gap:5px; align-items:center; flex-wrap:wrap; }
.ps-preset-tools { height:36px; min-height:36px; max-height:36px; padding:4px 0; }
.ps-preset-status { flex:1; min-width:70px; color:#bdbdbd; font-size:11px; overflow-wrap:anywhere; }
.ps-preset-editor { position:absolute; inset:auto 0 0; z-index:10; background:#242424; padding:10px;
  border:1px solid #484848; border-radius:6px;
  display:flex; flex-direction:column; gap:8px; box-sizing:border-box; }
.ps-preset-editor[hidden] { display:none; }
.ps-preset-editor input { width:100%; box-sizing:border-box; padding:5px; }
.ps-preset-editor-actions { display:flex; gap:6px; }
`;

/** Make a UI element without interpreting preset names or prompts as HTML. */
function element(tag, text, parent) {
  const result = document.createElement(tag);
  if (text) result.textContent = text;
  parent?.appendChild(result);
  return result;
}

/** Append compact UI-only preset rows immediately below the full-width Prompt field. */
export function mountTextPresets(node, notifyChange = () => {}) {
  const container = element("div");
  container.className = "ps-presets ps-preset-tools";
  const library = new PresetLibrary({
    getItem: key => window.localStorage.getItem(key),
    setItem: (key, value) => window.localStorage.setItem(key, value),
  });
  const rows = [];
  const sections = { quality: "Quality", prompt: "Prompt" };
  let refresh;
  let status;
  const editor = element("form");
  editor.className = "ps-preset-editor";
  editor.hidden = true;
  editor.setAttribute("role", "dialog");
  editor.setAttribute("aria-label", "Preset editor");
  const editorMessage = element("label", "", editor);
  const editorInput = element("input", "", editor);
  editorInput.type = "text";
  editorInput.maxLength = 100;
  editorInput.setAttribute("aria-label", "Preset name");
  const editorActions = element("div", "", editor);
  editorActions.className = "ps-preset-editor-actions";
  const editorAccept = element("button", "Save", editorActions);
  editorAccept.type = "submit";
  const editorCancel = element("button", "Cancel", editorActions);
  editorCancel.type = "button";
  let resolveEditor;

  /** Resolve in-node prompts without browser-native dialogs (unsupported in some hosts). */
  const finishEditor = value => {
    editor.hidden = true;
    const resolve = resolveEditor;
    resolveEditor = null;
    resolve?.(value);
  };
  const ask = (message, initialName, action) => new Promise(resolve => {
    resolveEditor?.(null);
    resolveEditor = resolve;
    editorMessage.textContent = message;
    editorInput.hidden = initialName === null;
    editorInput.value = initialName ?? "";
    editorInput.setCustomValidity("");
    editorAccept.textContent = action;
    editor.hidden = false;
    if (initialName === null) editorAccept.focus();
    else { editorInput.focus(); editorInput.select(); }
  });
  editor.onsubmit = event => {
    event.preventDefault();
    if (!editorInput.hidden && !editorInput.value.trim()) {
      editorInput.setCustomValidity("Enter a preset name.");
      editorInput.reportValidity();
      return;
    }
    finishEditor(editorInput.hidden ? true : editorInput.value);
  };
  editorInput.oninput = () => editorInput.setCustomValidity("");
  editorCancel.onclick = () => finishEditor(null);
  editor.addEventListener("keydown", event => { if (event.key === "Escape") finishEditor(null); });

  /** Surface failures locally without replacing prompt text or saved presets. */
  const report = message => { status.textContent = message; };
  const guard = operation => {
    try {
      const result = operation();
      return result?.catch ? result.catch(error => report(error.message)) : result;
    }
    catch (error) { report(error.message); return undefined; }
  };

  for (const [section, label] of Object.entries(sections)) {
    const row = element("div");
    row.className = `ps-presets ps-section-presets ps-${section}-presets ps-preset-row`;
    element("span", `${label} preset`, row).className = "ps-section-label";
    const selector = element("select", "", row);
    selector.setAttribute("aria-label", `${label} preset`);
    const buttons = {};
    for (const action of ["Save", "Rename", "Delete"]) {
      buttons[action] = element("button", action, row);
      buttons[action].type = "button";
      buttons[action].setAttribute("aria-label", `${action} ${label} preset`);
    }
    const field = () => node.widgets?.find(widget => widget.name === section);
    const connected = () => node.inputs?.some(input => input.name === section && input.link != null);
    const sectionPresets = () => library.read().presets.filter(preset => preset.section === section || preset.section === "both");
    selector.addEventListener("change", () => guard(() => {
      const preset = sectionPresets().find(item => item.id === selector.value);
      if (!preset) { refresh(); return; }
      const widget = field();
      if (!widget || connected()) throw new Error("Disconnect this section's input to apply a preset.");
      widget.value = preset.text;
      // Native legacy widgets and Vue component widgets both keep their original value contract.
      const textarea = widget.element?.tagName === "TEXTAREA" ? widget.element : widget.inputEl;
      if (textarea?.tagName === "TEXTAREA" && textarea.value !== preset.text) {
        textarea.value = preset.text;
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
      }
      widget.callback?.(preset.text);
      node.setDirtyCanvas?.(true, true);
      notifyChange();
      refresh();
      report(`Applied ${preset.name}.`);
    }));
    buttons.Save.addEventListener("click", () => guard(async () => {
      if (connected() || !field()) throw new Error("Disconnect this section's input to save its text.");
      const presets = sectionPresets();
      const selected = presets.find(item => item.id === selector.value);
      const name = await ask("Preset name", selected?.name ?? "", "Save");
      if (name === null) return;
      const existing = sectionPresets().find(item => item.name.toLowerCase() === name.trim().toLowerCase());
      if (existing && !await ask(`Replace saved text in “${existing.name}”?`, null, "Replace")) return;
      if (connected() || !field()) throw new Error("Disconnect this section's input to save its text.");
      const id = library.save(name, field().value, existing?.id, section);
      selector.value = id;
      refresh();
      report("Preset saved.");
    }));
    buttons.Rename.addEventListener("click", () => guard(async () => {
      const preset = sectionPresets().find(item => item.id === selector.value);
      if (!preset) return;
      const name = await ask("New preset name", preset.name, "Rename");
      if (name === null) return;
      selector.value = library.rename(preset.id, name, section);
      refresh();
      report("Preset renamed.");
    }));
    buttons.Delete.addEventListener("click", () => guard(async () => {
      const preset = sectionPresets().find(item => item.id === selector.value);
      if (preset && await ask(`Delete preset “${preset.name}”? Applied text will stay unchanged.`, null, "Delete")) {
        library.remove(preset.id, section);
        report("Preset deleted.");
      }
    }));
    rows.push({ row, section, selector, buttons, field, connected });
  }
  const footer = element("div", "", container);
  footer.className = "ps-preset-footer";
  const importButton = element("button", "Import", footer);
  const exportButton = element("button", "Export", footer);
  status = element("span", "", footer);
  status.className = "ps-preset-status";
  status.setAttribute("role", "status");
  const fileInput = element("input", "", container);
  fileInput.type = "file";
  fileInput.accept = ".json,application/json";
  fileInput.hidden = true;
  container.appendChild(editor);
  importButton.onclick = () => fileInput.click();
  fileInput.onchange = async () => {
    try {
      const file = fileInput.files?.[0];
      if (!file) return;
      if (file.size > MAX_BYTES) throw new Error("Preset file exceeds 4 MB.");
      report(`Imported ${library.importText(await file.text())} presets.`);
    } catch (error) { report(error.message); }
    finally { fileInput.value = ""; }
  };
  exportButton.onclick = () => guard(() => {
    const url = URL.createObjectURL(new Blob([library.exportText()], { type: "application/json" }));
    const anchor = element("a");
    anchor.href = url;
    anchor.download = "prompt-sections-presets.json";
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    report("Presets exported.");
  });

  /** Refresh dropdown names without applying text or changing workflow content. */
  refresh = () => guard(() => {
    const presets = library.read().presets.sort((first, second) => first.name.localeCompare(second.name));
    for (const { section, selector, buttons, field, connected } of rows) {
      const sectionPresets = presets.filter(preset => preset.section === section || preset.section === "both");
      let selected = selector.value;
      const preset = sectionPresets.find(item => item.id === selected);
      if (!preset || preset.text !== field()?.value) selected = "";
      selector.replaceChildren();
      const empty = element("option", "Choose preset…", selector);
      empty.value = "";
      for (const preset of sectionPresets) {
        const option = element("option", preset.name, selector);
        option.value = preset.id;
      }
      selector.value = selected;
      selector.disabled = !field() || connected();
      buttons.Save.disabled = selector.disabled;
      buttons.Rename.disabled = !selected;
      buttons.Delete.disabled = !selected;
    }
  });
  // Do not let the graph consume typing/deletion/navigation inside the controls.
  const controls = [...rows.map(({ row, section }) => ({ element: row, name: `${section}_presets`, height: PRESET_HEIGHT })),
    { element: container, name: "text_presets", height: FOOTER_HEIGHT }];
  for (const control of controls) {
    for (const eventName of ["pointerdown", "keydown", "keyup", "wheel"]) {
      control.element.addEventListener(eventName, event => event.stopPropagation());
    }
    control.element.addEventListener("focusin", refresh);
    const widget = node.addDOMWidget(control.name, "ps-presets", control.element, {
      serialize: false, margin: 0, getValue: () => "", setValue: () => {},
      getMinHeight: () => control.height, getMaxHeight: () => control.height,
      getHeight: () => control.height,
    });
    widget.serialize = false;
  }
  listeners.add(refresh);
  const storageChanged = event => { if (event.key === STORAGE_KEY || event.key === null) refresh(); };
  window.addEventListener("storage", storageChanged);
  const previousRemoved = node.onRemoved;
  node.onRemoved = function (...args) {
    finishEditor(null);
    listeners.delete(refresh);
    window.removeEventListener("storage", storageChanged);
    return previousRemoved?.apply(this, args);
  };
  refresh();
  return { refresh, container };
}
