"""Run directly with Python; no ComfyUI imports needed."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("prompt", Path(__file__).parents[1] / "prompt.py")
prompt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prompt)
Node = prompt.PromptSectionsCond


class FakeClip:
    def __init__(self):
        self.encoded = []

    def tokenize(self, text):
        return text

    def encode_from_tokens_scheduled(self, tokens):
        self.encoded.append(tokens)
        return [[tokens, {}]]


class PromptSectionsTests(unittest.TestCase):
    def test_outputs(self):
        self.assertEqual(Node.RETURN_NAMES, ("style 1", "style 2", "style 3", "negative"))
        self.assertEqual(len(Node.RETURN_TYPES), 4)
        self.assertIn("negative_prompt", Node.INPUT_TYPES()["optional"])

    def test_texts(self):
        texts = Node.build_texts("q,", " a ", "b", prompt="p,, ", style_3="", negative_prompt=" bad, ")
        self.assertEqual(texts, ("q, a, p", "q, b, p", "q, p", "bad"))

    def test_negative_has_no_quality(self):
        self.assertEqual(Node.build_texts("q", "", "")[3], "")

    def test_identical_sections_encode_once(self):
        clip = FakeClip()
        result = Node().encode(clip, "q", "s", "s", prompt="p", style_3="t", negative_prompt="n")
        self.assertEqual([r[0][0] for r in result], ["q, s, p", "q, s, p", "q, t, p", "n"])
        self.assertEqual(clip.encoded, ["q, s, p", "q, t, p", "n"])

    def test_old_call_without_negative(self):
        result = Node().encode(FakeClip(), "q", "a", "b", "p", "c")
        self.assertEqual(result[3][0][0], "")


if __name__ == "__main__":
    unittest.main()
