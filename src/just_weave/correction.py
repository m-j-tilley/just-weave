"""
correction.py — load the panel's 3DStackCorrection_A/B weave-correction textures.

These two grayscale images are sampled by the weave shader (uCorrA / uCorrB). If a file is missing
they fall back to a NEUTRAL constant so the geometric weave still runs (uncalibrated): fill=0 for A
(corrA = 0) and fill=128 for B (corrB ~= 0.5) make the correction terms vanish.
"""
import os
import numpy as np
import cv2


def load_correction(path, fill):
    """Load a 3DStackCorrection_* image, or a neutral constant if it's absent."""
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None:
        print(f"[weaver] {os.path.basename(path)} missing -> neutral correction (uncalibrated)", flush=True)
        return np.full((64, 64), fill, np.uint8)
    return im


def corr_rgb(im):
    """Normalize a correction image to contiguous RGB uint8 (16->8 bit, gray/BGRA/BGR -> RGB)."""
    if im.dtype == np.uint16:
        im = (im / 257).astype(np.uint8)
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2RGB)
    elif im.shape[2] == 4:
        im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGB)
    else:
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    return np.ascontiguousarray(im.astype(np.uint8))
