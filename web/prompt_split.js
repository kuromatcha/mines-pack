/**
 * ComfyUI caches a node by its own inputs plus every ancestor's inputs. One
 * PromptSectionsCond feeding several samplers therefore makes every sampler
 * re-run when any one section changes. Before queueing, replace each prompt
 * node with one core CLIPTextEncode per used output, so each sampler depends
 * only on the text it actually receives. The saved workflow is unchanged.
 */
const CLASS = "PromptSectionsCond";
const TEXT_INPUTS = ["quality", "style_1", "style_2", "style_3", "prompt", "negative_prompt"];
const OUTPUT_KEYS = ["style1", "style2", "style3", "negative"];
const OUTPUT_TITLES = ["style 1", "style 2", "style 3", "negative"];

/** Same as PromptSectionsCond._clean in prompt.py. */
function clean(text) {
  return String(text ?? "").trim().replace(/,+$/, "").trim();
}

/** Same as PromptSectionsCond.build_texts in prompt.py. */
export function buildTexts(inputs) {
  const quality = clean(inputs.quality);
  const prompt = clean(inputs.prompt);
  const styles = ["style_1", "style_2", "style_3"].map(name =>
    [quality, clean(inputs[name]), prompt].filter(Boolean).join(", "));
  return [...styles, clean(inputs.negative_prompt)];
}

const isLink = value => Array.isArray(value) && value.length === 2 && typeof value[1] === "number";

/** Rewrite an API prompt in place. Nodes it cannot split are left as they are. */
export function splitPromptSections(output) {
  for (const [id, node] of Object.entries(output)) {
    if (node?.class_type !== CLASS) continue;
    const inputs = node.inputs ?? {};
    // Text arriving through links is only known at run time; keep the node.
    if (!isLink(inputs.clip) || TEXT_INPUTS.some(name => isLink(inputs[name]))) continue;
    const ids = OUTPUT_KEYS.map(key => `${id}_${key}`);
    if (ids.some(newId => newId in output)) continue;

    const texts = buildTexts(inputs);
    const used = new Set();
    for (const other of Object.values(output)) {
      for (const [name, value] of Object.entries(other?.inputs ?? {})) {
        if (!isLink(value) || String(value[0]) !== String(id) || !ids[value[1]]) continue;
        other.inputs[name] = [ids[value[1]], 0];
        used.add(value[1]);
      }
    }
    delete output[id];
    const title = node._meta?.title ?? "prompt";
    for (const slot of used) {
      output[ids[slot]] = {
        class_type: "CLIPTextEncode",
        inputs: { text: texts[slot], clip: inputs.clip },
        _meta: { title: `${title} (${OUTPUT_TITLES[slot]})` },
      };
    }
  }
  return output;
}
