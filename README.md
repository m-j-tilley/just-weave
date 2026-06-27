# just-weave

The lenticular **weave** for the Samsung Odyssey 3D (G90XF) glasses-free display, as a small reusable library.

Give it **left/right views (or a side-by-side frame) + an eye position** → it returns the **woven framebuffer** the panel expects.

- Pure Python + `moderngl` → cross-platform (Linux / Windows / macOS)
- Renders headless (offscreen, no window)
- Ships the standard G90XF calibration — works out of the box

Thanks to people over at [r/Odyssey3D](https://www.reddit.com/r/Odyssey3D/) for getting me into this glasses-free 3D-monitor stuff.

## Disclaimer

- **Unofficial.** Not produced, endorsed by, or affiliated with Samsung, Leia, or Dimenco.
- **Use at your own risk.** No warranty. It drives display hardware over a custom interface.
- Made by me with a helping of Claude Code vibes, proceed with caution.

## Install

```bash
pip install -e .          # the library + deps (moderngl, numpy, opencv-python)
# or just the deps:  pip install -r requirements.txt
```

- Needs a GL 3.3 context (any OS).
- Headless rendering needs no window (EGL on Linux, WGL on Windows).

## Use

```python
from just_weave import standalone, OPTPOS

wv = standalone(panel="G90XF")     # offscreen context + Weaver
wv.set_eye(*OPTPOS)                # eye position, display-frame cm
wv.weave_sbs(sbs_frame)            # side-by-side frame in -> woven out
woven = wv.read()                  # HxWx3 uint8 -> send to the panel
```

- Two separate eye views instead of SBS: `wv.weave(left, right)`
- Inputs accept a `moderngl.Texture` (zero-copy) or an HxWx3 uint8 numpy array
- Render into your own framebuffer: `wv.weave(..., out=fbo)`
- Head-tracked app: call `wv.set_eye(x, y, z)` each frame

Run the demo / test:

```bash
python examples/weave_image.py          # synthetic test -> weave_out.png
python examples/weave_image.py in.png out.png
pytest                                  # headless test
```

## API

| call | does |
|------|------|
| `standalone(panel="G90XF", res=(3840,2160))` | make an offscreen context + Weaver |
| `Weaver(ctx, panel="G90XF", parametric=True)` | wrap your own `moderngl` context |
| `set_eye(x, y, z)` | set eye position (cm); updates the weave |
| `weave(left, right, out=None)` | weave two views → framebuffer |
| `weave_sbs(sbs, out=None, swap_lr=True)` | weave a side-by-side frame → framebuffer |
| `read(out=None)` | woven framebuffer as HxWx3 uint8 |
| `set_tuning(**kw)` | tweak `filter_slope`, `xtalk_fac`, `contrast`, `conv` |

## How it works

- `shaders.py` — the GLSL weave (interleave + crosstalk + view separation).
- `oracle.py` — per-pixel weave attributes from eye position + panel geometry.
- `calib/G90XF/` — the standard G90XF calibration (weave field + correction textures).

## License

[MIT](LICENSE).
