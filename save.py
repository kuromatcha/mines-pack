"""Manual numbered PNG export for ComfyUI and Nodes 2.0."""
import asyncio
import copy
import logging
import shutil
import threading
import time
import uuid
from pathlib import Path

import numpy as np
from aiohttp import web
from PIL import Image

import folder_paths
from comfy.cli_args import args
from server import PromptServer
from .png import export_png

_lock = threading.RLock()
_batches = {}
_root = Path(folder_paths.get_temp_directory()) / "numbered_png_saver"
_root.mkdir(parents=True, exist_ok=True)
_session = _root / uuid.uuid4().hex
_session.mkdir()
_TTL = 24 * 60 * 60


def _cleanup():
    """Only remove our expired staging data, never user exports."""
    now = time.time()
    for token, record in list(_batches.items()):
        if now - record["created"] > _TTL:
            shutil.rmtree(record["directory"], ignore_errors=True)
            del _batches[token]
    for directory in _root.iterdir():
        if directory.is_dir() and directory != _session:
            if now - directory.stat().st_mtime > _TTL:
                shutil.rmtree(directory, ignore_errors=True)


class NumberedPNGSaver:
    def __init__(self):
        self._previous_token = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "folder": ("STRING", {"default": "", "tooltip": "Blank: ComfyUI output folder. Absolute paths or relative output subfolders are supported."}),
                "filename_prefix": ("STRING", {"default": "", "tooltip": "Blank: 00001.png. Example: character_ gives character_00001.png."}),
                "number_padding": ("INT", {"default": 5, "min": 1, "max": 12}),
                "include_metadata": ("BOOLEAN", {"default": True, "label_on": "On", "label_off": "Off"}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "stage"
    OUTPUT_NODE = True
    CATEGORY = "image/saving"
    DESCRIPTION = "Click Save to save the first input image without rerunning generation."

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Refresh staged images and generation metadata on each run.
        return float("nan")

    def stage(self, images, folder="", filename_prefix="", number_padding=5,
              include_metadata=True, prompt=None, extra_pnginfo=None):
        token = uuid.uuid4().hex
        directory = _session / token
        directory.mkdir(parents=True, exist_ok=True)
        paths = []
        try:
            for index, tensor in enumerate(images):
                array = np.clip(255.0 * tensor.detach().cpu().numpy(), 0, 255).astype(np.uint8)
                image = Image.fromarray(array)
                path = directory / f"{index}.png"
                image.save(path, compress_level=1)
                paths.append(path)
            metadata = {}
            if not args.disable_metadata:
                if prompt is not None:
                    metadata["prompt"] = copy.deepcopy(prompt)
                metadata.update(copy.deepcopy(extra_pnginfo or {}))
            settings = dict(folder=folder, filename_prefix=filename_prefix,
                            number_padding=number_padding, include_metadata=include_metadata)
            with _lock:
                _cleanup()
                previous = _batches.pop(self._previous_token, None)
                if previous:
                    shutil.rmtree(previous["directory"], ignore_errors=True)
                _batches[token] = dict(directory=directory, paths=paths, metadata=metadata,
                                       settings=settings, created=time.time())
                self._previous_token = token
            return {"ui": {"numbered_png": [dict(token=token, count=len(paths),
                           settings=settings, metadata_disabled=args.disable_metadata)]}}
        except BaseException:
            shutil.rmtree(directory, ignore_errors=True)
            raise


def _get_record(token):
    record = _batches.get(token)
    if record is None or time.time() - record["created"] > _TTL:
        raise ValueError("Images expired. Run the workflow again.")
    return record


def _save(data):
    with _lock:
        record = _get_record(data.get("token"))
        index = data.get("index")
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(record["paths"]):
            raise ValueError("Select a valid image number.")
        settings = data.get("settings")
        if not isinstance(settings, dict):
            raise ValueError("Save settings are missing.")
        folder = settings.get("folder", "")
        if not isinstance(folder, str):
            raise ValueError("Folder must be text.")
        destination = Path(folder.strip()) if folder.strip() else Path(folder_paths.get_output_directory())
        if not destination.is_absolute():
            destination = Path(folder_paths.get_output_directory()) / destination
        include = settings.get("include_metadata", True)
        if not isinstance(include, bool):
            raise ValueError("Metadata option must be on or off.")
        target = export_png(record["paths"][index], destination.resolve(),
                            settings.get("filename_prefix", ""), settings.get("number_padding", 5),
                            record["metadata"] if include and not args.disable_metadata else None)
        return {"filename": target.name, "path": str(target),
                "metadata_included": bool(include and not args.disable_metadata)}


@PromptServer.instance.routes.post("/numbered-png-saver/save")
async def save(request):
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError("Invalid save request.")
        result = await asyncio.to_thread(_save, data)
        return web.json_response(result)
    except (ValueError, TypeError, OSError) as error:
        return web.json_response({"error": str(error)}, status=400)
    except Exception:
        logging.exception("Numbered PNG save failed")
        return web.json_response({"error": "Could not save PNG. Check the ComfyUI log."}, status=500)


with _lock:
    _cleanup()
