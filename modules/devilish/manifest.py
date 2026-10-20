"""dEVILish -- Robin Whittle's Devil Fish mods to the TB-303, as an FX for OCTA303 tracks.

Put dEVILish on the FX1 or FX2 of an OCTA-303 track (or a FLEX track playing a TB303* sample): OCTA303's
voice reads this slot's twelve knobs from the live lane and applies them INSIDE the 303 -- in
the oscillator's level into the filter, the filter's frequency, its feedback, the envelopes and
the slide, where the mods live and where an effect after the voice cannot reach. Take dEVILish
off and the track is the 303 of v6.1.1, sample for sample. Its DSP part is a pass-through
(init and proc return at once: an in-place insert that touches no frame).

After Whittle, "User Manual for the Devil Fish mods to the TB-303" (2019); the knob laws are
tools/octa303/o3tables.py (DF_*), the voice is modules/octa303/octa303.s.

Page 1, the knobs (scene- and lock-able): OVDR FM TRCK VDEC SLID ADEC.
Page 2: SATK, then the switches SWP SPD MUFF CUTX ENVX (selects, as on the Devil Fish).
Every default is the TB-303 ("Limiting the Devil Fish to TB-303 sounds", p. 8).
"""

from remix.schema import (BusRole, Category, DspSection, Formatter, Harness, Kind, MenuEntry,
                          Module, Param, Proof, YBase)

# The FX id. OCTA303's unit compares the track's FX1/FX2 id bytes with it (DEVIL_ID in
# modules/octa303/manifest.py, through remix.inc); test_octa303 checks the two agree.
FX_ID = 0x1e

_PLAIN = Formatter.PLAIN
_STEP = Formatter.STEPPED

MODULE = Module(
    name="devilish",
    key="DEVILISH",
    kind=Kind.DSP_EFFECT,
    category=Category.TRACK,
    author="Marko Brajković", author_url="https://github.com/braikomarko-hub",
    proof=Proof.HARDWARE,
    proof_note="the owner's MKI, acidtrack images up to ACIDV71, October 2026: in daily use for days, many "
               "hours, on two or three OCTA303 tracks beside DisTorX; the Devil Fish engine is bit-exact in "
               "OCTA303's source simulator (test_octa303)",
    doc="The Devil Fish mods (Robin Whittle) for an OCTA303 track: twelve knobs read by the 303 "
        "voice; the DSP passes the audio through.",
    menu=MenuEntry(
        fx2_id=FX_ID,
        donor_desc=0x400d58b8,        # DARK REV: 12 active slots (CHARACTER's donor, on hardware)
        abbr=b"dEVL",
        fullname=b"dEVILish",
        build_tag=False,
    ),
    params=(
        # ---- page 1: the knobs ------------------------------------------------
        Param(b"OVDR", 25, 128, active=True, formatter=_PLAIN,
              doc="overdrive: the VCO into the filter, 0 none, 25 the 303, 127 66.6x (resonance swamped)"),
        Param(b"FM", 0, 128, active=True, formatter=_PLAIN,
              doc="filter FM from the VCA output (after the Muffler); 0 off, high = towards chaos"),
        Param(b"TRCK", 0, 128, active=True, formatter=_PLAIN,
              doc="filter tracking, linear in Hz up to ~2.7 kHz/oct; low notes can shut the filter"),
        Param(b"VDEC", 64, 128, active=True, formatter=_PLAIN,
              doc="volume: 0-64 decay 16 ms .. the 303's; 64-127 its final level, 127 = endless notes"),
        Param(b"SLID", 0, 128, active=True, formatter=_PLAIN,
              doc="slide time, 60 ms (0, the 303) .. 360 ms"),
        Param(b"ADEC", 50, 128, active=True, formatter=_PLAIN,
              doc="accented notes' filter decay, 30 ms .. 3 s; 50 = the 303's fixed ~200 ms"),
        # ---- page 2 ------------------------------------------------------------
        Param(b"SATK", 0, 128, active=True, formatter=_PLAIN,
              doc="soft attack of the volume on non-accented notes: 0 none, 1-127 0.3 .. 30 ms"),
        Param(b"SWP", 0, 3, active=True, formatter=_STEP, labels=("ACID", "WHST", "SELF"),
              doc="ACID the 303; WHST resonance doubled; SELF resonance doubled and no accent sweep"),
        Param(b"SPD", 1, 3, active=True, formatter=_STEP, labels=("FAST", "NORM", "SLOW"),
              doc="accent sweep speed: FAST first accent strongest, NORM the 303, SLOW up to twice"),
        Param(b"MUFF", 0, 3, active=True, formatter=_STEP, labels=("OFF", "SOFT", "HARD"),
              doc="Muffler after the VCA: the loud peaks clipped, the bass kept"),
        Param(b"CUTX", 0, 2, active=True, formatter=_STEP, labels=("OFF", "ON"),
              doc="the wide cut-off pot: lower, and up to ~5 kHz"),
        Param(b"ENVX", 0, 2, active=True, formatter=_STEP, labels=("OFF", "ON"),
              doc="env mod tripled, from none"),
    ),
    dsp=DspSection(
        asm="modules/devilish/devilish.asm",
        priority=20,
        bus_role=BusRole.NONE,        # an insert; never on the bus
        ybase=YBase.NEVER,            # no buffers
        r7_latch_slot=None,
        gate_label=None,
    ),
    harness=Harness(layout_char=None, is_server=False),
    requires=("OCTA303",),            # without the voice there is nothing to read the knobs
    dear={"OVDR": 127, "FM": 127, "TRCK": 127, "VDEC": 127, "SLID": 127, "ADEC": 127,
          "SATK": 127, "SWP": 1, "SPD": 2, "MUFF": 1, "CUTX": 1, "ENVX": 1},
)
