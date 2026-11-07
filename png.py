"""PNG encoding and collision-safe sequential filenames, independent of ComfyUI."""
import io
import json
import os
import re
from pathlib import Path

from PIL import Image
from PIL.PngImagePlugin import PngInfo


def export_png(source, folder, prefix, padding, metadata=None):
    if not isinstance(prefix, str) or re.search(r'[<>:"/\\|?*\x00-\x1f]', prefix):
        raise ValueError("Prefix must be a filename prefix, without path separators or special characters.")
    if not isinstance(padding, int) or isinstance(padding, bool) or not 1 <= padding <= 12:
        raise ValueError("Number padding must be between 1 and 12.")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(re.escape(prefix) + r"([0-9]+)\.png", re.IGNORECASE)
    highest = 0
    for entry in folder.iterdir():
        match = pattern.fullmatch(entry.name)
        if match and entry.is_file():
            highest = max(highest, int(match[1]))
    info = PngInfo()
    for key, value in (metadata or {}).items():
        info.add_text(key, json.dumps(value, ensure_ascii=False))
    encoded = io.BytesIO()
    with Image.open(source) as image:
        # A fresh image avoids inheriting EXIF/text from the staged image.
        clean = Image.frombytes(image.mode, image.size, image.tobytes())
        clean.save(encoded, format="PNG", pnginfo=info, compress_level=4)
    payload = encoded.getvalue()
    number = highest + 1
    while True:
        target = folder / f"{prefix}{number:0{padding}d}.png"
        try:
            stream = target.open("xb")
        except FileExistsError:
            number += 1
            continue
        try:
            with stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return target.resolve()
