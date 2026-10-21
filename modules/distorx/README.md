# `distorx` — DISTORX

Two pedals in one insert: the BOSS SD-1 Super OverDrive (1981) and the
Pro Co RAT (1978), with the Turbo RAT's LEDs as a third MODE. MODE picks
the pedal; changing it fades to the dry signal and back in about 3 ms, so a
scene or a p-lock can switch pedals without a click. Built for a TB-303
line (OCTA303), fine on anything.

> **T1:** v7 tore track 1's read-back block under load (16-sample bursts of junk, "On the unit").
> v9, a quarter lighter and without PAD, played clean on T1 on the owner's MK1 (20 Oct 2026,
> "On the unit (v9)"): one session so far. If junk returns on T1, report it with the load.

**MODE starts at OFF** (v8): nothing runs and the frames pass untouched, so
DISTORX can be put on a track in the middle of a set and a pedal faded in
when wanted. **MODE SD-1 is SUPER OD's circuit** — the same constants from
the 1981 service notes, the same arithmetic — run at the sample rate since
v8 (SUPER OD runs the clipper at 2×). FX id `0x0a`, the one id free in
octabam on 20 Oct 2026; until then DISTORX sat on SUPER OD's `0x1b` (BBD's
now), so a part saved with the old id needs DISTORX chosen again. A part
saved before v8 reads its MODE one step lower: SD-1 → OFF, RAT → SD-1,
TURB → RAT.

## Knobs

| page | slot | name | range | what it does |
|---|---|---|---|---|
| 1 | 0 | LEVL | 0–127, default 64 | LEVEL, linear; 64 ≈ the input's loudness at DRIV 64 in every MODE (the RAT's make-up below) |
| 1 | 1 | TONE | 0–127, default 64 | SD-1: TONE. RAT: FILTER, **turned round**: right is bright in every MODE (the real FILTER darkens clockwise) |
| 1 | 2 | DRIV | 0–127, default 64 | SD-1: DRIVE, 18–47 dB. RAT: DISTORTION, the 100k-A pot: 0–67 dB |
| 1 | 3 | IN | bipolar, default 64 | how hard the track hits the pedal: −12 … +12 dB; 0 dBFS = 1 V at the jack |
| 1 | 4 | MIX | 0–127, default 127 | dry/wet: 127 is the pedal alone, 0 an exact passthrough |
| 1 | 5 | MODE | OFF / SD-1 / RAT / TURB | OFF (default: nothing runs) or the pedal (a value past TURB, as an LFO can send, reads as TURB) |

Slots 0–4 are SUPER OD's.

## The SD-1 (MODE 1)

SUPER OD's README is the whole story: the input couplings, the clipping
stage with DRIVE and the asymmetric 1S2473 diodes in its feedback (the diode
law solved exactly, at 2×), the TONE stage by nodal analysis, the output
coupling and LEVEL. Shared callees replace some of its straight-line
per-block code (the knob stretch, the LN lookup, the TONE polynomials as a
loop over a P table, the halfbands); the arithmetic is word for word the
same. Until v8 the gate held the output to SUPER OD's model bit for bit;
since v8 the clipper runs at 1× ("v8" below).

## The RAT (MODES 2 and 3)

Modelled from the parts list and schematic of ElectroSmash's *Pro Co Rat
Analysis*:

| stage | parts | as computed |
|---|---|---|
| input coupling | C1 22 n, R2 1 M | HP 7.2 Hz, at 1×, a 48-bit state |
| — | R3 1 k, C2 1 n | 159 kHz: left out (−0.07 dB at 20 kHz) |
| LM308 stage | DISTORTION ‖ C4, R4 + C5, R5 + C6, C3 30 p | v− = q vo + c0 from the two ground legs (trapezoidal companions, exact); the op-amp an integrator of 0.8 MHz gain-bandwidth, trapezoidal where it is not stiff (θ-method: θ = ½, raised only where the closed loop's own pole is stiff, at DISTORTION near 0), the step held to the slew rate (0.3 V/µs), the output to ±3.5 V |
| clipper node | C7 4.7 µ, R6 1 k, D1/D2 to ground, FILTER + R7 1.5 k, C8 3.3 n, C9 22 n into R8 1 M | one node: v + Rp·Is(e^(v/N) − 1) = u per side, solved exactly — v = u + N k − N ω(U), U = u/N + k + ln k (ω the Wright omega, tabulated: 113 words, 16 segments an octave of U + 12); the FILTER network the node's load, C9/R8 included |
| output | the JFET (unity), C10 1 µ into VOLUME 100 k | HP 1.6 Hz, at 1×, a 48-bit state; then LEVEL × the make-up |

The LM308 stage and the clipper node run at 1×, one straight-line callee
called once a sample. (Until 15 Oct 2026 they ran at 2× through SUPER OD's
11-tap halfbands; on the MK1 that cost too much on core 1, "On the unit".
The owner A/B'd the two by ear, "almost imperceptible", and chose 1×.) At
1× the integrator's W is ~114 and the slew ~6.8 V a sample: W is applied as
W/128 with one more shift, and the slew compares the step at volts/8.

**TURBO** is the same circuit with red LEDs for D1/D2 (the LTspice
`LedRed` model: Is = 93.2 pA, n = 3.73; about 1.6 V at 1 mA).

## Assumptions

What the analysis does not give, and what was chosen:

- **LM308 gain-bandwidth 0.8 MHz**, fitted to the analysis's own clipping
  amplifier curve: 64.4 dB at 714 Hz at full DISTORTION (the curve: ~64 dB
  near 700 Hz), 37.9 dB at 10 kHz (37.5), 31.9 at 20 kHz (31); the 1 k curve
  24.7 dB at 1.5 kHz (24) and 8.2 dB at 60 Hz (8). The datasheet gives no
  number in text.
- **Slew rate 0.3 V/µs** (the analysis, from the datasheet's figure).
- **Output swing ±3.5 V** around the 4.5 V bias (the datasheet's typical
  1 V short of each rail at ±15 V).
- **C4 left out.** With the gain-bandwidth modelled, C4 (100 p across
  DISTORTION) moves the clipping amplifier's response by at most 0.5 dB
  (1 kHz, full DISTORTION) and 0.2 dB above 5 kHz; leaving it out drops a
  state and a division.
- **The derivative held in a word**: the integrator's slope from the last
  sample is stored as a word (±4 V a sample) instead of clamped to the slew;
  the float circuit clamps it, and the two differ by −57 … −82 dB.
- **1N914** as the SD-1's 1N4148/1S2473 model (Is = 2.52 nA, n = 1.752).
- **Pots**: DISTORTION, FILTER (and VOLUME) are 100k-A: an exponential law
  through 0, 10 % at the middle and 1 (33 points, interpolated).
- **The JFET buffer is unity** (a source follower with R9 10 k).
- **Make-up after LEVEL**: 0.51 (RAT), 0.20 (TURBO), so that the three
  modes meet at the same loudness at the default knobs on an acid line
  (−16.5 … −17.3 dBFS RMS). The real Turbo RAT is louder than the RAT; here
  it is not, so a MODE change does not jump in level.

## The MODE fade

d ∈ [−1, 0] steps 1/128 a sample: towards −1 while the knob asks for
another pedal, towards 0 otherwise; MIX is multiplied by (1 + d), exactly
MIX when d = 0. At d = −1 with the knob on another pedal the block zeroes
every state slot ($12..$3c) and the new pedal starts from rest. So a MODE
change is 2.9 ms out to the dry signal, the switch, 2.9 ms back in; with
MIX at 127 the dry signal is heard for those few milliseconds. The effect
starts the same way: d = −1 at init, so it fades in.

## Silence

Silence in, exact zeros out after 100 ms, every MODE. After a loud burst
the SD-1 is back to exact zeros within 0.5 s. The RAT keeps a charge on C7,
which only the diodes can bleed off (C8 and C9 block every other path, as on
the pedal): its slow, subsonic relaxation reaches the output through the
1.6 Hz HP at −95 dBFS after 2 s and about −118 dBFS after 10 s.

## Measured

✅ in a standalone DSP56300 harness (the vendored emulator with
`tools/patches/dsp56300.patch`, garbage in every register and in the whole
r7 block before init, fresh garbage in the scratch registers before every
call), 14 Oct 2026, every gate of `tools/verify/verify_distorx.py`:

- **Bit-exact** against `distorx_ref.fixed()`, every MODE: defaults, every
  knob at both ends, a full-scale square, a split block, page words with
  bits 8–15 dirty (an LFO's), MODE changed mid-render (SD-1, RAT, TURB, back,
  a 3-block RAT, with a split), MODE values past TURB.
- **SD-1 = SUPER OD**: 0 LSB against SUPER OD's own model after the
  128-sample fade-in, on an acid line, a square and noise; the service
  notes' WAVEFORM CHECKING page as SUPER OD measured it (1.21 / 1.22 / 0.74
  Vp-p against 1.2 / 1.2 / 0.8).
- **The analysis** (the float circuit's LM308 stage): 65.0 dB at 700 Hz at
  full DISTORTION (~64 dB near 700 Hz); 24.8 dB at 1.5 kHz and 8.2 dB at
  60 Hz with 1 k (24 and 8).
- **FILTER full left**, through the module, small signal: −3 dB at 543 Hz;
  the whole network (R6 + R7 + 100 k, C8, C9/R8) says 539 Hz. The
  analysis's 475 Hz is R7 + 100 k against C8 alone.
- **The diodes' level** at full DISTORTION, FILTER bright: 0.80 V peak at
  the gate (1N914), 1.99 V (red LEDs); the float circuit at 1× says the
  same, at 8× 0.73 / 1.82 V: the sampled peak of a bright square at 1×. **Symmetric**: the 2nd harmonic of a
  sine at −72.6 dB (the SD-1's: −33 dB).
- **The circuit**: against the float circuit at 1× (exact diode law, the
  slew clamp in float), −64 dB at the defaults, −43 dB at full DISTORTION,
  −78 dB at DISTORTION 0, −49 … −64 dB elsewhere; against the circuit run at
  8× and band-limited back (the ground truth), −49 dB (RAT), −53 dB (TURBO),
  −42 dB at full DISTORTION (SUPER OD: −31 … −44; the 2× core was −40 … −56).
  On an acid line with FILTER bright: −35 … −41 dB at 1×, −43 … −48 at 2×.
- **MIX 0** is an exact passthrough in every MODE with every other knob at
  an extreme.
- **The fade**: switching SD-1 → RAT → TURB → SD-1 on a 110 Hz tone makes no
  step larger than the pedals' own (0.0995 FS against 0.0993).
- **Cost**: 1,071 words of code + 515 words of table (WF 241, LN 65, EXP 33,
  TAPER 33, TP 18, OM 113, MK 12) = 1,586 words; SUPER OD was 919.
  Instructions a block in the harness (decode, loop and fade, no stall):
  SD-1 5,480, RAT/TURBO 4,537 (8,505 with the 2× core). By
  `tools/build/cycle_count.py`: the SD-1 loop 381 cycles a sample (SUPER OD
  345: the shared callees' calls, the fade and the nop at LA).

## Where it goes

1,586 words is one code stream, so it needs ONE harvested run that long.
CHORUS + PLATE REV + SPRING REV is 1,743 words up to the 35 SPRING REV words
DARK REV still calls (P:0x01586), which cut the run there: DISTORX fits with
157 to spare. A remix that keeps DARK REV and also places another module
of more than 157 words gives up a second, separate run for it. aCiDtRacK
gives up PHASER: its 207 words join EQUALIZER's 282 (dB666 is on
EQUALIZER's id) into 489, where dB666 (297 + 66 words) goes.

## On the unit

- **ACIDDTX1** (aCiDtRacK, MK1, 14 Oct 2026): every MODE sounds as rendered,
  the MODE fade is clean, dB666 and the rest of the remix unchanged. One
  defect: a **16-sample block of noise** now and then (about 200 in four
  minutes, in clusters at one phase of the pattern), on T1 and on T5, in
  every MODE. Measured on the owner's USB take: each is exactly one
  dispatcher block, both channels, not a copy of any other audio; L and R
  are identical before it and differ after it by up to 0.006 FS, dying
  away in ~0.5 s, so the junk passes through DISTORX's own state. With one
  DISTORX per core the load is far from any limit, and the harness renders
  bit-exact with every knob moving, fractional and dirty page bits included.
- **ACIDDTX2** (the same with a `nop` at LA in both sample loops): the same
  junk at the same rate. The LA cause is **retracted**; the `nop` stays (no
  loop ends on a change of flow, `verify_distorx` refuses one).
- **Where (✅ measured on the unit, 14 Oct 2026, 24-bit takes):** only on
  **T1**. T5 and T8 with the same kick, 130 BPM, every knob at 127: no junk
  block in 99 s. On T1: none without a sample playing (trigs or not); with
  one, bursts of junk blocks whose rate rises with the tempo (hundreds a
  second around 130 BPM). The junk is a 16-sample block, in pairs, at one
  phase of the block grid, holding wrapped ramps: a slow signal's low bits
  read as its high bits, the signature of the read-back's hi/lo words torn
  or shifted, not of DISTORX's arithmetic (bit-exact in the harness with
  every knob moving, fractional and dirty page bits, near-silent DC and
  noise in). The "L and R differ after it" above is retracted with it.
- **Cause (🟡 inferred from the above and the BusDelay record):** T1 is the
  first block core 1's ColdFire pull reads (`docs/firmware/DSP.md` "Frames,
  tempo, read-back"); the dispatcher's copy of the block right after
  DISTORX's rts lands inside that pull when DISTORX ends in its window,
  which moves with the machine's work and the sequencer. SUPER OD
  (shorter) ended before it.
- **Measured cost in the harness** (instructions a block, no stall):
  SD-1 5,480, RAT/TURBO 8,505 (the 2× core).
- **Workaround (image ACIDDTX3): PAD**, page 2, slot 6: wait PAD x 256
  cycles after the loop, before the rts (0 = none, 127 = 32,512 cycles,
  ~7 samples), the output bit for bit the same. Turned up on T1 until the
  junk stops, it measures where the window is; the value found becomes the
  fixed fix (T1 only, as BusDelay's 8,192-cycle pad). PAD costs core 1's
  budget, so it stays 0 on every other track.
- **ACIDDTX3 measured** (24-bit takes, 15 Oct 2026): on T1 in RAT, 130
  BPM, junk up to PAD 7, **none at PAD 8** (12 minutes, T1 and T5 with
  dEVILish: 0 junk blocks). PAD 10 and, another time, 12 **wedged the
  unit** (power cycle). With T1 at PAD 8, a second DISTORX on **T2** (PAD 0,
  so SD-1 by default) **wedged it too**. So core 1 has a hard limit just
  past the junk window; the 2× core put DISTORX at its edge.
- **The fix (image ACIDDTX4):** the RAT core at 1× (above): RAT/TURBO
  4,537 instructions a block, 47 % less, below the SD-1's 5,480. PAD reads
  at most 8 (10 and 12 wedged core 1). To find out on the unit: T1 in RAT
  and SD-1 at PAD 0 (the RAT now ends before the window, if the window is
  where the 2× measurements put it); then a second DISTORX on T2.

## v8 (18 Oct 2026): lighter, for T1

T1's junk blocks ("On the unit") come when DISTORX ends late in core 1's
frame; SUPER OD, shorter, never made them. v8 makes every MODE end earlier
and adds OFF. Instructions per 16-sample block in `dsp_host` (the owner's
audition dump with v8's code in it, an acid line, the default knobs):

| | v7 (ACIDV68) | v8, knobs still | v8, knobs moving | v8, the fade-in's blocks |
|---|---|---|---|---|
| OFF | — | 29 | 29 | — |
| SD-1 | 5,483 | 2,709 | 2,939 | 3,184 (the first 3,464) |
| RAT / TURBO | 4,540 | 3,801 | 4,140 | 4,276 (the first 4,665) |

What changed:

- **OFF**, MODE 0 and the default: the block returns after the MODE logic;
  the frames, processed in place, pass untouched. Leaving a pedal for OFF
  fades it out (2.9 ms) and then stops; leaving OFF for a pedal switches it
  in from rest and fades it in (2.9 ms), as any MODE change.
- **The SD-1 at 1×.** The clipper ran at 2× through SUPER OD's 11-tap
  halfbands, with vp delayed 5 samples to match them; now vf = F(h) and
  o1 = clamp(vp + vf) at the sample rate. Against the circuit at 8×,
  band-limited (an acid line): −39.7 dB at the defaults (2×: −41.5),
  −37.4 at full DRIVE (−39.2), −33.7 at full DRIVE and TONE (−35.4); 1× against
  2×: −37 … −44 dB. The owner chose 1× for the RAT by ear on 15 Oct.
- **A settled block** (d = 0, the knob's pedal on, MIX 127) writes the wet
  alone; MIX × (1 + d) would be 1 − 2⁻²³ (≤ 1 LSB of difference).
- **The knob decode is skipped** when LEVL, TONE and DRIV are the words the
  last decode read ($20..$22, $23 = valid; the init and every switch clear
  it). Words are compared whole, LFO fractions included.
- The halfbands (`dtx_up`, `dtx_down`) are gone: 1,064 words of code (v7:
  1,071), the same P table.
- Every instruction form v8 uses is one v7 already ran on the MK1.
- PAD stayed (T1 only, 8 at most); removed in v9, below.

**On the unit (v7 — v8 was never flashed — the owner's MK1, images ACIDV68 to ACIDV70, 15–19 Oct 2026):**

- On tracks other than T1: hours of playing, on claps and on two OCTA303 tracks with dEVILish,
  beside dB666 and the reverbs; no junk blocks. A 7.5-minute recording (19 Oct): peak −2.2 dBFS,
  no dropouts.
- On T1 (a kick): the junk blocks stay. The PAD that silences them moves with the load: the owner
  turned it up to 14 as effects were added (v8 reads at most 8), and at other times had to go back down to stop the clicks.
  No fixed wait works; T1 is out.

## v9 (19 Oct 2026): PAD removed, lighter

- v9 is v8 without PAD: PAD (page 2, slot 6) and its wait are gone, page 2 is empty; with PAD 0
  the output is v8's, sample for sample; `verify_distorx` passes.
- `dtx_out` is branch-free: v8's settled block returned early with the wet alone, a branch inside a
  `bsr` callee that `make cycles` refuses to price (v8 never passed `make check` on the owner's
  tree, so it was never flashed). v9 computes the mix and then keeps the wet with `tne y0,a` (the
  Tcc form v7 already ran as `tgt`/`tlt x0,a`): the same samples, bit for bit (`verify_distorx`).
- `make cycles`: 289 cycles/sample at worst (RAT/TURB; SD-1 225), v7 381.
- The cause of v7's T1 junk (🟡) stays the one above: the dispatcher's copy of T1's block lands
  inside the ColdFire's read-back pull when the insert ends in that window, which moves with the
  machine's load. It is the same family as BusDelay's open T1 case
  (`docs/contributing/FAILURE_MODES.md`). v9 ends earlier in the block (289 cycles/sample against
  381), which is consistent with the clean T1 below; it does not prove the window can never be
  reached under a heavier load.

**On the unit (v9, the owner's MK1, image ACIDV71 = BUILD 88, remix `acidtrack`, 20 Oct 2026):**

- Five DISTORX at once, all playing: T1 kick in SD-1, T3 hats in RAT, T5 an OCTA303 in SD-1,
  T6 in TURB, and dEVILish with OCTA303 on another track. No clicks, no junk blocks, no
  slow-downs (by ear; no recording of this session).
- A part saved with PAD keeps a byte in slot 6 that nothing reads.

## Open

- The `-pword` (dirty LFO word) renders of `verify_distorx`: skipped on the owner's tree, whose
  `dsp_host` lacks the option. `make check REMIX=acidtrack` otherwise passes there (20 Oct 2026).
- Instruction forms: DISTORX uses SUPER OD's and dB666's (both on the
  MK1) and CHARACTER's `bne`, `beq` and `do #n` (Sam's MKII), outside the
  sample loops. New beside those, all plain register moves: `move rN,x0`
  and `move nN,x0` for the four limits the RAT loop keeps in r1, r2, r3
  and n3 (r1 and r2 the dispatcher reloads after proc; r3 and n3 SUPER
  OD's own), `move #>imm,n3`, `move x0,y0`, `move y0,x:(r7+d)` and
  `move p:(r5)+,x0`. `verify_distorx` lists any form with no stock site:
  watch those on the first flash.
- The knobs DRIV/TONE/LEVL are applied once per block, like SUPER OD's.

## Gates

`tools/verify/verify_distorx.py` (the manifest's): generated source,
bit-exact against the model (19 renders), SD-1 = SUPER OD (when
`modules/superod` is in the tree), MIX 0, the service notes, the analysis,
the circuit and its 8× truth, silence, the fade, every knob in every MODE;
and an information list of instruction forms with no stock precedent.

## Files

| file | what |
|---|---|
| `manifest.py` | the module, and every constant computed from the part values |
| `distorx.tmpl.asm` | the DSP code, with `@NAME@` constants |
| `generate_asm.py` | writes `distorx.asm` (dsp_asm has no `equ`); `--check` |
| `distorx.asm` | generated, what the build assembles |
| `distorx_ref.py` | the float circuits (`SD1`, `RATCircuit`) and the bit-exact model (`fixed`) |

## Sources

- BOSS SD-1 service notes, ET5212-510A, 3 Mar 1981 (SUPER OD's).
- ElectroSmash, *Pro Co Rat Analysis* (the schematic, the parts list, the
  clipping amplifier's response, the LM308's slew rate):
  <https://www.electrosmash.com/proco-rat>.
- The LTspice `LedRed` diode model (IS = 93.2 p, N = 3.73), as quoted on
  the All About Circuits forum:
  <https://forum.allaboutcircuits.com/threads/the-most-simple-ltspice-led-simulation-question.183992/>.
- PedalPCB forum, *Differences between Rat and Turbo Rat* (the LEDs are the
  difference that matters): <https://forum.pedalpcb.com/goto/post?id=69119>.
- D. T. Yeh, J. S. Abel, J. O. Smith, *Simplified, physically-informed
  models of distortion and overdrive guitar effects pedals*, DAFx 2007.
