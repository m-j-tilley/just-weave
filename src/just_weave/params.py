"""
params.py — the weave's scalar tuning parameters (shader uniform defaults).

These are the standard G90XF values. You normally don't touch them; `conv`/`contrast` are the only
ones you might tweak at runtime (via Weaver.set_tuning). The crosstalk + FilterSlope values are part
of the calibrated weave.
"""
from dataclasses import dataclass


@dataclass
class WeaveParams:
    filter_slope: float = 10.0      # uFS    — FilterSlope triangle width (view separation sharpness)
    xtalk_fac:    float = 0.012853500433266163  # uXTalkFac  — static crosstalk pre-distortion factor
    xtalk_dyn:    float = 0.0        # uXTalkDyn — eye-angle-dependent crosstalk term (0 = off)
    contrast:     float = 1.0        # uContrast — per-view contrast about mid-grey
    corr_a_scale: float = 1.0        # uCorrAScale — scale on the A correction texture
    conv:         float = 0.0        # uConv  — horizontal convergence shift (keep 0 for the calibrated weave)
