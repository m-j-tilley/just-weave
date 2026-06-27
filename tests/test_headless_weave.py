"""Headless test: a G90XF weave runs offscreen and produces a fine vertical interlace."""
import numpy as np
import pytest

from just_weave import standalone, OPTPOS


@pytest.fixture(scope="module")
def weaver():
    try:
        wv = standalone(panel="G90XF")
    except Exception as e:                       # no GL context available (e.g. CI without EGL/GPU)
        pytest.skip(f"no offscreen GL context: {e}")
    yield wv
    wv.release()


def test_sbs_weave_interlaces(weaver):
    W, H = weaver.W, weaver.H
    sbs = np.zeros((H, W, 3), np.uint8)
    sbs[:, : W // 2, 0] = 220        # left = red
    sbs[:, W // 2 :, 1] = 220        # right = green
    weaver.set_eye(*OPTPOS)
    weaver.weave_sbs(sbs, swap_lr=True)
    woven = weaver.read()

    assert woven.shape == (H, W, 3)
    assert woven.dtype == np.uint8
    # the woven frame must carry both views' colours...
    assert woven[:, :, 0].mean() > 5 and woven[:, :, 1].mean() > 5
    # ...interleaved as a fine vertical pattern -> strong horizontal neighbour differences
    hdiff = np.abs(np.diff(woven[:, :, 1].astype(np.int16), axis=1)).mean()
    assert hdiff > 5.0, f"expected an interlace (high horizontal diff), got {hdiff:.2f}"


def test_two_texture_weave(weaver):
    W, H = weaver.W, weaver.H
    left = np.zeros((H, W, 3), np.uint8);  left[..., 0] = 200
    right = np.zeros((H, W, 3), np.uint8); right[..., 2] = 200
    weaver.set_eye(*OPTPOS)
    weaver.weave(left, right)
    woven = weaver.read()
    assert woven.shape == (H, W, 3)
    assert woven[:, :, 0].mean() > 5 or woven[:, :, 2].mean() > 5
