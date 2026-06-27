"""
weave_image.py — headless demo: side-by-side image + eye position -> woven PNG.

Runs with NO X display (offscreen EGL on NVIDIA). Either pass an SBS image, or run with no args to
weave a synthetic red-left / green-right test pattern (handy as a test / "does it run here").

    python examples/weave_image.py                      # synthetic red|green -> weave_out.png
    python examples/weave_image.py my_sbs.png out.png   # weave an SBS image
"""
import sys
import numpy as np
from PIL import Image

from just_weave import standalone, OPTPOS


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    out = sys.argv[2] if len(sys.argv) > 2 else "weave_out.png"

    wv = standalone(panel="G90XF")               # headless EGL context + Weaver
    print("GL renderer:", wv.ctx.info.get("GL_RENDERER"))
    wv.set_eye(*OPTPOS)                           # sweet-spot eye (display-frame cm)

    if src:
        sbs = np.asarray(Image.open(src).convert("RGB"))
        wv.weave_sbs(sbs)                         # left|right halves split on the GPU
    else:
        # synthetic full-SBS: left half red, right half green
        W, H = wv.W, wv.H
        sbs = np.zeros((H, W, 3), np.uint8)
        sbs[:, : W // 2, 0] = 220                 # left view = red
        sbs[:, W // 2 :, 1] = 220                 # right view = green
        wv.weave_sbs(sbs, swap_lr=True)

    woven = wv.read()                             # HxWx3 uint8, top-down
    Image.fromarray(woven).save(out)
    print(f"wrote {out}  ({woven.shape[1]}x{woven.shape[0]})  "
          f"mean={woven.reshape(-1,3).mean(0).round(1).tolist()}")
    # a correct weave is a fine vertical interlace -> large horizontal neighbour differences
    hf = np.abs(np.diff(woven[:, :, 1].astype(np.int16), axis=1)).mean()
    print(f"horizontal-neighbour diff (interlace strength): {hf:.2f}")
    wv.release()


if __name__ == "__main__":
    main()
