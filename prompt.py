class PromptSectionsCond:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "quality": ("STRING", {"multiline": True, "placeholder": "quality", "default": "masterpiece, best quality, very aesthetic"}),
                "style_1": ("STRING", {"multiline": True, "placeholder": "style 1", "default": ""}),
                "style_2": ("STRING", {"multiline": True, "placeholder": "style 2", "default": ""}),
            },
            "optional": {
                "style_3": ("STRING", {"multiline": True, "placeholder": "style 3", "default": ""}),
                "prompt": ("STRING", {"multiline": True, "placeholder": "positive prompt", "default": ""}),
                "negative_prompt": ("STRING", {"multiline": True, "placeholder": "negative prompt", "default": ""}),
            },
        }

    # Appended outputs keep existing workflow links on their original slots.
    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "CONDITIONING", "CONDITIONING")
    RETURN_NAMES = ("style 1", "style 2", "style 3", "negative")
    FUNCTION = "encode"
    CATEGORY = "conditioning"

    @staticmethod
    def _clean(text):
        return (text or "").strip().rstrip(",").strip()

    @classmethod
    def build_texts(cls, quality, style_1, style_2, prompt="", style_3="", negative_prompt=""):
        """Return the four texts encoded by the outputs, in output order.

        web/prompt_split.js mirrors this so the queued prompt can encode each
        output separately (see README)."""
        q, p = cls._clean(quality), cls._clean(prompt)
        styles = [", ".join(s for s in (q, cls._clean(style), p) if s) for style in (style_1, style_2, style_3)]
        return (*styles, cls._clean(negative_prompt))

    def encode(self, clip, quality, style_1, style_2, prompt="", style_3="", negative_prompt=""):
        if clip is None:
            raise RuntimeError("clip input is None")
        encoded = {}
        results = []
        for text in self.build_texts(quality, style_1, style_2, prompt, style_3, negative_prompt):
            # Identical sections share one encode.
            if text not in encoded:
                encoded[text] = clip.encode_from_tokens_scheduled(clip.tokenize(text))
            results.append(encoded[text])
        return tuple(results)


class MinesPickStyle:
    """Passes on one of the prompt node's three styles. The styles not picked are not encoded."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"style": ("INT", {"default": 1, "min": 1, "max": 3})},
            "optional": {name: ("CONDITIONING", {"lazy": True}) for name in ("style_1", "style_2", "style_3")},
        }

    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "pick"
    CATEGORY = "conditioning"

    def check_lazy_status(self, style, **styles):
        name = f"style_{style}"
        return [name] if styles.get(name) is None else []

    def pick(self, style, **styles):
        picked = styles.get(f"style_{style}")
        if picked is None:
            raise ValueError(f"style {style} is not connected")
        return (picked,)
