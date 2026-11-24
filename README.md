# aCiDtRacK modules for octabam

Acid on the Elektron Octatrack MKI: a TB-303 voice, the Devil Fish mods, pedals, compressors, a
granular delay, a drone machine and a scene morph, as modules for
[octabam](https://github.com/sambanks/octabam), Sam Banks' remixer for the Octatrack's OS 1.40C.

This repository is the **showcase**: every module the author has made, in one place, with its
status. The folders below hold the versions in the author's newest images (24 Nov 2026). Several
modules are also part of octabam itself; there, octabam's copy is the one to build with.

Author: MaMarko (Marko Brajković, [braikomarko-hub](https://github.com/braikomarko-hub)): the
ideas, the listening and the tests on the unit. **The code was written by Claude (Anthropic)**:
engines, calibration, integration and gates. Each module's README separates what was measured
from what is inferred.

## The modules

| module | kind | what it is | in octabam | on the unit |
|---|---|---|---|---|
| [OCTA303](modules/octa303/README.md) | ColdFire machine | **OCTA-303**: a circuit-modelled TB-303 voice, one per track, a machine of its own (FUNC + SRC → OCTA-303), calibrated against Din Sync's recordings of a real TB-303 | ✅ [`octa303`](https://github.com/sambanks/octabam/tree/main/modules/octa303) (an older version than this folder's) | ✅ |
| [OCTA303 SEAM](modules/octa303-seam/README.md) | hybrid (ColdFire + DSP) | the hybrid OCTA-303: the ColdFire keeps the knobs, the envelopes and the VCO; the DSP renders the filter, the VCA and the output at the track's source seam | — | ✅ image ACIDV97 (20 Nov 2026) |
| [dEVILish](modules/devilish/README.md) | DSP FX, with OCTA303 | Robin Whittle's Devil Fish modifications for OCTA-303 tracks: filter FM, MUFF, sweep, slide, accent | ✅ [`devilish`](https://github.com/sambanks/octabam/tree/main/modules/devilish) | ✅ |
| [DISTORX](modules/distorx/README.md) | DSP insert | BOSS SD-1, Pro Co RAT and Turbo RAT in one insert; MODE picks the pedal | ✅ [`distorx`](https://github.com/sambanks/octabam/tree/main/modules/distorx) | ✅ near-daily use |
| [dB666](modules/db666/README.md) | DSP insert + side-chain bus | a model of the dbx 160 compressor (1976) from its schematic, KEY from any track | ✅ as [`vca160`](https://github.com/sambanks/octabam/tree/main/modules/vca160) (VCA160, KEY over KEYBUS) | ✅ |
| [FET76](modules/fet76/README.md) | DSP insert | a model of the UREI 1176LN FET limiter (1967) from its manual, for the master | ✅ [`fet76`](https://github.com/sambanks/octabam/tree/main/modules/fet76) | ✅ |
| [AtoMizer](modules/atomizer/README.md) | DSP FX2 | a granular delay after the Red Panda Particle (re-derived from its manual) | — | ✅ ACIDV79 (27 Oct 2026); out of the newest remix |
| [MORPH](modules/morph/README.md) | ColdFire | a track's scene morph played by itself, at the tempo; v1.2 adds the way back (RET, CURV, END: risers that come back "as if by hand") | ✅ [`morph`](https://github.com/sambanks/octabam/tree/main/modules/morph), with v1.1 and v1.2 | v1.1 ✅; v1.2 is in the image on the unit since 23 Nov 2026 (ACIDF10) |
| [STROJ](modules/stroj/README.md) | ColdFire machine | a drone machine: four plates with cross phase modulation (after SOMA's Lyra-8) and two sub-octaves (after Moog's Subharmonicon) | — | ✅ ran on the author's MKI (reported by the author, 24 Nov 2026); its cost is not measured there |

OCTA303 SEAM also needs OCTA303; dEVILish works on OCTA-303 tracks; MORPH needs octabam's STORE.

## The remixes

- [`acidhyb`](remixes/acidhyb/README.md): aCiDtRacK with the hybrid OCTA-303 (OCTA303 SEAM): images
  ACIDV97, then ACIDV98 with MORPH v1.2.
- At the time of writing (24 Nov 2026) the author's unit runs a vFable test image, ACIDF10 (see
  "Shelved or elsewhere").
- [`acidtrack`](remixes/acidtrack/README.md): aCiDtRacK, the author's live set.
- `remixes/test/…`: one module each, for its gates.

## Shelved or elsewhere

Made, tried, and set aside (or kept on their own branch of the author's octabam fork). They are
not copied here; the links go to the branch where each one lives.

| what | where | status |
|---|---|---|
| TRACK MENU (ACID BUCKET), v1 and v2 | [`trackmenu`](https://github.com/braikomarko-hub/octabam/tree/trackmenu), [`trackmenu-v2`](https://github.com/braikomarko-hub/octabam/tree/trackmenu-v2) | v2 tried on the unit, shelved (25 Oct 2026) |
| ERGOSUM (a Cartesian sequencer) and EuKlé (Euclidean modes) | [`ergosum-v1`](https://github.com/braikomarko-hub/octabam/tree/ergosum-v1), inside `trackmenu-v2` | shelved (25 Oct 2026) |
| BOOT_SMILE (an acid smiley at power-on) | [`trackmenu`](https://github.com/braikomarko-hub/octabam/tree/trackmenu) | made, kept for a final image |
| MORPH LOCK page (recorded knob values as bars) | [`morph-lock`](https://github.com/braikomarko-hub/octabam/tree/morph-lock) | emulator only |
| MORPH v2 | [`morph-v2`](https://github.com/braikomarko-hub/octabam/tree/morph-v2) | shelved (26 Oct 2026) |
| vFable, a second OCTA303 engine (developed separately) with its own hybrid: with dEVILish on FX1 of an OCTA-303 track, the filter, the VCA, DRIV, MUFF, FM and SWP run on the DSP inside dEVILish (a 640-word insert); without dEVILish on FX1, or with it on FX2, the voice runs on the ColdFire as before | branch [`octa303_optimus_23`](https://github.com/braikomarko-hub/octabam/tree/octa303_optimus_23) of the fork (earlier: `octa303-fable-*`) | work in progress. Test images ACIDF08 (19 Nov 2026) and ACIDF10 (23 Nov 2026) have run on the author's MKI. Measured on ACIDF10 with octabam's LOAD METER: a dEVILish voice slot costs 277 cycles a sample (6.1 % of a frame). Known in ACIDF10: with FM on, some frames are refused and come out silent (fixed on the branch, not yet on the unit); notes held by a chain of slides sometimes close early (also in older images; open) |

## Using them

You need a working octabam checkout and your own stock 1.40C image (octabam's `README.md` and
`docs/guide/` explain the setup). **No Elektron byte is in this repository**: the image is always
built from your own.

1. For a module that is in octabam, use octabam's copy.
2. For the others, copy the folders of this repository into your octabam folder, keeping the
   paths (`modules/…`, `tools/…`, `remixes/…`). They were last built on the author's fork (branch
   [`morph-v1.2`](https://github.com/braikomarko-hub/octabam/tree/morph-v1.2), on octabam of
   mid-November 2026); a newer octabam may need small changes.
3. `make docs`, then `make check REMIX=<name>`, then `make bus REMIX=<name>`, and flash as
   octabam describes.

Tested on one Octatrack MKI, OS 1.40C. **Use at your own risk**, and keep your stock OS image and
a way back (the Startup Menu's OS upgrade).

## Credits and sources

- **Sam Banks**, [octabam](https://github.com/sambanks/octabam) (MIT): the remixer, the build,
  the emulator port and the gates these modules are checked with; STORE, HOOKS, KEYBUS.
- **Tim Hastie**, SYNTH MACHINE in
  [octatrick-modules](https://github.com/timhastie/octatrick-modules) (MIT, © 2026 Tim
  Hastie): the FLEX renderer integration OCTA303 follows for one voice, and the semitone tuning.
- **repeat98** (Jannik Aßfalg), `analog-bassdrum` in octabam: the machine-list seams the
  OCTA-303 row uses, and the source seam OCTA303 SEAM uses.
- **Zac Kyoti**, [octatrack-kyoti-fw](https://github.com/Zac-Kyoti/octatrack-kyoti-fw) (MIT):
  SIDECHAIN_COMPRESSOR's dispatcher hook and shared-window words, which dB666's bus uses.
- **Din Sync**, [TB-303 reference recordings for x0xb0x](http://www.dinsync.info/2010/02/tb-303-reference-recordings-for-x0xb0x.html):
  the calibration target.
- **tinyloops**, [Programming the Roland TB-303](https://tinyloops.com/tb303/index.html).
- **Robin Whittle**, [Devil Fish](https://www.firstpr.com.au/rwi/dfish/) (Real World
  Interfaces): the Devil Fish modifications and the TB-303 notes.
- **Tim Stinchcombe**, [TB-303 diode ladder analysis](https://www.timstinchcombe.co.uk/index.php?pge=diode2).
- **dbx**, 160/161 manual and schematic; **D. E. Blackmer**, US 3,681,618.
- **UREI / Universal Audio**, 1176LN manual.
- **Red Panda**, Particle 2 owner's manual and changelog (no Red Panda code or firmware used).
- **SOMA Laboratory** (Lyra-8) and **Moog** (Subharmonicon): the instruments STROJ is after.
- **Roland**, TB-303 service notes; **BOSS**, SD-1 service notes; **Pro Co**, RAT schematics.

Each module's README has its own sources in full.
