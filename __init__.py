"""mine's pack: Prompt Sections, manual numbered PNG saving, and the nodes for the Mine's video workflows."""
from .prompt import PromptSectionsCond
from .save import NumberedPNGSaver
from .video import MinesLoadImageOptional, MinesSVIProEndFrame
from .color import MinesColorDriftFix, MinesKeepSourceColors
from .mask import MinesBackgroundRemovalResolution, MinesMaskTemporalSmooth
from .winfix import quiet_socket_reset

NODE_CLASS_MAPPINGS = {
    "PromptSectionsCond": PromptSectionsCond,
    "NumberedPNGSaver": NumberedPNGSaver,
    "MinesLoadImageOptional": MinesLoadImageOptional,
    "MinesSVIProEndFrame": MinesSVIProEndFrame,
    "MinesColorDriftFix": MinesColorDriftFix,
    "MinesKeepSourceColors": MinesKeepSourceColors,
    "MinesBackgroundRemovalResolution": MinesBackgroundRemovalResolution,
    "MinesMaskTemporalSmooth": MinesMaskTemporalSmooth,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptSectionsCond": "prompt",
    "NumberedPNGSaver": "save",
    "MinesLoadImageOptional": "load image (optional)",
    "MinesSVIProEndFrame": "SVIPro end frame",
    "MinesColorDriftFix": "color drift fix",
    "MinesKeepSourceColors": "keep source colors",
    "MinesBackgroundRemovalResolution": "background removal resolution",
    "MinesMaskTemporalSmooth": "mask temporal smooth",
}
for node in NODE_CLASS_MAPPINGS.values():
    node.CATEGORY = "mine's pack"

quiet_socket_reset()

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
