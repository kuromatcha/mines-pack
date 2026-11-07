class PromptSectionsCond:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "quality": ("STRING", {"multiline": True, "placeholder": "quality", "default": "masterpiece, best quality, very aesthetic"}),
                "style_1": ("STRING", {"multiline": True, "placeholder": "style", "default": ""}),
                "style_2": ("STRING", {"multiline": True, "placeholder": "selective style", "default": ""}),
            },
            "optional": {
                "style_3": ("STRING", {"multiline": True, "placeholder": "selective style 2", "default": ""}),
                "prompt": ("STRING", {"multiline": True, "placeholder": "prompt", "default": ""}),
            },
        }

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "CONDITIONING")
    RETURN_NAMES = ("main", "selective", "selective 2")
    FUNCTION = "encode"
    CATEGORY = "conditioning"

    @staticmethod
    def _clean(text):
        return text.strip().rstrip(",").strip()

    @staticmethod
    def _encode(clip, text):
        tokens = clip.tokenize(text)
        return clip.encode_from_tokens_scheduled(tokens)

    def encode(self, clip, quality, style_1, style_2, prompt="", style_3=""):
        if clip is None:
            raise RuntimeError("clip input is None")
        q, s1, s2, p = map(self._clean, (quality, style_1, style_2, prompt))
        s3 = self._clean(style_3)
        main = ", ".join(s for s in (q, s1, p) if s)
        selective = ", ".join(s for s in (q, s2, p) if s)
        selective_2 = ", ".join(s for s in (q, s3, p) if s)
        return (self._encode(clip, main), self._encode(clip, selective), self._encode(clip, selective_2))
