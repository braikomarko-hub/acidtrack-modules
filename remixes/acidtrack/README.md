# acidtrack

aCiDtRacK, MaMarko's (Marko Brajković's) live set on the Octatrack MKI: OCTA303 (the OCTA-303 machine),
dEVILish (Devil Fish), MORPH (the scene morph by itself, saved with the project; it needs STORE), DISTORX (SD-1 / RAT /
Turbo RAT), dB666 (side-chain from any track), FET76 (the UREI 1176LN limiter, for the master), LOAD METER, USB
(MIDI and AUDIO OUT MASTER) and BRAIN (FX presets from the card; it carries REMIX SWITCH); DARK REV is the one reverb.
PLATE REV, SPRING REV, CHORUS, PHASER, SPATIALIZER, EQUALIZER and FLANGER are given up: DISTORX takes SPATIALIZER's
id, dEVILish PHASER's, dB666 EQUALIZER's, FET76 a new id (0x1d), and their DSP words come from the others. FLANGER went
(2 Nov 2026) because its 289 words sat between the two harvested runs: without it they join into one
of 2,782 words, the only way FET76's 549 (table and code) fit beside DISTORX and dB666. A saved Part
with FLANGER on a track plays that slot as NONE (fallback), as with the effects given up before.

**11 Nov 2026 (ACIDV91): STROJ, AtoMizer, the demand loader it needed (DLPUMP, DLCOPY, the DARK REV guard) and KITS
are out**, the author's call to give OCTA303 the ColdFire and the shared window for the sound and load work. A
project saved with AtoMizer on a slot plays it as NONE; one saved with KITS keeps its `kits.work` on the card,
unread. The image also carries OCTA303's stopwatch: per track, the render call's time on DMA timer 3, read over
USB with `tools/octa303/prof/o3prof.py` (block 4 of the USB module's `0xc0/0x57`).

The master chain the author's projects use: **T8 FX1 = dB666 (GLUE), T8 FX2 = FET76** (20:1, ATK 110,
REL 80, INPT 47, OUTP 89 as a starting point, about 3 dB louder with the peaks caught).

## Where it has run

- ACIDV77 (24 Oct 2026, with TAPE ECHO and MORPH v1, on an older tree): on the author's MKI, "works perfectly".
- ACIDV68..ACIDV71 (October 2026): hours of live use.
- This form (26–27 Oct 2026: MORPH v1.1, AtoMizer (lighter), LOAD METER, KITS, TAPE ECHO left out): not yet on the unit.
- With FET76 and without FLANGER (2 Nov 2026, ACIDV82): FET76 bit-exact in dsp_host; not yet on the unit.
- ACIDV91 (11 Nov 2026, without STROJ, AtoMizer, the demand loader and KITS; OCTA303 v8.2 with the stopwatch): not yet on the unit.
