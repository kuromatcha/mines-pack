"""mine's pack: Prompt Sections and manual numbered PNG saving."""
from .prompt import PromptSectionsCond
from .save import NumberedPNGSaver

PromptSectionsCond.CATEGORY = "mine's pack"
NumberedPNGSaver.CATEGORY = "mine's pack"

NODE_CLASS_MAPPINGS = {
    "PromptSectionsCond": PromptSectionsCond,
    "NumberedPNGSaver": NumberedPNGSaver,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptSectionsCond": "prompt",
    "NumberedPNGSaver": "save",
}
WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
