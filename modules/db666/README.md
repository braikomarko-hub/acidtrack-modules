# `db666` — dB666

A model of the dbx 160 compressor/limiter (1976), built from its schematic and
its manual, as a per-track insert with an id of its own — with a side-chain KEY
from any track over a one-word-per-track bus. It takes no stock effect's id;
its code runs in a given-up effect's words (PLATE REV in `remixes/test/db666`).

Author: MaMarko (Marko Brajković, [braikomarko-hub](https://github.com/braikomarko-hub)): the idea, the listening and the tests on the unit.
**The code was written by Claude (Anthropic)**: engine, calibration, integration and gates.

The name: decibels and the Devil (it sits beside dEVILish in the author's remix).
dbx is a trademark of Harman; this module is not affiliated with or endorsed by
dbx or Harman, and the name dbx 160 below only says which unit it models. It was
called DBX 160 in the author's images up to ACIDV73MP (October 2026).

The 160's character is its detector: dbx's true-RMS module (RMS 208, M2 on
the schematic; David Blackmer's log-domain RMS, US 3,681,618, one of the
patents printed on the schematic). Attack and release are not knobs on a 160:
they are that detector's single time constant. The manual gives the release
as 125 dB/s, which fixes it at τ = 10·log₁₀(e)/125 = 34.7 ms, and the same τ,
unchanged, gives attack times near the manual's ("Measured"). THRESHOLD and COMPRESSION act in
dB on the detector's output and drive a VCA (dbx 200, M1) with the
difference: a hard knee, ratio 1/(1 − k) for a fraction k of the dB over
threshold.

## FX id

`0x1b` preferred (a free id: `schema.FREE_FX2_IDS`), no `replaces`, so no
stock effect is taken and a remix may move it (`registry.assign_ids`). Up to
image ACIDV81 (28 Oct 2026) the author's remix ran it on EQUALIZER's `0x0c`
(`replaces="EQUALIZER"`); a project saved there opens its dB666 tracks on
whatever that remix puts on `0x0c`, so those tracks are re-selected once
(or the remix keeps the old id with `Remix.ids`, where the id is free).
BBD prefers `0x1b` too: in a remix carrying both, `assign_ids` moves one of
them, and a project saved there opens that track on the other id.

## Knobs

| page | slot | name | range | what it does |
|---|---|---|---|---|
| 1 | 0 | THRS | 0–127, default 96 | THRESHOLD: −50 dBFS (0) … 0 dBFS (127), RMS — the 160's 10 mV … 3 V span (49.5 dB), its top at full scale |
| 1 | 1 | RATI | 0–127, default 50 | COMPRESSION: k = 0.992 × RATI/100 up to 100 (0 = 1:1, 50 = 2:1, 75 = 4:1, 100 = 120:1, the 160's "infinity"); 101…127 carry on to k = 2 (127 = −1:1, the 160A's negative compression: louder in, quieter out) |
| 1 | 2 | OUT | bipolar, default 64 | OUTPUT GAIN (R80): −20 … +20 dB |
| 1 | 3 | KEY | OFF, T1…T8 | the detector's source: OFF = this track (the 160's own input), T1…T8 = that track's level from the bus (the 160's detector input jack) |
| 1 | 4 | MIX | 0–127, default 127 | dry/wet: 127 is the 160 alone, 0 an exact passthrough |
| 2 | 6 | KNEE | HARD / OVER | HARD = the 160; OVER = the 160A's OverEasy, a 10 dB-wide soft knee (width assumed) |

Stereo-linked like two 160s strapped for "true RMS power summing": one
detector on (L² + R²)/2, one gain on both channels.

## The side-chain bus

A `DspHook` at the stock dispatcher's FX1 entry — the site SIDECHAIN_COMPRESSOR
hooks (`sctap`), proven on an MKI — runs `dbt_tap` for every track, every
block, with the track's 16 frames at X:$00–$1F. Each track has a record of
four words at its core's half of the shared window:

| tracks | records (BEAT COUNT LAST LEVEL each) | LEVEL words |
|---|---|---|
| T1–T4 | payload B (core 1), Y:$3FFF0–$3FFFF | $3FFF3, $3FFF7, $3FFFB, $3FFFF |
| T5–T8 | payload A (core 0), Y:$37FF0–$37FFF | $37FF3, $37FF7, $37FFB, $37FFF |

**The tap sums a track's block only while someone listens** (29 Oct 2026,
the author's rule: what nobody hears is not computed). Every word has one
kind of writer, so the two cores cannot undo each other:

| word | written by | what |
|---|---|---|
| BEAT | each dB666 whose KEY names the track (OFF branches over the store) | its own heartbeat, +1 a block |
| COUNT, LAST | that track's tap only | the BEAT it saw last; blocks left awake |
| LEVEL | that track's tap only | the block's mean square, or 0 asleep |

The tap reads BEAT: changed since LAST → LAST = BEAT, COUNT = 8, sum; the
same → COUNT − 1 and sum while COUNT was above 0; else LEVEL = 0 and return.
A KEY turned on reads 0 for its first one or two blocks (0.36–0.73 ms,
against the detector's 34.7 ms: not heard); a KEY turned off keeps the tap
running 8 more blocks after the last beat it saw, plus up to one by the two
cores' order (about 3 ms). Two dB666 keying one track only make BEAT
change more often. (A first form of 29 Oct, one WANT word refilled by the
effect and counted down by the tap, could lose the refill when the two
cores' writes crossed: found by an independent review before it ran.)

A dB666 on either core reads the one LEVEL word its KEY names, once per
block; one 24-bit store is atomic, and a word is at most one block old.
The tap uses a, b, r0, r1, x0 — inside the set stock reloads after this site
— and replays the displaced `move x:>$208,r6` after its address arithmetic,
where it fills the AGU gap. The sum is one `mac` with its parallel load per
sample word (32 a block). It leaves r0 at $21 awake, or in the shared window
asleep; no stock setup routine reads r0 before writing it (all 13 checked).

Cost, counted from the listing at about one cycle a word, four for a taken
branch, three for `jsr` and `rts`, not measured: asleep about 33 cycles per
track per block, awake about 77. Per core, for its four tracks, cycles a
sample:

| what the tracks do | before 29 Oct | now |
|---|---|---|
| nobody keys any track | ~23 | **~8** |
| one track keyed (a kick pumping a bass) | ~23 | **~11** |
| all four keyed | ~23 | ~19 |

About 0.75 % of a core before and 0.27 % now when nobody keys (against
≈3,120 usable cycles a sample, CHIP.md). It is paid by every image that
carries dB666, and `cycle_count` does not price it (it is reached from the
dispatcher, not from the effect). The effect's side adds a heartbeat and a
branch per block, about one cycle a sample per instance.

SIDECHAIN_COMPRESSOR's tap copies the track's audio
instead, to offer audio-rate keys and a key listen, which the 160's RMS
detector does not need. The records sit at +$3FF0 of T8's and T4's FX2
slots, above every stock effect's measured extent (DARK REV's +$3DA2), in
Y:0x37F00..0x3FFFF, which payload B's boot zero loop clears. Until 26 Oct 2026
the (then single) words sat at Y:$33FF8 / $3BFF8 (the last $202 words of each half, measured by
SIDECHAIN_COMPRESSOR as never written by stock code); the demand loader's
window code (DLCOPY from 0x33DC3) now stops payload A's boot zero loop below
them, so they moved.

The ledger refuses dB666 beside SIDECHAIN_COMPRESSOR (the same hook site,
and a declared `conflicts`), so it cannot join `octabam`, which carries
SIDECHAIN_COMPRESSOR, and beside DELAY SERVER, whose line covers payload B's
words from 0x38000 up, the records at $3FFF0–$3FFFF included (so no bus remix).
No `window` placement is declared; the build checks window homes against
`Claims.dsp_ranges`.

## Measured

✅ `tools/verify/verify_db666.py` in `dsp_host`, the code as this image
places it, 29 Oct 2026 (the LEVEL words planted with `-pokey`; the tap is
run on its own, below):

- **Bit-exact** against `db666_ref.fixed()`: defaults, every knob at its
  ends, OverEasy, KEY from T1 (payload B's half) and T7 (payload A's), KEY
  out of range, a split block, LFO-dirty page words.
- **The manual**: attack to 63 % of the reduction 15.8 / 6.7 / 2.8 ms for
  10 / 20 / 30 dB over threshold at infinity:1 (the manual: 15 / 5 / 3 ms);
  release 123 dB/s (125).
- **Ratios** on a tone 10 dB over threshold: 2:1 → +5.04 dB, 4:1 → +2.56,
  120:1 → +0.08, −1:1 → −10.00.
- **KEY**: a −6 dBFS word on T1 ducks a −30 dBFS tone by −18.63 dB, the float
  law's figure exactly; an empty word does nothing.
- Below threshold at OUT 0 dB, and at MIX 0, the output is the input exactly;
  silence comes out as zeros.
- **Cost**: 338 words of code (the tap's 45 included; 297 before 29 Oct,
  when the AGU nops and the records came in) + 66 words of table; 160 cycles per sample by the
  pricer (`make cycles`), plus the tap (above). Worst core: 8 instances
  (FX1 and FX2 on its four tracks) = 1,280 static, about 1,800 with the
  ~1.4 that COSTS.md measured between static counts and the unit
  (inferred), against about 3,120 usable cycles a sample (CHIP.md). The
  code has no branch on a knob, so its cost does not depend on the
  settings (no `max_per_core`).
- **Instruction forms** (`verify_db666`, after `verify_distorx`): 105 used,
  88 with a stock site. Of the 17 without one, 14 (Tcc forms,
  `mac x0,x0,a`, the P table reads) ran on the owner's MKI in every
  acidtrack image; `beq` and `bra` have stock sites (the report's normaliser
  does not match stock's labels); **`mac x0,x0,a x:(rN)+,x0`, the tap's new
  sum, has none and has not run on a unit.** The bus stores use stock's
  forms (`(rN)+`, `(rN)-`).
- **The tap and the handshake** (`verify_db666`, dbt_tap run as the proc in
  dsp_host with the block at X:$00, 29 Oct 2026): asleep it writes LEVEL 0
  and leaves COUNT and LAST alone; a new beat sets LAST and COUNT = 8 and
  LEVEL = `db666_ref.tap()` of the block, bit for bit; the same beat counts
  down and keeps summing (LEVEL again bit-exact after 9 blocks); the tenth
  sleeps; a beat that changes while counting refills. The effect: KEY T1
  steps T1's BEAT once a block; KEY OFF writes no BEAT (sentinels kept).
  Not run: the two cores together (dsp_host runs one); the single-writer
  layout is the argument for that.

## How it differs from COMPRESSOR and SIDECHAIN_COMPRESSOR

CONTRIBUTING.md asks a module that overlaps an accepted one to say what
differs. Stock COMPRESSOR, and SIDECHAIN_COMPRESSOR on top of it, is a
compressor with ATTACK and RELEASE knobs; dB666 models one particular unit
whose character is that it has neither.

| | COMPRESSOR / SIDECHAIN_COMPRESSOR | dB666 |
|---|---|---|
| method | stock's compressor (a detector with ATTACK and RELEASE knobs, RMS on page 2) | the 160's true-RMS detector: one time constant, 34.7 ms, from the manual's 125 dB/s; attack and release follow the program (measured above: 15.8 / 6.7 / 2.8 ms at 10 / 20 / 30 dB over) |
| ratio | stock's range (not measured here) | 1:1 … 120:1 (the 160's "infinity") and on to −1:1 (the 160A's negative compression) |
| knee | stock's (not measured here) | HARD (the 160) or OVER (the 160A's OverEasy) |
| parallel | MIX | MIX (0 is an exact passthrough, `verify_db666`) |
| key | SIDECHAIN_COMPRESSOR: T1–T8 as audio, a base-width key filter (KBAS, KWID), key gain, a key listen (MON) | T1–T8 as a level: one mean-square word per track per block over a bus, computed only while a dB666 keys that track (about 8 cycles a sample per core asleep, 11 with one key; counted, not measured); no filter, no listen (the 160's detector takes a level, not audio) |
| knobs | 6 on page 1 + RMS and 5 key controls on page 2 | 5 on page 1 (THRS RATI OUT KEY MIX) + KNEE |
| in one image | — | not with SIDECHAIN_COMPRESSOR (the same dispatcher hook, `conflicts`); beside stock COMPRESSOR, yes |
| cost on a unit | COMPRESSOR 2.18 % a slot (COSTS.md); SIDECHAIN_COMPRESSOR not read | not read yet (see "Open") |

What was measured is dB666's side (the 160's attack and release law, the
ratios, the key); the difference in sound is by ear, on the owner's unit.

In short: COMPRESSOR is the tool to shape a transient by hand; dB666 is
a "set threshold and ratio and play" compressor with a sound of its own,
and a pump from the kick in two knobs (KEY, THRS).

## On the unit

✅ The owner's MKI, remix `acidtrack`, on EQUALIZER's id, from 11 Oct 2026
(first flash) to image ACIDV81 (28 Oct 2026): the side-chain ducking heard
clearly from the first flash (KEY on the kick), then hours of live use beside
OCTA303, dEVILish, DISTORX and, from ACIDV79, AtoMizer (demand-loaded into
T8's FX2 slot at +$1000, below the bus words at +$3FF8). `make check
REMIX=acidtrack` (the tap inside the real dispatcher, under the ColdFire
port) passed on the owner's tree. By ear only: no measurement of the ducking
on the unit.

⏳ On its own id (this form, `remixes/test/db666`): not yet flashed. What
changed for it: the dispatch row, the descriptor clone and the FX1 chooser
(now a list of its own, `Remix.fx1`, where before the module inherited
EQUALIZER's row), and in the DSP code the AGU nops, the BEAT handshake and
the one-cycle sum (the tap and the consumer's KEY block). The bus words have been
at today's +$3FF8 since ACIDV78 (26 Oct 2026); ACIDV79 (27 Oct) and ACIDV81
(28 Oct) ran them on the unit.

## Open

- Its slot cost on a unit (LOAD METER, defaults and `dear`), and the tap's.
- A recording of the ducking on the unit, against the model's attack and
  release.
- Instruction forms without a stock site (`verify_db666` lists them).
- OverEasy's real width; the 160A's own curves are not published.

## Gates

`tools/verify/verify_db666.py`: generated source, bit-exact on eight
settings (the bus planted with `-pokey`), the passthroughs, the manual's
attack and release, the ratios, the key, silence, every knob.

## Files

| file | what |
|---|---|
| `manifest.py` | the module, the hook, the bus words, every constant |
| `db666.tmpl.asm` | the DSP code with `@NAME@` constants (`@ROFF@` per payload: the half's first record less four words for each track before it) |
| `generate_asm.py` | writes `db666.asm`; `--check` |
| `db666_ref.py` | the 160 in float (`DB666`) and the module bit for bit (`fixed`, `tap`) |

## Sources

- dbx 160/161 manual and schematic (dbx Inc., c. 1976): the controls, the
  specifications (attack, ratio 1:1–120:1, threshold 10 mV–3 V), Figs. 4–5.
- dbx 160A cut sheet (Harman): release 125 dB/s, −1:1, OverEasy.
- D. E. Blackmer, US 3,681,618, printed on the schematic: the RMS
  detector.
- Zac-Kyoti, SIDECHAIN_COMPRESSOR (MIT): the dispatcher hook site and the
  shared-window region, measured on an MKI.
