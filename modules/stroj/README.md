# STROJ

A drone machine for the Octatrack MKI, on the ColdFire: four "plates" in two nearly-tuned pairs
with cross phase modulation (after SOMA's Lyra-8) and two sub-octaves that swell at their own rates
(after Moog's Subharmonicon). *Stroj* is "machine" in Bosnian / Croatian / Serbian.

Idea, design choices and listening: **MaMarko**. Code: **Claude** (Anthropic).

## Pages

STROJ is row 5 of the track's machine list (FUNC + SRC). The track is stored as FLEX and signed
`'S','J',1` in its NEIGHBOR PLAYBACK bytes (`Part' + 0x3c + 30·track`), so a project stays an
ordinary project. No sample is needed.

| Page | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| PLAYBACK | NOTE | SPRD | INTV | FM | SUB | TONE |
| SETUP | VOIC | SUB1 | SUB2 | BRTH | RYTM | WAVE |

| Knob | Values | What it does |
|---|---|---|
| NOTE | C0..C6 (default C2) | the base note, one semitone a detent |
| SPRD | 0..127 | how far each pair's two plates are apart (0..~30 cents): the speed of the beating |
| INTV | UNI MIN3 MAJ3 4TH 5TH MIN7 OCT OCT5 | the second pair's interval over the first |
| FM | 0..127 | cross phase modulation between the pairs (the Lyra's metallic side) |
| SUB | 0..127 | the two sub-octaves' level |
| TONE | 0..126, OFF | a state-variable low-pass, 40 Hz..~6 kHz; OFF (127) skips the filter |
| VOIC | 1..4 | how many plates sound (and are computed) |
| SUB1, SUB2 | /2../8 | each sub-octave's divisor of the base note |
| BRTH | OFF, 1..127 | the breath: a triangle of 2..64 s that moves FM (25..100 %) and the swells |
| RYTM | OFF 3:4 4:5 3:5 5:7 | the two sub-octaves swell at these rates against the breath |
| WAVE | SIN TRI SAW SQR | the plates' wave (band-limited tables, 48 partials) |

LFO SETUP names the PLAYBACK destinations NOTE SPRD INTV FM SUB TONE. CHROMATIC plays NOTE in
semitones (TRIG 13 = C2, as the knob's middle; raw = 52 + key index, OCTA303's mapping).

A trig starts the track; a trigless trig, a lock or a scene change only changes what the plates
play: their phases never restart, so a chord moves without a click. AMP, FX1 and FX2 are stock
after the voice: a long AMP ATK lets the plates in slowly; the Lyra's delay is the track's DELAY
with a high feedback, the space DARK REV.

## Cost

What is not heard is not computed: plates past VOIC, the FM path at FM 0, the sub-octaves at
SUB 0, the filter at TONE OFF. ColdFire instructions a 16-sample call (sj_voice, counted under
cfsim by `tools/stroj/test_stroj.py`):

| Setting | Instructions |
|---|---|
| everything on (4 plates, FM, SUB, filter) | 2,468 |
| 1 plate, FM 0, SUB 0, TONE OFF | 860 |
| OCTA303, for comparison (its README) | ~3,200 |

Not measured on a unit (the LOAD METER's ColdFire share would be the number).

## Beside OCTA303 (HOOKS)

With OCTA303 in the remix, HOOKS's `machine_rows` bridge makes STROJ the head of a seven-row
list, in ANALOG BD's place: STROJ row 5, OCTA-303 row 6. STROJ's hooks take every shared site and
hand each row but 5 to OCTA303's routine for it; OCTA303 keeps the kind table's FLEX entry and calls
`stroj_render` as its next renderer (`HK_HEAD_STROJ` in its `remix.inc`), and its `o3_retrig`,
`o3_lfo_name` and `o3_chrom` ask STROJ (`sj_latched`, `sj_sig`) about tracks that are not 303s;
STROJ's own retrig, LFO-name and CHROMATIC detours (used alone) yield to them. STROJ and ANALOG BD are never in one remix (both
are the head). Remixes: `test/stroj` (STROJ alone), `test/stroj-303` (beside OCTA303).

## How it works

- **Audio** follows OCTA303 (after Tim Hastie's SYNTH MACHINE 2.9): on a STROJ track the stock FLEX
  renderer writes the header with PTCH / RATE neutral and the carrier's positions pinned (the frame's
  last call), then `sj_voice` writes the samples (L = R). PLAYBACK knobs come from the packer's DSP
  parameter record (locks, scenes and LFOs applied), SETUP from the live lane.
- **The voice** (per sample, integer): four phase accumulators reading 2048-entry wave tables, the
  partner plate's last output as phase modulation, two sub-octave counters (their top bit is the
  square), `1.5·(x − x³/3)` saturation, a Chamberlin state-variable low-pass with its states held in
  ±65535. Control (increments, breath, swells, gains) once a call.
- **The machine row** takes the fifteen seams repeat98 measured for ANALOG BD, as OCTA303 v7.0 does;
  the page record is a RAM clone of the stock FLEX record with STROJ's names, defaults, counts and
  formatters. The Part validator sees FLEX's defaults in a signed track's twelve bytes and gets
  STROJ's back after.

## Measured

- ✅ `tools/stroj/test_stroj.py`: the module's text under cfsim, linted whole against the ColdFire
  encoding limits; `sj_voice` bit-identical to `tools/stroj/stroj_ref.py` (every knob at 0 and 127,
  random knobs changing every call with odd call lengths, a 400-call held drone); the generated
  tables are `stroj_ref.py`'s.
- ✅ `tools/verify/verify_stroj_port.py` (OT_PROJECT, under the ColdFire port): the list shows STROJ
  on row 5 (OCTA-303 on row 6 beside it), YES signs the track with STROJ's defaults in the Part, its
  shadow and the live lane, SETUP edits land there, UI type 5's record is STROJ's, another machine
  clears the signature; LFO SETUP reads `PB NOTE`; CHROMATIC's TRIG 16 / 1 / 13 play D#2 / C1 / C2;
  a signed track with a trig reaches the outputs with C2, its octave and the /2 /3 sub-octaves.
  Run on both test remixes (30 Oct 2026).
- Not run on a unit.

## Not yet

- A track is checked for STROJ at a START (as OCTA303 does): choosing another machine without a
  trig leaves the drone sounding until the next trig.
- `verify_hooks`'s Unicorn run of the machine rows (`machines()`) covers ANALOG BD as the head only;
  STROJ as the head is covered in the image (`installed`) and under the port (`verify_stroj_port`).
