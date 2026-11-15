"""Windows: hide a harmless asyncio traceback."""


def quiet_socket_reset():
    """Windows only: drop the harmless 'ConnectionResetError [WinError 10054]' traceback that asyncio logs at ERROR
    when a browser tab closes or refreshes (Proactor _call_connection_lost, cpython#83413, Comfy-Org/ComfyUI#15163).
    Every other loop exception still goes to the previous handler."""
    import asyncio
    import sys
    if sys.platform != "win32":
        return
    try:
        loop = asyncio.get_event_loop()  # ComfyUI's server loop: custom nodes are imported while it runs
    except RuntimeError:
        return
    previous = loop.get_exception_handler()
    if getattr(previous, "_mines_quiet_reset", False):
        return

    def handler(loop, context):
        if isinstance(context.get("exception"), ConnectionResetError) and \
                "_call_connection_lost" in repr(context.get("handle", "")) + str(context.get("message", "")):
            return
        if previous is not None:
            previous(loop, context)
        else:
            loop.default_exception_handler(context)

    handler._mines_quiet_reset = True
    loop.set_exception_handler(handler)
