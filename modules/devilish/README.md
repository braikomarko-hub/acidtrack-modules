# `devilish` — dEVILish

Robin Whittle's **Devil Fish** modifications to the TB-303, as an FX for [`octa303`](../octa303/README.md)
tracks. Put dEVILish on FX1 or FX2 of an OCTA-303 track:
the 303 voice reads this slot's twelve knobs and applies them **inside** the voice — the oscillator's
level into the filter, the filter's frequency and feedback, the envelopes, the slide — where the
mods live and where an effect after the voice cannot reach. Take dEVILish off and the voice is the
plain TB-303, sample for sample. On any other track it does nothing.

Author: MaMarko (Marko Brajković, [braikomarko-hub](https://github.com/braikomarko-hub)): the idea, the listening and the tests on the unit.
**The code was written by Claude (Anthropic)**: engine, calibration, integration and gates.
Markers as in `CHIP.md`: ✅ measured, 🟡 inferred.

## Knobs

Every default is the TB-303 (Whittle, "Limiting the Devil Fish to TB-303 sounds"). Page 1 can be
locked, morphed by scenes and the crossfader and modulated by the track's LFOs, as any effect's knobs
(page 2 has no LFO destinations on any effect).

| page | name | range | default | what it does |
|---|---|---|---|---|
| 1 | OVDR | 0..127 | 25 | overdrive: the VCO into the filter; 0 none, 25 the 303, 127 = 66.6× (resonance swamped) |
| 1 | FM | 0..127 | 0 | filter FM from the VCA output (after the Muffler); high = towards chaos |
| 1 | TRCK | 0..127 | 0 | filter tracking, linear in Hz up to ~2.7 kHz/oct; low notes can shut the filter |
| 1 | VDEC | 0..127 | 64 | volume: 0..64 decay 16 ms .. the 303's; 64..127 the sustain level, 127 = endless notes |
| 1 | SLID | 0..127 | 0 | slide time, 60 ms (0, the 303) .. 360 ms |
| 1 | ADEC | 0..127 | 50 | accented notes' filter decay, 30 ms .. 3 s to 10 %; 50 = the 303's own (OCTA303's MEG circuit, 200 ms). v7.9: every value is the same circuit with another resistance in place of R138 (the Devil Fish's Accent Decay pot), so the knob is continuous: 49 / 50 / 51 = 192 / 200 / 207 ms to 10 %, no jump, and the tail (1 %, 0.1 %) lengthens with it too; below ~1 % it is extrapolated 🟡 |
| 2 | SATK | 0..127 | 0 | soft attack on non-accented notes: 0 none, 1..127 = 0.3 .. 30 ms |
| 2 | SWP | ACID, WHST, SELF | ACID | ACID the 303; WHST resonance doubled; SELF doubled and no accent sweep (the filter can self-oscillate) |
| 2 | SPD | FAST, NORM, SLOW | NORM | accent sweep speed: FAST first accent strongest, NORM the 303, SLOW up to twice (v7.8: C13 of OCTA303's accent circuit / 4, as is, x 4 read doubled; 🟡 an interpretation) |
| 2 | MUFF | OFF, SOFT, HARD | OFF | the Muffler after the VCA: loud peaks clipped, the bass kept |
| 2 | CUTX | OFF, ON | OFF | the wide cutoff pot: lower, and up to ~5 kHz |
| 2 | ENVX | OFF, ON | OFF | env mod tripled, from none |

With dEVILish on the track, its SLID replaces the OCTA-303 SETUP page's SLID.

## How it works

- **ColdFire:** the module is a menu entry with twelve knobs (a clone of DARK REV's descriptor,
  FX id `0x10`, PHASER's, which it replaces on both menus). The OCTA303 voice compares each track's live FX1 / FX2 id with that id
  (`DEVIL_ID`, handed to `octa303` through `remix.inc`) and, on a match, reads the slot's knobs
  as the DSP gets them: page 1 from the track's DSP voice record, where the frame builder has applied
  the locks, the scene morph and the LFOs before the 303 renders (`docs/firmware/LFO.md` section 5,
  MIDI.md Appendix C); page 2 from the live lane. Until 21 Oct 2026 the voice morphed the lane's bytes
  itself, which no LFO reaches: an LFO on a dEVILish knob did nothing on the unit (the owner's MKI,
  image DEVPR1).
  The knob laws are tables in `tools/octa303/o3tables.py` (`DF_*`); the engine is
  `modules/octa303/octa303.s`.
- **DSP:** a pass-through (init and proc return at once, 5 words): an in-place insert that touches no frame.
- A remix without dEVILish gives `octa303` `DEVIL_ID 0x100`, which no id byte equals: every 303
  track is then the plain one.

## Measured

- ✅ `tools/octa303/sim/test_octa303.py` (the `octa303` gate): the Devil Fish engine in
  `octa303.s` equals `ref303.py` sample for sample, on FX1 and FX2, with knobs moved, locked and
  taken away, at the extremes, and from the voice record with an LFO's fractional low bytes, a moving
  LFO and either ping; the neutral knobs equal no
  dEVILish; a remix without it is neutral; the module's knob order and defaults are the engine's.
- ✅ DSP cost 1 cycle/sample (`make cycles REMIX=acidtrack`).
- ✅ On the unit: the author's MKI, `acidtrack` images up to ACIDV71, October 2026: the current
  dEVILish in daily use for several days, many hours in all, on two or three OCTA303 tracks beside
  DisTorX; no fault seen. Those images had it on FX id `0x1f`, then `0x1e`; on `0x10` (PHASER's,
  since 21 Oct 2026, when `0x1e` became RESONATOR's) see "On the unit, this tree" when flashed.

- ✅ On the unit, this tree (on `0x10`): image DEVPR2 (BUILD 93, remix `devilish`, the owner's MKI,
  22 Oct 2026), by ear: an LFO on a dEVILish knob (FM, OVDR, TRCK) moves the 303, as it did not
  before the voice-record read; a scene with another FM through the crossfader and a lock on a
  step still act as before.
  The same image, every knob: OCTA-303 on T1 with accents and slides; dEVILish on FX1 at its
  defaults sounds as FX1 = NONE; page 1 OVDR, FM, TRCK, VDEC (0, 64, 127 = endless notes), SLID,
  ADEC and page 2 SATK, SWP (ACID, WHST, SELF), SPD (FAST, NORM, SLOW), MUFF (OFF, SOFT, HARD),
  CUTX and ENVX each act; on FX2 the same; on a track that is not a 303 the sound passes; an LFO
  on a knob, no hang; two OCTA-303 tracks with dEVILish for five minutes; save, power-cycle,
  reload keep dEVILish and its knobs.

## Inferred

- 🟡 ColdFire cost on the OCTA303 voice: ~1,500 instructions more per 16-sample frame with FM and
  MUFF on (~4,700 against ~3,200, simulator counts), ~3 % of the frame at ~1.77 cycles an
  instruction. Falsified by CF METER on the unit.
- 🟡 The knob ranges follow Whittle's descriptions; they are not measured against a Devil Fish.

## Open

- No recordings of a real Devil Fish with known settings were used; the mods are modelled from the
  manual, the plain 303 from Din Sync's recordings.

## Credits and sources

- **Robin Whittle**, Real World Interfaces — *User Manual for the Devil Fish mods to the TB-303*
  (2019) and the Devil Fish pages: https://www.firstpr.com.au/rwi/dfish/
- **Sam Banks**, octabam — the menu, the descriptor clone, the remixer.

## Gates

`tools/octa303/sim/test_octa303.py` (through `octa303`: 92/92 with `modules/devilish` in the
tree, its three manifest checks included); `make check REMIX=devilish` (`remixes/test/devilish`:
OCTA303 and dEVILish beside the stock effects but PHASER, whose id dEVILish takes).

## FX id

`0x10`, PHASER's, with `replaces="PHASER"`: on main every non-stock id below `0x20` is a
module's. A remix with dEVILish gives up PHASER on both menus.
