"""
weaver.py — the public Weaver API.

A Weaver turns left/right views (or a side-by-side frame) + an eye position into the woven,
lenticular-interleaved framebuffer the Samsung Odyssey 3D (G90XF) expects. It owns the weave shader,
the attribute oracle, and the panel calibration; the CALLER owns the GL context, the source frames,
and (if head-tracking) the eye position.

    from just_weave import Weaver, standalone, OPTPOS
    wv = standalone()                       # headless offscreen context + a G90XF Weaver
    wv.set_eye(*OPTPOS)                      # eye position, display-frame cm
    fbo = wv.weave(left_rgb, right_rgb)      # -> woven framebuffer (also wv.output)
    woven = wv.read()                        # HxWx3 uint8, top-down

`left`/`right`/`sbs` may be a moderngl.Texture or an HxWx3 uint8 numpy array.
The weave math is byte-identical to the verified player; see shaders.py.
"""
from __future__ import annotations
import os
import numpy as np
import moderngl

from . import shaders
from .params import WeaveParams
from .correction import load_correction, corr_rgb
from .oracle import Oracle, OPTPOS

__all__ = ["Weaver", "standalone", "OPTPOS", "WeaveParams"]

_CALIB_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calib")

# full-screen quad: pos.x, pos.y, uv.x, uv.y  for TL, TR, BL, BR
_CORNERS = [(-1.0, 1.0, 0.0, 0.0), (1.0, 1.0, 1.0, 0.0),
            (-1.0, -1.0, 0.0, 1.0), (1.0, -1.0, 1.0, 1.0)]
# NDC corners for oracle.fill (FillAttributes y screen-DOWN): TL, TR, BL, BR
_NDC = [(-1.0, -1.0), (1.0, -1.0), (-1.0, 1.0), (1.0, 1.0)]
_INDICES = np.array([0, 1, 2, 1, 3, 2], dtype="i4")


class Weaver:
    def __init__(self, ctx: moderngl.Context, *, panel: str = "G90XF",
                 res: tuple[int, int] = (3840, 2160), calib_dir: str | None = None,
                 parametric: bool = True, params: WeaveParams | None = None):
        self.ctx = ctx
        self.panel = panel
        self.W, self.H = int(res[0]), int(res[1])
        self.params = params or WeaveParams()
        self.calib_dir = calib_dir or os.path.join(_CALIB_ROOT, panel)
        if not os.path.isdir(self.calib_dir):
            raise FileNotFoundError(f"no calibration for panel {panel!r} at {self.calib_dir}")
        self._owns_ctx = False
        self._src_tex: dict[str, moderngl.Texture] = {}

        # --- weave programs (two-texture + side-by-side) ---
        self._prog = ctx.program(vertex_shader=shaders.VERT, fragment_shader=shaders.FRAG)
        self._prog_sbs = ctx.program(vertex_shader=shaders.VERT, fragment_shader=shaders.FRAG_SCREEN)
        self._prog["uL"] = 0; self._prog["uR"] = 1
        self._prog["uCorrA"] = 2; self._prog["uCorrB"] = 3
        self._prog_sbs["uSrc"] = 0; self._prog_sbs["uCorrA"] = 2; self._prog_sbs["uCorrB"] = 3
        self._prog_sbs["uSrcFlip"] = 0; self._prog_sbs["uSrcBGR"] = 0; self._prog_sbs["uSrcSwapLR"] = 1
        for p in (self._prog, self._prog_sbs):
            p["uRes"].value = (float(self.W), float(self.H))
            p["uWeave"].value = 1
        self._apply_params()

        # --- correction textures (units 2/3) ---
        cA = load_correction(os.path.join(self.calib_dir, "3DStackCorrection_A.png"), 0)
        cB = load_correction(os.path.join(self.calib_dir, "3DStackCorrection_B.png"), 128)
        self._tA = self._tex(corr_rgb(cA), 2)
        self._tB = self._tex(corr_rgb(cB), 3)

        # --- oracle + dynamic per-vertex attribute buffer ---
        self.oracle = Oracle(self.W, self.H, parametric=parametric,
                                  fields_pkl=os.path.join(self.calib_dir, "_fields.pkl"))
        self._vbo = ctx.buffer(reserve=4 * 11 * 4, dynamic=True)
        self._ibo = ctx.buffer(_INDICES.tobytes())
        layout = [(self._vbo, "2f 2f 2f 2f 3f", "pos", "uv", "av2", "av3", "av4")]
        self._vao = ctx.vertex_array(self._prog, layout, self._ibo)
        self._vao_sbs = ctx.vertex_array(self._prog_sbs, layout, self._ibo)

        # --- library-owned offscreen output ---
        self._color = ctx.texture((self.W, self.H), 3, dtype="f1")
        self._fbo = ctx.framebuffer(color_attachments=[self._color])

        self.set_eye(*OPTPOS)

    # ---------------------------------------------------------------- internals
    def _apply_params(self):
        pr = self.params
        for p in (self._prog, self._prog_sbs):
            p["uFS"].value = float(pr.filter_slope)
            p["uXTalkFac"].value = float(pr.xtalk_fac)
            p["uXTalkDyn"].value = float(pr.xtalk_dyn)
            p["uContrast"].value = float(pr.contrast)
            p["uCorrAScale"].value = float(pr.corr_a_scale)
            p["uConv"].value = float(pr.conv)

    def _tex(self, arr, unit, filt=moderngl.LINEAR):
        t = self.ctx.texture((arr.shape[1], arr.shape[0]), 3, np.ascontiguousarray(arr).tobytes())
        t.filter = (filt, filt); t.repeat_x = False; t.repeat_y = False
        t.use(unit)
        return t

    def _upload(self, src, unit, key, filt=moderngl.LINEAR):
        """Bind `src` (moderngl.Texture or HxWx3 uint8 ndarray) to a sampler unit."""
        if isinstance(src, moderngl.Texture):
            src.use(unit); return src
        arr = np.ascontiguousarray(src)
        if arr.dtype != np.uint8 or arr.ndim != 3 or arr.shape[2] != 3:
            raise ValueError("source array must be HxWx3 uint8 (RGB)")
        h, w = arr.shape[:2]
        t = self._src_tex.get(key)
        if t is None or t.size != (w, h):
            if t is not None:
                t.release()
            t = self.ctx.texture((w, h), 3, arr.tobytes())
            t.filter = (filt, filt); t.repeat_x = False; t.repeat_y = False
            self._src_tex[key] = t
        else:
            t.write(arr.tobytes())
        t.use(unit)
        return t

    # ---------------------------------------------------------------- public API
    def set_eye(self, x: float, y: float, z: float) -> None:
        """Set the viewer's eye position (display-frame cm) and refresh the weave attributes."""
        self.oracle.set_eye(float(x), float(y), float(z))
        fa = [self.oracle.fill(nx, ny) for (nx, ny) in _NDC]   # [(v2, v3, v4), ...] for TL,TR,BL,BR
        v4min = float(int(min(min(f[2]) for f in fa)))          # reduce v4 magnitude -> sharper float32 frac
        vdata = []
        for i, (v2, v3, v4) in enumerate(fa):
            px, py, uvx, uvy = _CORNERS[i]
            vdata += [px, py, uvx, uvy, v2[0], v2[1], v3[0], v3[1],
                      v4[0] - v4min, v4[1] - v4min, v4[2] - v4min]
        self._vbo.write(np.array(vdata, dtype="f4").tobytes())

    def set_tuning(self, **kw) -> None:
        """Update scalar weave params (filter_slope, xtalk_fac, xtalk_dyn, contrast, corr_a_scale, conv)."""
        for k, v in kw.items():
            if not hasattr(self.params, k):
                raise AttributeError(f"unknown weave param {k!r}")
            setattr(self.params, k, v)
        self._apply_params()

    def weave(self, left, right, out: moderngl.Framebuffer | None = None) -> moderngl.Framebuffer:
        """Weave two separate eye views into the output framebuffer (FRAG path)."""
        fbo = out or self._fbo
        self._upload(left, 0, "L"); self._upload(right, 1, "R")
        self._tA.use(2); self._tB.use(3)
        fbo.use(); self.ctx.clear(0.0, 0.0, 0.0)
        self._vao.render()
        return fbo

    def weave_sbs(self, sbs, out: moderngl.Framebuffer | None = None, *,
                  flip: bool = False, bgr: bool = False, swap_lr: bool = True) -> moderngl.Framebuffer:
        """Weave a single side-by-side frame (left|right halves) into the output (FRAG_SCREEN path)."""
        fbo = out or self._fbo
        self._prog_sbs["uSrcFlip"] = int(flip)
        self._prog_sbs["uSrcBGR"] = int(bgr)
        self._prog_sbs["uSrcSwapLR"] = int(swap_lr)
        self._upload(sbs, 0, "sbs")
        self._tA.use(2); self._tB.use(3)
        fbo.use(); self.ctx.clear(0.0, 0.0, 0.0)
        self._vao_sbs.render()
        return fbo

    def read(self, out: moderngl.Framebuffer | None = None) -> np.ndarray:
        """Read the woven framebuffer back as an HxWx3 uint8 RGB array (top-down)."""
        fbo = out or self._fbo
        raw = fbo.read(components=3, dtype="f1")
        img = np.frombuffer(raw, dtype=np.uint8).reshape(self.H, self.W, 3)
        return np.flipud(img).copy()   # GL framebuffer is bottom-up -> top-down image

    @property
    def output(self) -> moderngl.Framebuffer:
        return self._fbo

    def release(self) -> None:
        for o in (self._vao, self._vao_sbs, self._vbo, self._ibo, self._tA, self._tB,
                  self._color, self._fbo, self._prog, self._prog_sbs):
            try: o.release()
            except Exception: pass
        for t in self._src_tex.values():
            try: t.release()
            except Exception: pass
        self._src_tex.clear()
        if self._owns_ctx:
            try: self.ctx.release()
            except Exception: pass


def standalone(panel: str = "G90XF", res: tuple[int, int] = (3840, 2160), *,
               backend: str | None = None, **kw) -> Weaver:
    """Create an offscreen GL context and a ready Weaver. Prefers headless/offscreen (no window needed); EGL on Linux, WGL on Windows."""
    if backend is not None:
        ctx = moderngl.create_standalone_context(backend=backend)
    else:
        try:
            ctx = moderngl.create_standalone_context(backend="egl")   # headless, no X
        except Exception:
            ctx = moderngl.create_standalone_context()                # GLX/X11 fallback
    wv = Weaver(ctx, panel=panel, res=res, **kw)
    wv._owns_ctx = True
    return wv
