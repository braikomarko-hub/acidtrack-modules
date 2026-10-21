# aCiDtRacK modules for octabam

Acid on the Elektron Octatrack MKI: a TB-303 voice, the Devil Fish mods and a distortion
pedal, as modules for [octabam](https://github.com/sambanks/octabam), Sam Banks' remixer for
the Octatrack's OS 1.40C.

| module | kind | what it is | proven |
|---|---|---|---|
| [`octa303`](modules/octa303/README.md) | ColdFire | **OCTA-303**: a circuit-modelled TB-303 voice, one per track, as a machine of its own (FUNC + SRC → OCTA-303). Calibrated against Din Sync's recordings of a real TB-303. Runs on the ColdFire, so it leaves the DSP to the effects (unlike Zac Kyoti's DSP-based BLACKPYRAMIDS_303, see its README). | the author's MKI |
| [`devilish`](modules/devilish/README.md) | DSP FX (with `octa303`) | **dEVILish**: Robin Whittle's Devil Fish modifications for OCTA-303 tracks (filter FM, MUFF, sweep, slide, accent) | the author's MKI |
| [`distorx`](modules/distorx/README.md) | DSP insert | **DISTORX**: BOSS SD-1, Pro Co RAT and Turbo RAT in one insert, MODE picks the pedal | the author's MKI |
| [`db666`](modules/db666/README.md) | DSP insert + side-chain bus | **dB666** (decibels and the Devil; formerly DBX 160): a model of the dbx 160 compressor (1976) from its schematic, true-RMS detector, ratio to infinity and beyond, KEY from any track over a one-word-per-track bus | the author's MKI |

The [`acidtrack`](remixes/acidtrack/README.md) remix puts them all together (with USB AUDIO OUT
on MASTER and DARK REV as the one reverb): the author's live set.

## Status

These modules are **not (yet) part of octabam**. A pull request to
[sambanks/octabam](https://github.com/sambanks/octabam) is planned; until it is merged, this
repository is where they live. The same files are on the branch
[`acidtrack-modules`](https://github.com/braikomarko-hub/octabam/tree/acidtrack-modules) of
the author's octabam fork.

Tested on one Octatrack MKI, OS 1.40C (October 2026): hours of playing with two or three
OCTA-303 tracks, dEVILish and DISTORX, image `ACIDV71`, dB666 (as DBX 160) since 11 Oct 2026. **Use at your own risk** and keep your
stock OS image and a way back (the Startup Menu's OS upgrade over MIDI/USB).

## Using them

You need a working octabam checkout and your own stock 1.40C image (octabam's `README.md` and
`docs/guide/` explain the setup). No Elektron byte is in this repository: the image is always
built from your own.

1. Copy the folders of this repository into your octabam folder, keeping the paths
   (`modules/…`, `tools/…`, `remixes/…`).
2. Add the modules to a remix (`remixes/<name>/remix.py`, `modules=(…, 'OCTA303', 'DEVILISH',
   'DISTORX')`), or try `remixes/test/octa303` (OCTA303 alone).
3. `make docs`, then `make check REMIX=<name>`, then `make bus REMIX=<name>` and flash as
   octabam describes.

Notes for the octabam of 20 October 2026:

- `octa303` cannot share an image with `analog-bassdrum`, `blackpyramids-303` or SYNTH MACHINE
  (same seams); `db666` cannot share one with SIDECHAIN_COMPRESSOR (same hook and words) and
  takes EQUALIZER's id.
- FX ids: `distorx` `0x0a`; `devilish` `0x10`, PHASER's, which it replaces on both menus (as
  `db666` replaces EQUALIZER): since RESONATOR took `0x1e` (21 Oct 2026) every non-stock FX2 id
  is a module's. octabam's `tools/remix/selftest.py` needs `"octa303": ()` and the acidtrack
  line in its harvest table.
- dEVILish was on `0x1f` before 20 Oct 2026 and on `0x1e` until 21 Oct; DISTORX was on `0x1b`
  before 20 Oct: a part saved with an old id needs the effect chosen again on its tracks.

## Credits and sources

Author: MaMarko (Marko Brajković, [braikomarko-hub](https://github.com/braikomarko-hub)): the idea, the listening and the tests on the unit.
**The code was written by Claude (Anthropic)**: engines, calibration, integration and gates.
Each module's README separates what was measured from what is inferred.

- **Sam Banks**, [octabam](https://github.com/sambanks/octabam) (MIT): the remixer, the build,
  the emulator port and the gates these modules are checked with.
- **Tim Hastie**, SYNTH MACHINE in
  [octatrick-modules](https://github.com/timhastie/octatrick-modules) (MIT, © 2026 Tim
  Hastie): the FLEX renderer integration OCTA303 follows for one voice, and the semitone tuning.
- **repeat98** (Jannik Aßfalg), [`analog-bassdrum`](https://github.com/repeat98) in octabam:
  the measured machine-list seams the OCTA-303 row uses.
- **Din Sync**, [TB-303 reference recordings for x0xb0x](http://www.dinsync.info/2010/02/tb-303-reference-recordings-for-x0xb0x.html):
  the calibration target.
- **tinyloops**, [Programming the Roland TB-303](https://tinyloops.com/tb303/index.html):
  example recordings for the resonance and the accent.
- **Robin Whittle**, [Devil Fish](https://www.firstpr.com.au/rwi/dfish/) (Real World
  Interfaces): the Devil Fish modifications and the TB-303 notes (gate length, accent and slide
  RC values).
- **Tim Stinchcombe**, [TB-303 diode ladder analysis](https://www.timstinchcombe.co.uk/index.php?pge=diode2).
- **dbx**, 160/161 manual and schematic, 160A cut sheet; **D. E. Blackmer**, US 3,681,618 (the
  RMS detector).
- **Zac Kyoti**, SIDECHAIN_COMPRESSOR in
  [octatrack-kyoti-fw](https://github.com/Zac-Kyoti/octatrack-kyoti-fw) (MIT): the dispatcher
  hook site and the shared-window words dB666's bus uses, measured on an MKI.
- **Roland**, TB-303 service notes; **BOSS**, SD-1 service notes; **Pro Co**, RAT schematics
  (as documented by ElectroSmash's RAT analysis).

TB-303, BOSS, SD-1, RAT, Devil Fish, dbx and Octatrack are trademarks of their owners; these
modules are independent models and are not affiliated with or endorsed by them.

## License

MIT, © 2026 Marko Brajković (`LICENSE`).
