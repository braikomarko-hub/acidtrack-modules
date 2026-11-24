# `octa303` — OCTA303

A circuit-modelled Roland TB-303 voice that runs on the Octatrack MKI's ColdFire, one voice per
track. Since v7.0 it is a machine of its own, **OCTA-303**: row 5 of the track's machine list (row 6,
below ANALOG BD, in an image that carries both; CX OSC then follows it: [HOOKS](../hooks/README.md) `machine_rows`), with
its own PLAYBACK and SETUP pages. It needs no sample. It is calibrated against recordings of a real
TB-303 (Din Sync's x0xb0x reference set, 400 notes with known knob positions) and optionally plays
Robin Whittle's Devil Fish modifications through the companion FX module `devilish`.

Author: MaMarko (Marko Brajković, [braikomarko-hub](https://github.com/braikomarko-hub)): the idea, the listening and the tests on the unit.
**The code was written by Claude (Anthropic)**: engine, calibration, integration and gates. Every number below
comes from the measurements and gates named beside it.

**Another TB-303 for the Octatrack:** Zac Kyoti's
[BLACKPYRAMIDS_303](https://github.com/Zac-Kyoti/octatrack-kyoti-fw) (BLKPYRAMD) adapts Robin
Schmidt's Open303 to the **DSP**: one voice per DSP core (one on T1–T4, one on T5–T8), in SPRING
REV's space, voiced by ear. OCTA303 takes the other road: the voice runs on the **ColdFire**, one
per track (up to two in a Part), gives up no stock effect, and its model is fitted to
measurements of a real TB-303 (Din Sync's set, below) rather than tuned by ear. Both register
their machine row with repeat98's ANALOG BD seams, so they cannot share an image.

Markers as in `CHIP.md`: ✅ measured, 🟡 inferred.

## Limit: two machines in a Part

A Part holds at most **two** OCTA-303 tracks. Choosing OCTA-303 for a third shows `MAX 2 OCTA-303` and the
track becomes plain FLEX. A Part loaded with more has its first two signed tracks (by track number) kept and
the rest unsigned by the Part validator, so they are FLEX in the Part and on the screen (a file saved
afterwards no longer has those signatures); the render path counts the same way. Measured on one MKII (2 Nov 2026, meter only, fresh start): nothing playing
25.3 % of the ColdFire frame interrupt, 2 machines playing 65.5 %, 4 machines 83.2 %; the model fitted to those
(about 21 points once any machine plays, 9.3 per machine) gives about 102 % for six. Near 98 % the frame
interrupt leaves the panel's task almost no time: the audio keeps playing and the interface stops answering
(`docs/contributing/FAILURE_MODES.md`). Until v7.9 a track that started on a sample named `TB303*` was a second
way into the voice, not counted; v7.9 took it away, so two is the limit.

## Using it

1. Double-tap the track key (the machine list), choose **OCTA-303** (below PICKUP), **YES**.
   FUNC + SRC opens the same list, but on a FLEX or STATIC track with a sample it opens the sample
   list first: LEFT reaches the machines (the stock behaviour).
2. Sequence it like any track. **Accent** = an ACC parameter lock. **Slide** = a trigless trig or a
   trigless lock (FUNC + TRIG) on the following step; since v7.1 it gets the note it slides from as
   its TUNE lock the moment it is placed (the previous step with a trig or a trigless step: its TUNE
   lock, or the Part's TUNE), so the slide ties into that note as on the TB-303. Turn TUNE with the
   step held to slide somewhere else. A step that already has a TUNE lock keeps it.
3. The CHROMATIC keys play semitones on an OCTA-303 track.
4. **The TB-303's UP and DOWN** (v7.1): in GRID RECORDING, hold one or more trigs and press UP or
   DOWN: each held step's TUNE goes an octave up or down (a step without a TUNE lock starts from
   the Part's TUNE; a note past C1..C5 stays where it is), and the screen shows the note
   (`C4 +OCT`). On every other track TRIG + UP / DOWN is stock (the sample-lock list).
5. LFO SETUP names an OCTA-303 track's PLAYBACK destinations TUNE CUT RES ENV DEC ACC (v7.1; before,
   FLEX's PTCH STRT LEN RATE RTRG RTIM: the modulation was right, the names were not).

Until v7.8 a FLEX track whose sample was named `TB303*.wav` (`TB303`, `TB303SQ`, `TB303D`, `TB303SQD`, any
case) played the same engine with neutral SETUP values. v7.9 took that way out: such a track plays its sample.
A project that used it gets the same sound from an OCTA-303 track with WAVE set to the file's carrier (SAW, SQR,
SAW+D, SQR+D) and the other SETUP values at their defaults.

### PLAYBACK page (the FLEX playback slots)

| slot | name | range | what it does |
|---|---|---|---|
| 0 | TUNE | C1..C5 (raw 40..88) | semitones, shown as note names; C3 = 0 |
| 1 | CUT | 0..127 | cutoff, the 303's CUTOFF FREQ law |
| 2 | RES | 0..127 | resonance (never self-oscillates without Devil Fish SWP; v7.3, ACID: no fs/4 whistle at the top, #1011) |
| 3 | ENV | 0..127 | ENV MOD (audio taper, as the Roland service notes) |
| 4 | DEC | 0..127 | DECAY, 0.157..2.46 s to 10 % (v7.5: the service notes' parts; ✅ the Din Sync fit agrees) |
| 5 | ACC | 0..127 | the ACCENT knob, applied on the notes that carry an ACC lock |

A new OCTA-303 track starts at TUNE C3, CUT RES ENV DEC 64, ACC 0.

### SETUP page (the FLEX setup slots)

| slot | name | values | default | what it does |
|---|---|---|---|---|
| 6 | WAVE | SAW, SQR, SAW+D, SQR+D, RSAW, RSQR, RSAWD, RSQRD | SAW | waveform; `+D` adds a distortion pedal stage after the VCA; v7.9: `R` = the 303 as Roland's factory trims its filter (TM3: the cutoff +0.575 octave at every CUT; without `R`, Din Sync's 303) |
| 7 | GATE | OFF, 303 | OFF | OFF: the AMP page shapes the note. 303: the 303's own gate, 3.5 of the step's 6 clocks (Whittle), tied into a slide |
| 8 | FINE | −64..+63 | 0 | fine tune, ±½ semitone |
| 9 | SLID | 0..127 | 0 | slide time (0 = the 303's RC; `devilish`'s SLID wins when it is on the track) |
| 10 | DRIV | 0..127 | 0 | v7.7: the 303's VOLUME (VR8) past Din Sync's position. 0 = the recording's level (pin 6's ceiling only); above 0 up to +10 dB into the output mixer's soft, asymmetric saturation (Q33/Q34). Projects saved with DRIV > 0 sound different |
| 11 | ACCV | 0..127 | 64 | accent loudness: v7.8 scales the accent's current into the VCA (I27, from the circuit); 64 = the 303 |

## How it works

- **Audio.** The FLEX entry of the renderer kind table (`0x400d6438`) points at `sy_render`. On an
  OCTA303 track it writes the header the stock renderer would (the count, the start, rate 1.0, the
  ring word) and the 303's samples into it, without calling the stock renderer (v8.6, CX OSC's way:
  a sample left in the track's slot is not rendered under the 303). Two calls still run the stock
  renderer: one before the track is latched, and (v8.7, vFable's hybrid) the last call of a frame
  with a START, neutralised as before -- without it a track set back to FLEX stayed silent on the unit.
  Every other track is stock. AMP, FX1 and FX2 stay stock, after the voice.
- **The engine** (per sample, Q-format integer): PolyBLEP saw, the square from Q8's circuit (v7.6), 4-pole
  diode ladder with the 303's unequal first stage, one high-pass after it shared by the feedback and
  the output (v7.5, the circuit's), resonance law `k = K(f) × law(RES) − decay(RES) × KD(f)` solved
  from a linear model of the ladder, the VCA's input pair (v7.5) and its OTA (v7.6), MEG / accent-sweep capacitor / VCA
  envelopes at control rate, RC slide, output coupling and a soft output ceiling.
- **The machine row** (v7.0) uses the seams that repeat98 measured for `analog-bassdrum`: the same
  fifteen detours and six pokes, without its engine pool. A track is stored as FLEX and signed
  `'T','B',1` in its NEIGHBOR PLAYBACK bytes (`Part + 0x3c + 30·track`, unused by NEIGHBOR). Its
  page record is a clone of the user's FLEX descriptor, built at run time, published as UI type 5
  (`0x400d5f4c`). The Part validator (`0x40002318`) sees FLEX's defaults in a signed track's twelve
  bytes and gets ours back after. Projects stay ordinary projects.
- **Every table** is generated by `tools/octa303/gen_tables.py` from `o3tables.py`; `make check`
  refuses a stale table.

## Measured

### Against a real TB-303 (✅, simulator, bit-exact engine)

Reference: Din Sync's x0xb0x reference recordings — 25 files, 400 notes at C2 with CUTOFF, RES,
ENV MOD, DECAY and ACCENT at known positions (0/25/50/75/100 %).

| measure | v6.5f | v6.7 | v6.9 |
|---|---|---|---|
| timbre, 16 half-octave bands, 80 ms..1.2 s | 6.02 dB | 0.77 dB | — |
| band energy, all windows 4 ms..1.2 s | — | — | 4.68 dB |
| brightness over time (spectral centroid 2 ms..1 s) | — | — | 0.18 oct (v6.8: 0.30) |
| resonance ring decay at RES 127, 1.2..12 kHz | — | — | 2.0..2.5 dB/ms (303: 2.0..2.6) |

For scale: the same 303 recorded twice at the same settings differs by 0.20 dB in the first metric.

tinyloops "drops" (the resonant ring on each saw reset): ring decay 3.4 / 3.1 / 3.1 dB/ms against the
303's 3.4 / 3.0 / 3.1; frequency error 0.062 octaves. Fitted from sound alone, the calibration places
tinyloops' RES at 112/127; the photo of the knobs reads 85–90 %.

Accent (Din Sync set A5, saw, peak / energy in the first 4–40 ms, relative to the plain note; all three measured
the same way on 3 Nov 2026, the engines through `ref303.py`; v6.8's table: `git show 1024283:modules/octa303/README.md`):

| ACCENT | TB-303 | v7.3 | v7.5 |
|---|---|---|---|
| 25 % | +0.6 / −0.5 dB | +2.5 / +1.9 dB | +0.7 / +0.5 dB |
| 50 % | +4.9 / +5.6 dB | +6.2 / +4.8 dB | +6.4 / +5.2 dB |
| 75 % | +15.3 / +13.0 dB | +17.2 / +13.2 dB | +13.3 / +10.9 dB |
| 100 % | +15.6 / +16.7 dB | +22.4 / +17.5 dB | +20.0 / +16.6 dB |

### The code (✅)

- `tools/octa303/sim/test_octa303.py`: 114/114 with `modules/devilish` (v7.6; v7.4–v7.5: 112/112; v7.3: 109/109; v7.1: 108/108; 92/92 before, 89/89 without it:
  three checks read dEVILish's manifest, one checks OCTA303's own `DEVIL_ID`). `octa303.s` executed
  from its source text in a ColdFire simulator equals the Python model `ref303.py` sample for sample:
  both carriers, accents, slides, split frames, extreme knobs, Devil Fish on FX1/FX2 (read from the DSP
  voice record: locks, scenes and LFOs applied), the gate state machine (fuzzed), the SETUP page, the machine registration helpers and
  the validator wrapper.
- No overflow: the VCA input is clamped from the tables so the product fits 32 bits (fuzzed
  over thousands of knob combinations).

**Why `tools/octa303/sim/cfsim.py` exists beside `ot_emu`.** The two answer different questions.
`cfsim.py` (415 lines) interprets the *text* of `octa303.s` and calls the voice's entry points
directly with knob words, frame states and fader positions chosen by the test, so the engine can be
compared with `ref303.py` sample for sample over thousands of fuzzed cases in seconds, with no OS
image, no assembler and no project. It also lints the source against ColdFire encoding limits a
68k-minded author gets wrong (`asr.l #15`, `muls.l #imm`, byte/word ALU ops): the v4 source had one
that m68k-elf-as refused. It is a correctness model, not a timing model, and not an assembler.
`ot_emu` runs the built image as a whole machine: it is what shows that the machine row, the pages,
the validator and the audio path work in the firmware (`verify_octa303_ui`, "Under the port" below),
but driving one engine call per case through the sequencer there would take hours for what the
simulator checks in seconds. Not done: `cfsim.py`'s output has not been compared bit for bit with
the same calls under `ot_emu`; the port gate and the unit are what catch a simulator that reads an
instruction differently from the chip.

### v7.3 (3 Nov 2026): Zac Kyoti's report, sambanks/octabam#1011

Zac Kyoti studied `ref303.py` against v7.1 and sent five findings with a repro script. Every number
in his report was reproduced exactly on `828314dc` before anything changed. v7.3 fixes the two that are
defects; the three that are calibration choices stay as fitted until they can be refitted on Din Sync.

| # | finding | v7.3 |
|---|---|---|
| 1 | CUT, RES and ENV high: an 11.025 kHz (fs/4) tone locks for the first 25–45 ms of every note (up to −1.7 dB of the signal) | **fixed** |
| 3 | `VCA_LIM` hard-clips plain notes (RES ≈ 0, open or accented: +3.4 dB over it) | **fixed** |
| 2 | the coupling high-passes (149 Hz in, 45 Hz in the loop) are not the circuit's (flat in, one ~92 Hz shared) | open: needs a refit |
| 4 | ENV MOD depth grows with RES (+0.36 to +0.80 octave) | open: needs a refit |
| 5 | accent peaks +1 to +4.5 dB over the 303 at 50–100 % | open: needs a refit |

- ✅ **The fs/4 lock** (simulator). As Zac found, the cubic soft clip in the resonance loop: as the
  resonance sweeps up through ~11 kHz its 3rd harmonic (3 fs/4) folds onto fs/4 and the loop locks to a
  period-4 cycle. v7.3 runs the clip at a lower operating point near the top of the table only:
  `y0 = softclip(u·g)/g`, g = 1 up to ladder index 383 (~5 kHz; the engine is unchanged below it), falling
  linearly to 0.5 at index 431 (~10 kHz) and above (v8.3: 0.3, see below). The clip's slope at 0 is 1, so the small-signal
  resonance law (KO / KD) is the same. ACID mode only: dEVILish's WHST / SELF oscillate on purpose and the
  clip sets their level (eased there, they were up to +4.6 dB louder at the top), so they are unchanged.
  Share of the first 46 ms at fs/4, `octa303_repro.py` cases: −2.7 → **−24.2**, −5.1 → **−29.1**,
  −6.6 → **−27.7**, −3.7 → **−11.0** dB (the clip bypassed altogether, Zac's diagnosis: −20.8, −30.6,
  −17.9, −14.1); what is left at fs/4 is the resonance passing through it: the strongest line above
  5 kHz now follows the linear ladder's sweep (15 → 7 kHz) in every 6 ms window instead of sitting at
  11 025 Hz for three of them. Worst case in his grid (RES 110–127, ENV 120–127): −24.9 → −39.8 dB. On a
  96-note grid (CUT 20/64/100/127 × RES 0/64/110/127 × ENV 0/64/120 × ACC 0/127), 65 notes are within
  −60 dB of v7.1 (the VCA's extra bit); the notes that change are the high CUT + RES + ENV ones, in their
  first ~45 ms (level ±2.3 dB there), the rest of the note within 0.1 dB and the same brightness.
  **v8.3: 0.5 → 0.3** (simulator, `ref303`). At 0.5 one note still locked in a 12-note accented run at
  CUT 110, RES/ENV/ACC 127, SAW R, TUNE −12/0/+12 (fs/4 above −6 dB of the note for 49 ms); on a
  2,304-note grid (TUNE ±12/0 × RES, ENV, CUT 110/127 × ACC 0/127 × SAW/SQR/RSAW/RSQR) 3 locked notes at
  0.5, **0 at 0.3**. Not 0.25 (also 0 locks): the clip's output grows as 1/g into the ladder's first
  multiply, and a random search with dEVILish OVDR / FM / MUFF up reached 0.72 of 2^31 there at 0.25,
  0.62 at 0.3, 0.37 at 0.5 (measured; no closed-form bound). Side effect: notes at CUT and RES near 127 are
  louder in their first ~50 ms. Measured at 0.3 against 0.5 on the same grid (192 runs, 2,304 notes): first 50 ms of
  each note within ±1 dB for 2,145 notes, +1 to +2.3 dB for 156, and −6 to −10 dB for the 3 that locked (the
  whistle gone); whole-run level median +0.05 dB (−2.2..+1.1); 174/192 runs within 1 dB in every band
  (50–200–800–3k2–8k–22k Hz). Not yet heard on the unit.
- ✅ **The VCA's room** (simulator). The multiply is now `(o >> 7) · (amp >> 1) >> 6` (was `(o >> 6) · amp >> 8`),
  and `AMP_MAX` counts SETUP's ACCV: before, ACCV above 64 on an open accented note **wrapped the 32-bit
  multiply** (found while checking #1011; CUT 80 RES 0 ENV 127 ACC 127 ACCV 127: full-scale jumps, a
  crack, in v7.0–v7.1). `VCA_LIM` 3 878 080 → 10 154 880: on a grid of CUT 0/80/127 × RES 0/10/127 ×
  ENV 0/127 × ACC 0/127 at ACCV 64 and 127, DRIV 0 and 127, saw and square, nothing clips and the
  loudest peak is −4.1 dB under it (OVDR 127: about half of it). MUFF's lowpass input is clamped so its
  multiply still fits 32 bits at the wider VCA (independent review: not reached in the model).
- 🟡 **Not changed, open** (2, 4, 5): they are the fit's choices, and moving one moves the others (Zac:
  the two high-passes trade against each other on single notes). A Python-only experiment, the
  circuit's high-pass layout (VCO → VCF 0.7 Hz, one 92 Hz high-pass shared by the loop and the output,
  KO / KD re-solved) plus an ENV MOD depth that ignores RES, was rendered for the author to listen to;
  it is not in the engine. A refit on Din Sync's set with the circuit topology is the next step.
- Not on the unit yet. `test_octa303` gains `bit_exact_v73_top_clip_accv` (the eased clip with and
  without dEVILish's per-sample FM, WHST's plain clip, ACCV 127 through the wider VCA).

### v7.4 (3 Nov 2026): GATE 303's first note after PLAY

Reported on Discord (misterairplane, Tom de Guerre): with SETUP's GATE 303 the first trig after PLAY
was silent. Measured under the port (1.40C, MKI): at PLAY the firmware writes the step word
(`0x800065b2`, which holds the step *after* the one playing) as 1 and the tick (`0x800065b6`) as 0,
then tick 1 a frame later; the STOP there wrote the transport word (`0x800065b8`, 1 = running) 0 and the
step word 0 (`docs/firmware/STEM_REC.md`: the STOP key writes 2 and keeps the position; the gate takes
anything but 1 as stopped). v7.0–v7.3 measured the step length from the first two moves and took PLAY's first move for a
step, so the first gate closed at once. v7.4 reads the transport word: no measurement while stopped,
two tick intervals skipped after a restart, and the slide test looks at the step playing
(`cur = (s − 1) mod L`), not the next one; the first move a fresh state sees (the first PLAY after boot)
counts as a PLAY too (v7.5, from the review). Under the port the first note after PLAY sounds in every
case (203 frames), and a slide ties on its own step. `test_octa303` adds
`gate_first_note_after_play` (the measured PLAY order) and `gate_slide_on_the_next_step`.

### v7.5 (3 Nov 2026): the circuit's layout, refitted; v7.3's accent stage

#1011's points 2, 4 and 5, after the Roland service notes (main board: the x0xb0x netlist's values).

| | v7.3 | v7.5 |
|---|---|---|
| VCO → VCF coupling | 149 Hz high-pass | none (C17/R62's corner is 0.72 Hz: left out) |
| loop and output high-pass | 45 Hz in the loop only | one ~107 Hz high-pass (C25/C27 into the Q21 pair), shared by the feedback and the output |
| VCA input | a fitted gain by RES | the pair R121 220k / C21 10 nF (72 Hz) + R122 100k / C22 10 nF (156 Hz) weighted 2.2 × RES |
| ENV MOD depth | grew with RES | by ENV MOD only (VR4b goes to the accent network, not the envelope) |
| DECAY | 0.08–2.35 s (fitted) | 0.157–2.46 s to 10 % (service notes: "MIN 200 ms, MAX 2.5 s"; C62 1 µF × 68k..1.068M) |
| accent decay | 0.13 s (fitted) | DECAY at its minimum (the service notes: the accent shorts the pot) |
| accent stage | direct path + capacitor (fitted) | the same code, refitted |

The accent stage was first rebuilt from the schematic too (D24, R46 47k, VR4b 50k, C13 1 µF, R72 100k,
solved per RES position: v7.4's draft "F"). It fitted Din Sync's isolated notes, but on tinyloops'
accents in a row (each note 112 ms after the last, so C13 builds up) its resonance sat 1.5–2 octaves
under the 303's in the first 15 ms; fitted with tinyloops in the objective it lost the lines. v7.3's
accent stage, refitted with everything else, matches both, so v7.5 keeps it.

Fitted (CMA-ES, two stages: the accent stage, then every number) on Din Sync's 400 notes and tinyloops'
accents in a row together. Measured the same way for every version (third-octave cells × 7 windows,
4 ms–1.2 s, the first two windows phase-averaged; tinyloops' ring frequency by zero crossings at
1 / 7 / 14 / 28 / 57 ms, each version at its best knobs inside the ranges read from tinyloops' photo):

| | v7.3 | v7.4 draft (F) | **v7.5** | the 303 against itself |
|---|---|---|---|---|
| Din Sync cells (dB) | 2.55 | 2.42 | **2.40** | 1.90 |
| Din Sync brightness (oct) | 0.171 | 0.162 | 0.169 | 0.092 (0.182 retracted: see v7.6) |
| Din Sync accent peak (dB, RMS) | 2.09 | 1.70 | 1.76 | — |
| tinyloops ring (oct, RMS), retracted (see v7.6) | ~~0.130~~ | ~~1.69~~ | ~~0.078~~ | — |

The table is the float twin the fit runs on. Through the integer engines (`ref303.py`), scored the same way (the
first two windows averaged over four VCO phases), v7.5 gives 2.40 dB / 0.168 oct / 1.81 dB: the same as the twin
(the accent peak 0.05 dB higher: the twin lacks v7.3's ladder-clip operating point, see v7.6).
(Retracted, 4 Nov 2026: an earlier paragraph here gave integer-engine numbers from one VCO phase and with Din Sync's
accents at ACCENT 0 rendered unaccented, a bug in the check's renderer, not the engine.)

tinyloops (Hz at 1 / 7 / 14 / 28 / 57 ms): the 303 5812 / 5075 / 4307 / 2187 / 1050. The fit puts tinyloops' knobs
at CUT 45, RES 106, ENV 116 (the edges of what the photo reads). (Retracted, 4 Nov 2026: integer-engine Hz given here,
v7.3 5775 / 5075 / 4200 / 2689 / 1084 and v7.5 5990 / 5685 / 4487 / 2156 / 1149, came from a renderer with its
steps rounded to 16 samples and no pre-roll, so the VCO's phase was not the twin's; this measure moves with that
phase, see v7.6.)

The "the 303 against itself" column: 18 settings Din Sync recorded twice (316 pairs). Before v7.5 the
tinyloops term in the fit measured ungated notes with the recording's onset detector, which put its
windows in the wrong place; fixed (the 303's gate on the model's notes, the same detector), the float
twin and the engine now agree (v7.3: 5298 / 4664 / 3969 / 2667 / 1121 against 5292 / 4688 / 4009 / 2667 / 1131).

🟡 Three videos of a real TB-303 with the pattern drawn on screen (Circus Bells, Stakker Humanoid,
Modjo) were used for listening only: one accent in all three patterns, damaged stretches in the
downloads, a ~5 kHz notch in every clip, knobs readable to ±10 %. One check from them: the plain notes
of Circus Bells' pattern 1 last 62–79 ms to −20 dB on the 303, 72–78 ms on v7.5's GATE 303 at 127 BPM.

The cost: the pair adds ~25 instructions a sample, 3,592 instructions a 16-sample frame (saw; 3,937
square), v7.3 3,198 / 3,543 (simulator counts).

### v7.9 (7 Nov 2026): WAVE's R, the 303 as Roland's factory trims it

The recordings OCTA303 is calibrated on (Din Sync's 303) ring ~0.5 octave below Roland's factory trim of the filter.
WAVE's four new values (RSAW, RSQR, RSAWD, RSQRD; bit 2 of WAVE) add TM3 as Roland trims it: TM3 feeds the cutoff node
N134 through R73, so it is the same octaves at every CUT (the researcher, `OCTA303_v79_catena_e_fabbrica.md` sec. 2).
The amount is Roland's own procedure (service notes p. 7: saw, key C, CUT halfway, RES full, ENV/DEC/ACC 0, the ring's
first interval 2.0 ms ± 0.5) applied to the model: without R it rings at 2.97–2.99 ms, so R adds log2(2.98 / 2.0) =
+0.575 octave (`TM3_FAB` = 1766 of 3072 an octave; the researcher's estimate +0.47…+0.64). On the engine, RSAW rings at
2.02–2.04 ms from 500 to 1,200 ms (test `fab_roland_ring_2ms`); the shift is 1766 at CUT 0/32/64/95/127
(`fab_same_octaves_every_cut`; the ladder's top still clamps). WAVE's count goes from 4 to 8: a project's stored
WAVE 0..3 keeps its meaning (`stamp-defaults` does not touch OCTA303's SETUP bytes, and nothing needs it here). Each label fits its 6-byte field with its NUL
(`wave_labels_fit_their_field`); no '.' (the panel's font). Din Sync does not judge R (it is not Din Sync's 303).

### v7.9 (7 Nov 2026): dEVILish ADEC, continuous

ADEC used to jump across its neutral 50 (v7.8, below). Now every ADEC value is the MEG circuit itself, with one
resistance in place of R138 + IC12's Ron on accents: the Devil Fish's Accent Decay pot (30 ms … 3 s, Whittle's manual
p. 4). `o3meg.adec_tables` solves R for the time to 10 % of a law that is geometric on each side of the 303's 200 ms:
30 ms at ADEC 0, 200 ms at 50, 3.0 s at 127 (R 8.3 kΩ … 1.3 MΩ). Each row's circuit runs 7 × its own time to 10 %,
so every row ends near 1 % as MEG_T's row 0 does; below that the last factor is held (🟡 extrapolated, as MEG_T's
tail), and the times to 1 % and 0.1 % grow with ADEC too (ADEC 50: 1.50 s / 5.03 s; the review found them
non-monotonic across 50 in a first draft with shorter runs). The engine reads
`ADEC_T`, MEG_T's format, 34 rows at ADEC −2, 2, …, 130, so ADEC 50 falls exactly on row 13, which *is* MEG_T's row 0:
without dEVILish, and at ADEC 50, the output is v7.8's sample for sample (1,600 frames of accented and plain notes,
the assembly, SPD NORM and SLOW: same sha256). Measured on the engine's own steps: ADEC 0 reaches 10 % in 30.1 ms,
127 in 2,995 ms; each step of the knob lengthens the time by 3.1–4.7 % (49 / 50 / 51: 192 / 200 / 207 ms). Memory
+8.7 KB (`O3_ADEC_T`, 34 × 64 longs); cost the same as v7.8 within ±1 % (a held accent 4,543 → 4,583 instructions a
frame at ADEC 10, 4,725 → 4,785 at 120: the table's tail is read for longer). Rule and tests: the project note
`OCTA303_v79_tarature.md` sec. 3; `adec_*` and `bit_exact_accent_circuit` in `test_octa303`.


### v7.9 (7 Nov 2026): the TB303* sample way in is gone

A FLEX track whose sample is named `TB303*` no longer plays the 303: it is an ordinary FLEX track, its sample
rendered by stock, its PLAYBACK page stock's, its CHROMATIC keys stock's. The TB-303 machine is the only way
in. Gone from `octa303.s`: the name match (`o3_marker`, `o3_basename`, `o3_name`), the sample's PLAYBACK clone
(`o3_pgdesc`, `o3_over`, the record's first half of `o3_desc`), v6.9's knob stamp for a new sample track
(`o3_stamp`, `o3_lastslot`), the semitone keys and the neutral SETUP for such a track (`o3_setup_neutral`), and the
dead-voice check that only a sample track needed. 6,520 → 6,274 lines; ~480 bytes of runtime data fewer.
The machine is the same sample for sample: `test_octa303`'s scripts, written in v6.x's vocabulary (a TB303*
file names the carrier), now play their carrier on the machine (SETUP's WAVE = the carrier, the rest
`SETUP_NEUTRAL`, which is what the sample's track played), and every bit-exact run passes against an
unchanged `ref303.py` (125 of 125); the same converted scripts run on v7.9's engine before this change pass
115 of 125, every bit-exact run among them: the ten that fail are the checks of what changed (the TB303* sample
now stock: 7; the machine's record now at the start of `o3_desc`: 3), so the machine's path did not move. New checks: `tb303_sample_is_stock_*` (samples, the DSP record, the retrig count and the
positions as stock leaves them), `page_tb303_sample_is_stock_*`, `machine_taken_away_releases_at_the_next_start`;
`chrom_stock_for_other_tracks` now includes TB303* files. Cost (simulator): a note start on a plain FLEX track
123 → 44 instructions; a machine frame 4,446 → 4,435 at its start and 4,110 → 4,105 after (the two checks
only a sample track needed). `tools/hw/ot_cfmatrix.py`'s OCTA-303 layouts are signed machines now, at most
two in a Part.

### v7.8 (6 Nov 2026): the MEG and the accent from the circuit (V8A)

Three parts of the voice now follow the Roland service notes' main board (= the x0xb0x netlist) with **no number
fitted to a recording**; everything else is v7.7's (claude/OCTA303_blocco3_accento.md, V8A).

- **The MEG (filter envelope)** is C62 1 µF discharging through R138 68k (+ VR6, DECAY) into the diodes D28/D29
  and the node R117/D26, read through the Q40/Q41 Darlington loaded by the Q39 JFET (`tools/octa303/o3meg.py`).
  The diodes stretch the tail: the decay is no longer exponential (simulated down to ~−33 dB of the peak; below that each
  row's last factor is held, 🟡 an extrapolation). Two numbers set it, both Roland's ("DECAY VR
  MIN T = 200 ms, MAX T = 2.5 sec"): the diodes' Is (1N4148 / 16.3) so that DECAY 0 (and every accent) falls to
  10 % in 200 ms, and VR6's part ×0.894 so that DECAY 127 does in 2.5 s; between them the pot's law is v7.7's.
  The engine steps it with a factor a frame from `O3_MEG_T`: 33 DECAY rows (0, 4, … 124, and an extrapolated row
  so that 127 is exact) × 64 levels (6 an octave, the level's position from `ff1` and the mantissa), linear in
  both, 8.4 KB. `meg_cache.json` holds it (~2 min in Python to rebuild).
- **The accent** is the circuit: the push to the filter VR7 → D24 → R46 → VR4B → C13, VR4B's wiper → R72 →
  N134, and the current into the VCA VR7 → R119 → C36 → R120 → D27 → the BA662A's pin 1 (a junction), the gain
  ∝ (I_Q31 + I27) / I_Q31 with no threshold or ceiling invented. Backward Euler on C13 and C36, two sub-steps a
  frame (as the twin); D24 is one diode in series with Re(ACCENT) + RA(RES), C36's step and D27 one diode in
  series with R120 + 1/G, each from a table of y = i·R (`O3_AC_F`, `O3_AC_F27`, 32.8 mV apart). VR7 and VR4B
  follow VR4A's S track (C2c, width 0.16). The accent sweep and VCA curves fitted in v7.3–v7.5 are gone
  (`TB_ACH`, `TB_SWDIRECT`, `TB_SWCAP`, `ACC_AMT`, `TB_ACC_VCA`). At rest (no MEG in, C36 and I27 at 0, C13's step
  0) the sub-steps are skipped: the shortcut gives the same numbers (gated).
- **Pin 6 is asymmetric and lower**: the negative side's limit L = "2.265 V" in the twin's scale (the centre of the band
  where the strongest accents' negative peak sits where Din Sync's does, −9.5…−8.2 dBFS), the positive side
  1.46 L (`O3_P6_FP`). Against v7.7 (3.951) the negative ceiling is 4.8 dB lower and the positive 1.5 dB lower; DRIV's
  limits follow it (`DRV_C` = `P6_F[256]`), so **projects saved with DRIV above 0 sound different again**. DRIV's own
  positive side (1.8 × the negative, the output mixer) now sits on top of pin 6's 1.46.

Measured on the twin (training | exam; from C2c, and the control from C2c′ with its own thresholds, both passed):
cells from 40 ms 1.655 | 1.667 → **1.340 | 1.343** (C2c′ 1.374 | 1.409); accent step 1.579 | 1.422 → **0.920 |
0.862**; the five strong exam accents +1.12 → −0.86 dB; Zac's map 1.946 | 2.075 → 1.741 | 1.737; brightness 0.1363 |
0.1388 (threshold 0.13727 | 0.14718). Engine against the twin (control 8): cells from 40 ms 1.334 | 1.335,
brightness 0.1366 | 0.1417, accent 0.917 | 0.853: within 0.004–0.008 on the cells and +0.003 on the exam's
brightness, the gap held in a few notes at CUT/RES 127 (as in C2c, per note); 🟡 with the MEG and the accent computed
exactly (floats) in the engine the brightness gap stays, so it is not these tables. Accepted (Marko, 6 Nov): the engine's
numbers pass V8A's thresholds too; the cause goes to v7.9. Assembly = engine bit for bit
(the suite, accents in a row with dEVILish's SPD FAST/SLOW, ADEC and SELF included).

dEVILish: **ADEC 50** (its default) is now the circuit's MEG (`DF_ADEC[50]` = 0); away from 50 the accents keep
v7.7's exponential, 30 ms … 3 s. The two do not join: at 49 and 51 an accent reaches −40 dB in ~355 and ~380 ms, at 50
(the circuit's tail) in ~1.5 s, so a lock or an LFO crossing 50 jumps. (v7.9: no longer; see above.) **SPD** acts on C13, 🟡 an interpretation (Whittle describes the modes, not the parts): FAST C13 / 4,
NORM the 303, SLOW C13 × 4 and its part of the push read doubled. **SWP SELF** still takes the MEG out of the accent circuit.

Cost (simulator counts, instructions a 16-sample frame, machine track, v7.7 → v7.8, mean / worst frame): a plain note
with the accent circuit at rest 3 990 / 4 025 → 4 051 / 4 110 (+1.5 %, the MEG's table); an accented note at
CUT/RES/ENV 127 4 191 / 4 241 → 4 727 / 4 790 (+12.8 %); with dEVILish SPD SLOW 4 071 → 4 602. The circuit stays
active after an accent until C13 settles (the review's measure, ACC 127): 0.7–1.1 s (NORM), 2.3–3.2 s (SLOW),
0.15–0.27 s (FAST); the notes in that time cost as an accent. 🟡 So a pattern with an accent every bar runs the full
circuit nearly all the time: two machines measured 65.5 % of the frame interrupt in v7.7 (above), ~74 % expected on
accents (65.5 × 1.128). To be measured on the unit with an accented pattern.

### v7.7 (5 Nov 2026): the BA662A's pin-6 ceiling replaces the digital output ceiling

The VCA's OTA (IC15) drives its output, pin 6, into (R127 + R129) ∥ R128 = 52.5 kΩ from the 5.333 V
reference: the voltage is the control current × 52.5 kΩ and cannot leave the supply. Only the strong
accents reach it (a normal note at full drive is 2.52 V). v7.7 puts that knee after the VCA multiply,
o / (1 + (o/L)⁴)^¼ as a 257-point table, L = 3.95 V (fitted on Din Sync with the exam notes held out,
range 3.8–5.0 V), and removes the fitted digital output ceiling. Every other number is the clean refit
P2K2. Measured on the twin (training | exam, the exam notes never seen by the fit): accent step 1.673 | 1.662
→ 1.591 | 1.409 dB; the five strong exam accents +1.94 → +0.97 dB too loud (a second run from the other
base: +2.12 → +1.56); cells from 40 ms unchanged (1.735 | 1.736 → 1.732 | 1.732). Engine = twin
(control 8) and assembly = engine bit for bit (114/114). Cost ~+0.5 % (simulator counts).

**The R122 branch follows RES on an S track (C2c, 6 Nov 2026).** RES is VR4, a dual pot; R122 (on the VCA's
side) hangs on VR4A's wiper. The weight of that branch per RES step is now the wiper of an S-taper track
(logistic, w 0.16) loaded by 50 kΩ, the same law on the twin and in `o3tables.VP_W2`; nothing was fitted
(the fitted variant, T9S, hit its range limit on the second base and did not pass). Measured on the twin
(training | exam): cells from 40 ms 1.732 | 1.732 → 1.655 | 1.667; Zac's map 2.044 | 2.147 → 1.946 |
2.075; accent step 1.591 | 1.409 → 1.579 | 1.422. Engine = twin within 0.0012 (control 8); in
`octa303.s` only the 128 numbers of `O3_VP_W2` change (0 instructions).

**DRIV** (SETUP) is the 303's VOLUME knob, VR8, turned past the position Din Sync's recording was made at,
into the output mixer Q33/Q34 (`o3tables` `DRV_*`):

- **DRIV 0 = Din Sync's position: the block is skipped and the sound is bit for bit the sound without it**
  (400-voice engine render and 40 seeded scenarios with SETUP moved, same sha256 as C2c).
- Above 0, after today's ceiling C (pin 6's asymptote): a gain 0 → +10 dB, linear in dB over 0..127, then
  a soft asymmetric saturation per side, K + (L − K)·tanh((|x| − K)/(L − K)) above the knee K = 0.95 L,
  the negative side L− = C and the positive side L+ = 1.8 L−. The tanh is a table of 257 points (u = 0..4,
  64 a unit), linear between points; |x| − K is held at 4 (L − K) (tanh 4 = 0.9993).
- Cost (simulator counts, instructions a 16-sample frame, machine track): DRIV 0 −3 against C2c; DRIV
  64/127 +117 (mean) on a quiet note, +134…+155 (mean) and +348…+379 (worst frame) on a loud accent, still under v7.6's digital drive at the
  same settings (its worst frame 4 654, this one 4 623). Every product fits 32 bits (swept, DRIV 1..127).
- **Projects saved with DRIV above 0 sound different from v7.6 and earlier**: DRIV was a digital drive up to
  +18 dB into −0.80 dBFS; it is now at most +10 dB into the mixer's ceiling. DRIV 0 is unchanged.

### v7.6 (4 Nov 2026): Q8's square and the VCA's OTA, fitted on two real 303s

Two parts of the circuit the voice did not have, from the Roland service notes' main board (= the x0xb0x
netlist):

- **Q8, the square shaper.** The saw (Q28's source) drives a 2SA733 PNP through R35 100k and a speed-up path
  C10 0.01 µF + R34 10k; the emitter sits on R45 22k to +12 V with C11 1 µF to ground, the collector on R36
  10k to +5.333 V. `tools/octa303/o3q8.py` solves it as a circuit (the base-emitter exponential, hFE,
  saturation) and takes its steady-state cycle at each semitone: the top droops as C11 discharges (more on
  low notes), one edge is sharp (the saw's reset), the other falls slowly, and the duty follows the pitch
  without a table of its own: the high part 60 % of the cycle at C1, 53 % at C3, 34 % at C5 (Whittle measured
  71 % low to 45 % high: the same direction, a lower level; 🟡 not reconciled). The engine plays it as a smooth part (128
  points a cycle, band-limited per semitone) plus `SQK` times the saw, so the one hard edge has the saw's
  polyBLEP: its aliasing is the saw's (−36 to −47 dB, C1–C5), each row band-limited at its top. The 303's square edges are softer than the
  circuit alone gives; the v6.9 one-pole stays on it, refitted (~6 kHz). It replaces `SQ_TH`, `TB_KSQ`.
- **IC15 BA6110, the VCA**, is an OTA: its input pair gets ~3 % of the filter (R121 220k ‖ R122 100k into
  R124 2.2k), enough to round the peaks: `OTA_V · softclip(o / OTA_V)` before the VCA.

Fitted (CMA-ES) on Din Sync's 400 notes, tinyloops' accents in a row and, for the first time, a second real
303: rolandclan's 30 one-shots (https://www.rolandclan.com/library/tb-303, 2006, knobs unknown: each sample at
the knobs that match it best). Q8's numbers come out physical: the saw swings 4.39–9.96 V, hFE 329 (the 2SA733's P
rank: 200–400).

Measured again on 4 Nov 2026 after an audit of the measuring tools (two independent reviews; what changed is
below). The float twin, now with the engine's ladder-clip point, equals the integer engine (cells within 0.002 dB,
brightness 0.002 oct, accent 0.02 dB; first 15 ms of the notes −40 dB apart, median):

| | v7.3 | v7.5 | **v7.6** | the 303 against itself |
|---|---|---|---|---|
| Din Sync cells (dB), all windows | 2.53 | **2.40** | 2.44 | 1.90 |
| Din Sync cells (dB), from 40 ms | 2.02 | **1.86** | 1.95 | 0.81 |
| Din Sync brightness (oct) | 0.179 | 0.170 | **0.156** | 0.092 |
| Din Sync accent step (dB, mean of 8 VCO phases) | 2.12 | **1.70** | 1.71 | ~0.40 |
| rolandclan, 30 one-shots (dB from 40 ms, best knobs) | 1.73 | 2.05 | **1.54** | — |
| … 16 squares / 14 saws | 1.80 / 1.64 | 2.36 / 1.70 | **1.55 / 1.54** | — |

What the audit changed, and what it retracts:
- **The 303 against itself**, scored as the model is (the 316 repeat pairs, the common mask): brightness 0.092,
  not 0.182 (that used each side's own mask); cells from 40 ms 0.81 dB. The first two windows depend on the
  VCO's phase, random in the recordings, and make most of the 1.90. The model is not at the 303's floor:
  ~1.1 dB of cells from 40 ms and ~0.06 oct of brightness remain.
- **tinyloops** (retracted: every tinyloops number given for v7.3–v7.6, 0.130 / 0.078 / 0.049 and the 8-phase
  0.157 / 0.093 / 0.074): the recording plays 35.70 Hz in 4,941-sample steps (measured; the term assumed
  35.42 Hz), 4.000 cycles a step, so every real note meets the saw at one phase, and the tracker's onset lands on
  a saw reset some time after the note starts. That time cannot be read from the recording reliably (two ways
  tried: the fundamental's phase, the energy's trough before the onset); played at 35.70 Hz the twin's error
  runs 0.04–0.64 oct with the start phase alone, more than the versions differ. 🟡 No tinyloops number stands
  until a measure that does not hang on that phase exists; v7.5's accent stage was chosen on the old one.
- **Din Sync's pitch** is 65.62 Hz (measured, 24 notes, 65.61–65.64), not C2: the model plays 65.643 Hz (the
  engine's 1/64-semitone grid). rolandclan's samples are C2 (±0.13 st, one −0.30) and stay there.
- **The accent step** is the mean over 8 VCO phases (it was one phase, 0.25, the luckiest of 8 for v7.6:
  1.668 there).
- **rolandclan**: the knob search started from one grid point and stopped in local minima (knobs found for
  another model beat it on 11 of 30 samples, by up to 1.1 dB); it now starts from the 4 best grid points and every
  knob set any search found. The fit term used knobs searched for an older model.
- **The twin**: v7.3's ladder-clip operating point was missing (only CUT, RES, ENV all near 127 felt it, up to
  1.4 dB in the first 15 ms); the fit's square-edge lowpass was not read back by the report script.
- Retracted from 4 Nov morning: the "integer engine" row (cells 2.29, brightness 0.172) and "~2 dB above the twin
  in the first 15 ms": the check's renderer ran its pre-roll 17 samples short.

Cost: 3,996 instructions a 16-sample frame (saw; 4,540 square), v7.5 3,592 / 3,937: the OTA's soft clip on both,
the table on the square (simulator counts).

### v7.1 (23 Oct 2026): the sites, read from the user's 1.40C

- ✅ The LFO PMTR formatter `0x4003bf64` (LFO page descriptor `0x400d37be`, slot 6's formatter)
  takes a PLAYBACK destination's names from `PB_TABLE[the track's machine]`; the detour at
  `0x4003bff0` hands it OCTA303's machine record on a signed track (Zac Kyoti's BLACKPYRAMIDS_303
  hooks the same site for its own row, MT13: the two modules already conflict).
- ✅ The held-trig layer's key table `0x400becda` sends UP and DOWN to `0x400434d8`, which opens
  the sample-lock list for the first held step on a STATIC or FLEX track; the detour at its entry
  takes the keys on an OCTA-303 track. The TUNE lock is written as the stock knob-lock writer
  (`0x40050e60`) writes it: the bank blob and its battery-backed copy (`0x1001614e + …`), then
  `bank + 0x9b332` and `0x100f8598`, `0x40027e00`, `0x4009da20(track)`.
- ✅ The trig keys go through a dispatcher `0x40060b58(key, event)`: a press to `0x40050f20`
  (FUNC + TRIG sets the trigless lock there: under the port, no write in `0x4005fb44` and the bit
  already set at its entry), a release to `0x4005fb44`. The dispatcher's entry keeps the track's
  trigless masks (+8 trigless trigs, +16 trigless locks) at a press; `0x4005fb44`'s tail before
  `jmp 0x40027de4` (`0x40060b3e`) compares them, and a step that became trigless gets its note.
- ✅ `test_octa303`: the three routines from their source text (octave up and down, the edges, the
  toast's note, the battery-backed copy, the stock path on FLEX and MIDI tracks; the slide's note
  from a trig, a slide, the Part, around the end of the pattern, a step already locked, no new step,
  another track).
- ✅ Under the port, `tools/octa303/port_o3keys.py` (the panel, a project, 23 Oct 2026): TRIG 1 + UP 64 → 76 and the toast `C4 +OCT`; FUNC + TRIG 2 a trigless lock with TUNE 76 at once; TRIG 3 + DOWN 64 → 52; a FLEX track's TRIG + UP opens the stock LOCK list and writes no lock; LFO SETUP shows `PB TUNE`.

### Under the port (✅, `ot_emu`, the user's OS 1.40 image, 19 Oct 2026)

- OCTA-303 appears as row 5; choosing it writes the signature, the defaults, the shadow copy and
  the live lane; choosing another machine clears the signature; reopening highlights OCTA-303.
- SETUP shows WAVE GATE FINE SLID DRIV ACCV, the encoders write the right bytes; WAVE and GATE step
  like stock LOOP and SLIC (same handler, same count).
- PLAYBACK shows TUNE CUT RES ENV DEC ACC; the footer reads `OCTA-303▸OCTA-303`.
- The validator called on a Part with a signed track keeps FINE/SLID/DRIV = 100/90/120; on an
  unsigned FLEX track the same bytes clamp to 1/1/3.
- Audio with an **empty** FLEX slot: C3 at 130.8 Hz; GATE 303 ≈ 58 % of a step; SQR has the odd
  harmonics (H2 −22 dB). With a TB303.wav in the slot, WAVE still decides (v7.9: the file is never read).

### On the unit

- ✅ v6.3–v6.9 played for hours on the author's MKI (two or three OCTA303 tracks, with `devilish` and
  `distorx`, image `acidtrack`).
- ✅ v7.0 on the author's MKI, image `ACIDV70` (BUILD 87, remix `acidtrack`), 19 Oct 2026: OCTA-303 chosen
  from the machine list with the panel keys; the SETUP page edits as designed; the project saved,
  power-cycled and reloaded with the machine and its SETUP values intact; GATE 303 by ear. A 7.5-minute recording (two OCTA-303 tracks, one with `devilish` and
  `distorx`, one with `devilish` and a filter, `distorx` on claps): peak −2.2 dBFS, level steady at
  about −17 dBFS RMS, no dropouts.
- ✅ v7.1 on the author's MKI, image `O3V71` (BUILD A0, remix `octa303`), 23 Oct 2026, by ear and eye: held trig + UP / DOWN moves the note an octave (several held trigs at once; a note at C5 stays, no toast), `C4 +OCT` on the screen; FUNC + TRIG on the next step makes a slide that ties into the previous note, held and turned to another note it slides there, and + UP lifts it an octave; a FLEX track's TRIG + UP opens the sample list as before; LFO SETUP lists TUNE CUT RES ENV DEC ACC; the locks survive save, power-cycle and reload.
- ✅ ACIDV71 (BUILD 88, same OCTA303), 20 Oct 2026: two OCTA-303 tracks with `devilish`, beside five
  `distorx` (one on T1): no clicks, no slow-downs, by ear.
- Not measured: the ColdFire load (CF METER). The author has run three OCTA303 tracks for hours.

## Inferred

- 🟡 **ColdFire cost.** v7.6: ~4,000 instructions per 16-sample frame per voice (saw), ~4,500
  (square); v7.5 ~3,600 / ~3,900; v7.3 ~3,200 / ~3,500, ~4,700 with Devil Fish FM + MUFF (simulator
  instruction counts). At ~1.77 cycles an instruction (`waveload`'s hardware calibration) that is ~8 %
  of the 363 µs frame per voice. Falsified by CF METER on the unit.
- 🟡 The signature bytes (NEIGHBOR's first three PLAYBACK bytes) are read by no stock code while the
  track is FLEX; `analog-bassdrum` relies on the same assumption. Falsified by a signed track
  losing its signature on a stock path (save, load, copy/paste Part, reload).

## Open

- The ColdFire load on the unit (CF METER).
- `SYNTH MACHINE` and `octa303` cannot share an image (the FLEX renderer and the page resolver).
  `analog-bassdrum` can since 28 Oct 2026, through HOOKS (`machine_rows`: OCTA-303 on row 6 of a
  scrolling list, its renderer after ANALOG BD's): both UI gates pass on the one image under the
  port, not flashed. A project saved on an image without ANALOG BD (OCTA-303 on row 5) opens as
  OCTA-303 on row 6 in one with both: the Part stores FLEX and the `T` `B` 1 signature, never the
  row, and `o3_type` gives the row from the signature (🟡 from the code; not run across two images).
- The first 15–40 ms of an accented note are still ~1 dB further from the 303 than the 303 is from
  itself.
- #1011, point 5 in part (v7.5 above): at ACCENT 100 % the accented note's first 40 ms still peak
  +20.0 dB over the plain note where the 303 peaks +15.6 dB (the energy is right: +16.6 / +16.7 dB).
- dEVILish's WHST / SELF still lock to fs/4 when their oscillation is swept to the top (v7.3 leaves
  them as they were); 2× oversampling of the ladder above ~fs/8 would cure both modes.

## Credits and sources

- **Din Sync**, *TB-303 reference recordings for x0xb0x* —
  http://www.dinsync.info/2010/02/tb-303-reference-recordings-for-x0xb0x.html — the calibration target.
- **tinyloops**, *Programming the Roland TB-303* — https://tinyloops.com/tb303/index.html — the example
  recordings (the resonant "drops", "saw with only accents") used for the ring decay and the accent.
- **Robin Whittle**, *Devil Fish* manual and "TB-303 unique" notes (Real World Interfaces) — the
  gate length (3.5 of 6 clocks), the accent RC values (47k × 0.033 µF; 47k + 100k with 1 µF), the
  slide RC, the square's duty by pitch, every Devil Fish modification in `devilish`. https://www.firstpr.com.au/rwi/dfish/ ; the
  *User Manual for the Devil Fish mods to the TB-303* (2019) is linked there.
- **Tim Stinchcombe**, analysis of the TB-303 diode ladder ("diode2") — the transfer function the
  low-frequency behaviour was checked against. https://www.timstinchcombe.co.uk/index.php?pge=diode2
- **Roland**, TB-303 service notes — DECAY range, ENV MOD taper, slide capacitor.
- **Tim Hastie**, SYNTH MACHINE 2.9 (https://github.com/timhastie/octatrick-modules, MIT) — the FLEX integration
  this module re-does for one voice (renderer entry, START resolution, PTCH/RATE neutral, pinned
  positions, the clean retrig byte, the PLAYBACK page clone) and the semitone tuning system.
- **repeat98** (https://github.com/repeat98), `analog-bassdrum` (this repository) — the measured machine-list seams the OCTA-303
  row uses.
- **Sam Banks**, octabam — the build, the port, the remixer.

## Gates

`tools/octa303/sim/test_octa303.py` and `tools/verify/verify_octa303_ui.py` (the panel under the
port: select and edit, unsign, the validator; needs `OT_PROJECT`), both in the manifest;
`remixes/test/octa303` carries the module alone. `make check REMIX=octa303` with a project
(`OT_PROJECT`) passed on the author's machine, 21 Oct 2026 (`afa20426`, before its rebase onto
`828edcac`): test_octa303 91/91, verify_octa303_ui (select, unsign, validate), verify_set 0 failures.

The manifest declares it in conflict with SYNTH MACHINE, ANALOG BD and BLACKPYRAMIDS_303 (the same
machine row and FLEX seams); `make modules` shows the matrix. The Devil Fish knobs need the companion
FX module [`devilish`](../devilish/README.md); without it every OCTA303 track is the plain 303. Passed in `make check REMIX=acidtrack` on the
author's tree, 20 Oct 2026.
