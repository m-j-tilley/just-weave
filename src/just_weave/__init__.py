"""
just-weave — the standalone lenticular weave for the Samsung Odyssey 3D (G90XF).

Turn left/right views (or a side-by-side frame) + an eye position into the woven, lenticular-
interleaved framebuffer the panel expects. Designed to be driven by any tool — a video player,
a browser compositor, a game/ReShade pipeline — not just one app.

    from just_weave import Weaver, standalone, OPTPOS
    wv = standalone()                  # headless offscreen context + a G90XF Weaver
    wv.set_eye(*OPTPOS)
    wv.weave(left_rgb, right_rgb)       # -> wv.output framebuffer
    woven = wv.read()                   # HxWx3 uint8, top-down

The weave math is extracted byte-for-byte from the verified player; see shaders.py.
"""
from .weaver import Weaver, standalone
from .params import WeaveParams
from .oracle import Oracle, OPTPOS

__version__ = "0.1.0"
__all__ = ["Weaver", "standalone", "WeaveParams", "Oracle", "OPTPOS", "__version__"]
