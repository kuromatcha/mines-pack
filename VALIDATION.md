# Merge validation

- Tested with ComfyUI 0.44.2, frontend 1.57.6, Python 3.13.12 on Windows, with Nodes 2.0 enabled.
- Both existing node IDs register under `mine's pack`; the original saver workflow loads without changing its node ID.
- Prompt Sections input schema and conditioning outputs match the original for full, empty, and trailing-comma inputs. The three outputs remain main, selective, selective 2.
- Prompt Sections' two JavaScript files are byte-identical to the supplied installation, preserving its layout, legacy workflow migration, preset format and localStorage key.
- Both nodes displayed together in the actual frontend. The merged saver executed and exported successfully; its Save button turned green.
- All six exporter checks passed, covering concurrent writes, numbering, metadata/pixels, validation and failed-write cleanup. All three frontend files passed JavaScript syntax checks.
- The active ComfyUI process is not restarted by installation. Restart it and refresh the frontend to load the merged pack.

The example workflow uses `examples/sample-a.png`; copy that file into ComfyUI's input folder first. Prompt Sections is shown unconnected, so the demo can test saving without loading a model. Connect CLIP and use its conditioning outputs in your real workflow.
