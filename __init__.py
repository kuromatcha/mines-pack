"""mine's pack: prompt sections, save on click, inpaint crop and stitch, and the nodes for the Mine's video workflows."""
from .prompt import PromptSectionsCond, MinesPickStyle
from .save import NumberedPNGSaver
from .video import MinesSVIProEndFrame, MinesH3FrameGuides
from .color import MinesColorDriftFix, MinesKeepSourceColors
from .inpaint import MinesInpaintCrop, MinesInpaintStitch
from .winfix import quiet_socket_reset

NODE_CLASS_MAPPINGS = {
    "PromptSectionsCond": PromptSectionsCond,
    "MinesPickStyle": MinesPickStyle,
    "NumberedPNGSaver": NumberedPNGSaver,
    "MinesSVIProEndFrame": MinesSVIProEndFrame,
    "MinesH3FrameGuides": MinesH3FrameGuides,
    "MinesColorDriftFix": MinesColorDriftFix,
    "MinesKeepSourceColors": MinesKeepSourceColors,
    "MinesInpaintCrop": MinesInpaintCrop,
    "MinesInpaintStitch": MinesInpaintStitch,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptSectionsCond": "prompt",
    "MinesPickStyle": "pick style",
    "NumberedPNGSaver": "save on click",
    "MinesSVIProEndFrame": "SVIPro end frame",
    "MinesH3FrameGuides": "H3 frame guides",
    "MinesColorDriftFix": "color drift fix",
    "MinesKeepSourceColors": "keep source colors",
    "MinesInpaintCrop": "inpaint crop",
    "MinesInpaintStitch": "inpaint stitch",
}
GROUPS = {
    "prompt": ["PromptSectionsCond", "MinesPickStyle"],
    "image": ["NumberedPNGSaver"],
    "inpaint": ["MinesInpaintCrop", "MinesInpaintStitch"],
    "video": ["MinesSVIProEndFrame", "MinesH3FrameGuides", "MinesColorDriftFix", "MinesKeepSourceColors"],
}
for group, names in GROUPS.items():
    for name in names:
        NODE_CLASS_MAPPINGS[name].CATEGORY = f"mine's pack/{group}"

quiet_socket_reset()

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
