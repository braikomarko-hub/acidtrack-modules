"""OCTA303 SEAM -- the hybrid OCTA303: the ColdFire keeps the knobs, the sequencer, the envelopes, the accent, the
slide and the VCO; the DSP renders the rest of the voice (the resonance loop, the ladder, the VCA pair, the level,
the OTA, the VCA, pin 6, the output coupling) at the per-track source seam, before the stock AMP, FX1 and FX2.

The seam is ANALOG BD's (modules/analog-bassdrum/ab_glue.asm): the stock `move a,x:>$20e` before the source
(payload A P:0x39c, B P:0x1a2) becomes a jsr into o3h.asm.  A track whose source record carries the signature
($a303 / $0303) is rendered by o3h into X:0, and the stock code continues after the source (A P:0x426, B P:0x221);
any other record returns into the stock source untouched.  octa303.s writes the record when its remix.inc has
O3_SEAM = 1 (modules/octa303/manifest.py) and the voice has no FM, no MUFF, no DIST carrier and DRIV 0; any other
voice plays on the ColdFire as before.  The record's format: tools/octa303/ibrido3/hyb.py.

o3h.asm is generated (tools/octa303/ibrido3/gen_o3h.py; the build does not regenerate it): integer-exact against
ref303, instruction forms with a stock site or a CHIP.md register row only.  Pin 6's two tables are its ptable.
"""
import os
import sys

from remix.schema import Category, Claims, DspHook, DspRange, DspSection, Kind, Module, Proof

_HERE = os.path.relpath(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "tools", "octa303"))
import o3tables as _T  # noqa: E402

PTABLE = tuple(int(v) & 0xFFFFFF for v in list(_T.P6_F) + list(_T.P6_FP))

MODULE = Module(
    name="octa303-seam",
    key="OCTA303 SEAM",
    kind=Kind.HYBRID,
    category=Category.MACHINES,
    author="MaMarko",
    author_url="https://github.com/braikomarko-hub",
    requires=("OCTA303",),
    doc=("The hybrid OCTA-303: the voice's filter, VCA and output stage run on the DSP at the track's source, "
         "the rest on the ColdFire; FM, MUFF, a DIST carrier and DRIV play on the ColdFire as before."),
    proof=Proof.CHECK,
    proof_note=("19 Nov 2026: the DSP half on the dsp56300 emulator from the seam's jsr, 956,560 frames (the judge's "
                "208 half-A notes, 120 random runs, 40 with dEVILish), 0 differing samples against ref303, both payloads; "
                "the ColdFire half in cfsim, record for record against tools/octa303/ibrido3/hyb.py. Not yet on a unit."),
    claims=Claims(dsp_ranges=(
        DspRange("x", 0x7C00, 0x40, "the four voices' state words (16 a voice, x:$418 / 2), in stock's unreferenced "
                                    "X:$7a92-$7fff (no DMA in its 8K block)"),
        DspRange("x", 0x7C40, 0x0C, "the piece's control block, decoded from the record"),
    )),
    dsp=DspSection(
        asm=os.path.join(_HERE, "o3h.asm"),
        priority=32,
        payloads=frozenset({"A", "B"}),
        ptable=PTABLE,
        hooks=(DspHook({"A": 0x39C, "B": 0x1A2}, (0x567000, 0x00020E), "oh01s",
                       "the per-track source seam: a signed OCTA303 record renders the voice into X:0 and continues "
                       "after the source"),),
    ),
)
