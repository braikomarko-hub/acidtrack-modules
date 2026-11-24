"""aCiDhYb: aCiDtRacK with the hybrid OCTA303 (OCTA303 SEAM: the voice's filter, VCA and output stage on the DSP at the source seam). COMPRESSOR, LO-FI and DJ EQ given up for the DSP code (MaMarko, 19 Nov 2026). OCTA303 + dEVILish + MORPH + DISTORX + dB666 + FET76 + LOAD METER + USB AUDIO OUT (MASTER) + BRAIN (REMIX SWITCH), DARK REV the one reverb."""
from remix.schema import Proof, Remix

REMIX = Remix(
    name="acidhyb", family="mods", proof=Proof.CHECK,
    proof_note="19 Nov 2026: aCiDtRacK (V96, stradaA-1) + OCTA303 SEAM; COMPRESSOR, LO-FI and DJ EQ out (not used: dB666 is the compressor). Not yet on a unit. Before, as aCiDtRacK: 11 Nov 2026 (ACIDV91, the measurement image): STROJ, AtoMizer (and the demand loader DLPUMP/DLCOPY it needed) and KITS left out, MaMarko's call for sound and load work; OCTA303 v8.2 with a stopwatch read over USB (tools/octa303/prof). "
               "2 Nov 2026: FET76 (the 1176LN) added, FLANGER given up; FET76 bit-exact in dsp_host, not yet on the unit. "
               "27 Oct 2026: KITS added (255 Kits per project, for long live sets). "
               "26 Oct 2026: on Sam's tree of 26 Oct with MORPH v1.1, AtoMizer (loaded on demand) and LOAD METER, "
               "TAPE ECHO left out; not yet on the unit in this form. Before: ACIDV77 (24 Oct 2026, the author's MKI: "
               "OCTA303 v7.1, dEVILish, MORPH v1, DISTORX, dB666, TAPE ECHO, BRAIN) 'works perfectly'; ACIDV68..ACIDV71 "
               "(October 2026): hours of live use with two or three OCTA-303 tracks, dEVILish, DISTORX and dB666",
    doc="aCiDhYb: the hybrid OCTA303 (filter, VCA and output on the DSP) + dEVILish + MORPH (track + UP/DOWN: the scene morph by itself) + DISTORX (BOSS SD-1 + Pro Co RAT + Turbo RAT) + dB666 (side-chain from any track) + FET76 (the UREI 1176LN limiter, for the master after dB666) + LOAD METER + USB AUDIO OUT MASTER + BRAIN (FX presets from the card; switch remixes from the card); DARK REV the one reverb.",
    modules=('OCTA303', 'OCTA303 SEAM', 'DEVILISH', 'MORPH', 'STORE', 'USB', 'BRAIN', 'MEMORY', 'FILTER',
             'COMB FILTER', 'DELAY', 'DARK REV', 'DISTORX', 'DB666', 'FET76',
             'LOAD METER'),
    fx1=('FILTER', 'COMB FILTER', 'DEVILISH', 'DISTORX', 'DB666'),
    # The shared window: LOAD METER's DSP half in the gap below 0x37F00 (dB666's side-chain bus sits at Y:0x37FF8 /
    # 0x3FFF8). ACIDV91: AtoMizer and the demand loader (DLCOPY, its stub, DARK REV's guard) are out.
    window=(("LOAD METER", 0x37DA3), ("LOAD METER:B", 0x37E50)),
    fallback='NONE',
    settings={("octabam.usb", "TRACKS"): "OFF", ("octabam.usb", "MAIN"): 0,
              ("octabam.usb", "CUE"): 0, ("octabam.usb", "MASTER"): 1,
              ("octabam.usb", "IN"): "OFF", ("octabam.usb", "MIDI"): 1},
)
