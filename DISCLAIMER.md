# Disclaimer & interoperability notice

**Use at your own risk.** Provided "as is", without warranty of any kind (see the [MIT License](LICENSE)).
You are solely responsible for how you use it.

## Not affiliated

Independent project, built by me (with the help of Claude Code). **Not** produced, endorsed, or supported
by Samsung, Leia, Dimenco, or any display vendor. "Samsung", "Odyssey", and "G90XF" are used only to state
factual hardware compatibility (nominative use); no affiliation or endorsement is implied. No vendor logos
or trademarks are included.

## What this is

The lenticular **weave** — the math that interleaves a side-by-side pair into the sub-pixel pattern the
Samsung Odyssey 3D (G90XF) lens needs — was produced by **reverse-engineering for interoperability**:
making independently-written software work with hardware **you own**, on an operating system the
manufacturer does not officially support. It is an independent re-implementation, not vendor source code.

## What it ships

To weave correctly for the G90XF, this library ships **captured calibration data**: the weave field
(`calib/G90XF/_fields.pkl`) and the stack-correction textures (`calib/G90XF/3DStackCorrection_*.png`).
These were **captured once for interoperability** from the panel's weave pipeline and ship as the standard
set because the G90XF is the same across units.

This is **calibration data, not code** — no vendor binaries, firmware, source, models, logos, or trademarks
are included. Replicating captured calibration data may carry legal considerations depending on your
jurisdiction; **you are responsible for lawful use where you live**, and I will remove anything a
rights-holder asks me to.
