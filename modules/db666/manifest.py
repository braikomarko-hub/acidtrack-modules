"""dB666 -- the dbx 160 compressor/limiter (1976), with a light side-chain bus.

A per-track insert on EQUALIZER's id (0x0c), modelled from the 160's
schematic and its manual (modules/db666/README.md):

  * the detector is dbx's TRUE RMS (the RMS 208 module, M2: Blackmer's
    log-domain RMS, US 3,681,618): the mean square of the signal through one
    time constant. The manual's release rate, 125 dB/s, fixes it at
    tau = 10 log10(e)/125 = 34.7 ms, and the same tau gives the manual's
    attack times (15 / 5 / 3 ms for 10 / 20 / 30 dB) -- the 160's "attack and
    release track the program" is this detector, not a control;
  * THRESHOLD (R70) takes the threshold off the detector's dB output, a
    hard knee (the 160 has no OverEasy; the 160A's OverEasy is page 2);
  * COMPRESSION (R40 with R41/R43) sends a FRACTION k of the dB above
    threshold to the VCA (the dbx 200, M1): ratio = 1/(1 - k). k runs 0..0.992
    (1:1 .. 120:1, the 160's range) over RATI 0..100 and on to k = 2
    (-1:1, the 160A's "negative compression") over 101..127;
  * OUTPUT GAIN (R80), +-20 dB;
  * KEY: OFF (the track itself) or T1..T8, read from the SIDE-CHAIN BUS: a
    hook in the stock dispatcher (where SIDECHAIN_COMPRESSOR hooks) writes
    each track's block mean square, ONE word per track, into the shared
    window; any dB666 on either core reads the one word it needs.
Stereo-linked: one detector on (L^2 + R^2)/2, one gain for both channels.
"""
import math as _m

from remix.schema import (BusRole, Category, Claims, DspHook, DspRange, DspSection, Formatter,
                          Gate, Harness, Kind, MenuEntry, Module, Param, Proof, YBase)

FS = 44100.0


def _q(v):
    i = round(v * (1 << 23))
    i = max(-(1 << 23), min((1 << 23) - 1, i))
    return i & 0xFFFFFF


# ---- the 160 ---------------------------------------------------------------
RELEASE_DB_S = 125.0                         # the manual
TAU = 10 * _m.log10(_m.e) / RELEASE_DB_S     # 34.7 ms: the RMS detector
ALPHA = 1.0 - _m.exp(-1.0 / (FS * TAU))
THR_LO, THR_HI = -50.0, 0.0                  # dBFS RMS; the 160's 10 mV..3 V span (49.5 dB)
OUT_DB = 20.0                                # R80: +-20 dB
K_160 = 0.992                                # 120:1 at RATI 100
RATI_160 = 100                               # RATI above this: the 160A's beyond-infinity
KNEE_DB = 10.0                               # ASSUMED OverEasy width (the 160A's page-2 KNEE)
DB_PER_BIT = 10 * _m.log10(2.0)              # 3.0103 dB per bit of MEAN SQUARE

# ---- the side-chain bus ------------------------------------------------------
# One word per track, the block's mean square (L^2 + R^2)/2 over 16 frames, in
# the last words of each core's half of the shared window. Payload A writes
# tracks 5-8 at $33ff8.., payload B tracks 1-4 at $3bff8..; any core reads
# track t (0-based) at $3bff8 + t (t < 4) or $33ff4 + t (t >= 4). Inside the
# region SIDECHAIN_COMPRESSOR measured as never written by stock code (its
# last $202 words of each half) and zeroed by each payload's own init.
BUS_A, BUS_B = 0x33FF8, 0x3BFF8

# P table: LOG[i] = log2(0.5 + i/64)/32 (33), EXP[i] = 2^(i/32)/2 (33; the
# last is 1.0, held at full scale).
LOG = tuple(_q(_m.log2(0.5 + i / 64) / 32) for i in range(33))
EXP = tuple(_q(2.0 ** (i / 32) / 2) for i in range(33))
EXP_AT = len(LOG)
PTABLE = LOG + EXP

W32 = KNEE_DB / DB_PER_BIT / 32               # the knee width, MS bits / 32
CONST = {
    "ALPHA": ALPHA,
    # THRS: T/32 in MS bits = THLO + x * THSPAN
    "THLO": THR_LO / DB_PER_BIT / 32,
    "THSPAN": (THR_HI - THR_LO) / DB_PER_BIT / 32,
    # RATI: k/2 = w * K1 (w <= 100/128); beyond: 1/2 + (w - 100/128) * K2H * 4
    "K1": K_160 * 128 / RATI_160 / 2,
    "WRAT": RATI_160 / 128,
    "K2Q": 128 / (127 - RATI_160) / 2 / 4,
    # OUT: amp bits/32 = (w - 1/2) * OUTK, w = knob/128 (64 -> 0 dB, 127 -> +19.8 dB)
    "OUTK": 128 * OUT_DB / 63.5 / (20 * _m.log10(2.0)) / 32,
    "W2": W32 / 2,
    "W32": W32,
    "IW8": 1.0 / (2 * W32) / 8,               # d^2/(2W) in /32 units: x 1/(2W), stored /8
    "TMIN": -0.5,                             # -16 bits of amplitude (-96 dB)
    "TMAX": 0.125,                            # +4 bits (+24 dB)
    "STRETCH": 1.0 / 127.0,
}
CONSTQ = {k: _q(v) for k, v in CONST.items()}
CONSTQ.update(EXP_AT=EXP_AT)

_P = Formatter.PLAIN
_B = Formatter.BIPOLAR

MODULE = Module(
    name="db666",
    key="DB666",
    kind=Kind.DSP_EFFECT,
    category=Category.TRACK, author="Marko Brajković", author_url="https://github.com/braikomarko-hub",
    proof=Proof.HARDWARE,
    proof_note="the owner's MKI, acidtrack images from 11 Oct 2026 to ACIDV71 (20 Oct): side-chain ducking by ear, "
               "hours of live use beside OCTA303, dEVILish and DISTORX; make check passed on the owner's tree. "
               "Bit-exact against its fixed-point model (verify_db666)",
    doc="A model of the dbx 160 compressor: true-RMS detector, threshold, ratio to infinity and beyond, side-chain KEY from any track.",
    menu=MenuEntry(
        fx2_id=0x0c,
        replaces="EQUALIZER",
        donor_desc=0x400d58b8,        # DARK REV: 12 active slots
        abbr=b"d666",
        fullname=b"dB666",
        build_tag=False,
    ),
    params=(
        Param(b"THRS", 96, 128, active=True, formatter=_P,
              doc="THRESHOLD: -50 dBFS (0) .. 0 dBFS (127) RMS, the 160's 49.5 dB span"),
        Param(b"RATI", 50, 128, active=True, formatter=_P,
              doc="COMPRESSION: 0 = 1:1, 50 = 2:1, 75 = 4:1, 100 = 120:1 (inf), 127 = -1:1"),
        Param(b"OUT", 64, 128, active=True, formatter=_B,
              doc="OUTPUT GAIN: -20 .. +20 dB, 0 = unity"),
        Param(b"KEY", 0, count=9, active=True, formatter=Formatter.WIDE_STEPPED,
              labels=("OFF", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"),
              doc="the detector's source: OFF = this track, T1..T8 = that track (the bus)"),
        Param(b"MIX", 127, 128, active=True, formatter=_P,
              doc="dry/wet: 127 = the 160 alone, 0 = exact passthrough (parallel compression between)"),
        Param(b"", 0),
        Param(b"KNEE", 0, count=2, active=True, formatter=Formatter.STEPPED,
              labels=("HARD", "OVER"),
              doc="HARD = the 160's knee; OVER = the 160A's OverEasy (10 dB wide, assumed)"),
        Param(b"", 0), Param(b"", 0), Param(b"", 0), Param(b"", 0), Param(b"", 0),
    ),
    dsp=DspSection(
        asm="modules/db666/db666.asm",
        ptable=PTABLE,
        priority=19,
        bus_role=BusRole.NONE,
        ybase=YBase.NEVER,
        r7_latch_slot=None,
        gate_label=None,
        hooks=(
            # SIDECHAIN_COMPRESSOR's `sctap` site: the dispatcher's FX1 entry,
            # every track, every block, the track's audio at X:0..$1f. The
            # displaced `move x:>$208,r6` is replayed at the end of dbt_tap.
            DspHook({"A": 0x004a7, "B": 0x0029c}, (0x66f000, 0x000208), "dbt_tap",
                    "dispatcher: publish every track's block mean square, one word"),
        ),
        subst={
            "A": {"@COREBASE@": "4", "@SBASE@": "$33ff8"},
            "B": {"@COREBASE@": "0", "@SBASE@": "$3bff8"},
        },
    ),
    claims=Claims(dsp_ranges=(
        DspRange("y", 0x3FF8, 0x8, "the side-chain bus: one word per track, "
                                   "four per core's half", half_relative=True),
    )),
    harness=Harness(layout_char=None, is_server=False),
    gates=(Gate("tools/verify/verify_db666.py", remix_arg=False),),
    dear={"THRS": 0, "RATI": 127, "OUT": 127, "KEY": 5, "MIX": 127, "KNEE": 1},
)
