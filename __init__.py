"""mine's pack: Prompt Sections, manual numbered PNG saving, and the nodes for the Mine's video workflows."""
from .prompt import PromptSectionsCond, MinesPickStyle
from .save import NumberedPNGSaver
from .video import MinesLoadImageOptional, MinesSVIProEndFrame, MinesH3FrameGuides
from .color import MinesColorDriftFix, MinesKeepSourceColors
from .mask import MinesBackgroundRemovalResolution, MinesMaskTemporalSmooth
from .inpaint import MinesInpaintCrop, MinesInpaintStitch
from .winfix import quiet_socket_reset

NODE_CLASS_MAPPINGS = {
    "PromptSectionsCond": PromptSectionsCond,
    "MinesPickStyle": MinesPickStyle,
    "NumberedPNGSaver": NumberedPNGSaver,
    "MinesLoadImageOptional": MinesLoadImageOptional,
    "MinesSVIProEndFrame": MinesSVIProEndFrame,
    "MinesH3FrameGuides": MinesH3FrameGuides,
    "MinesColorDriftFix": MinesColorDriftFix,
    "MinesKeepSourceColors": MinesKeepSourceColors,
    "MinesBackgroundRemovalResolution": MinesBackgroundRemovalResolution,
    "MinesMaskTemporalSmooth": MinesMaskTemporalSmooth,
    "MinesInpaintCrop": MinesInpaintCrop,
    "MinesInpaintStitch": MinesInpaintStitch,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptSectionsCond": "prompt",
    "MinesPickStyle": "pick style",
    "NumberedPNGSaver": "save",
    "MinesLoadImageOptional": "load image (optional)",
    "MinesSVIProEndFrame": "SVIPro end frame",
    "MinesH3FrameGuides": "H3 frame guides",
    "MinesColorDriftFix": "color drift fix",
    "MinesKeepSourceColors": "keep source colors",
    "MinesBackgroundRemovalResolution": "background removal resolution",
    "MinesMaskTemporalSmooth": "mask temporal smooth",
    "MinesInpaintCrop": "inpaint crop",
    "MinesInpaintStitch": "inpaint stitch",
}
for node in NODE_CLASS_MAPPINGS.values():
    node.CATEGORY = "mine's pack"

quiet_socket_reset()

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
