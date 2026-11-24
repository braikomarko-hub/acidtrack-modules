# `atomizer` -- AtoMizer

A granular delay for FX2, by Marko Brajković, after the **Red Panda Particle**
(V1 on the Spin FV-1, 2011; Particle 2, 2019). Particle is Red Panda's name and
pedal: AtoMizer re-derives its behaviour for the Octatrack from the Particle 2
owner's manual (firmware 2.2, July 2023) and Red Panda's public changelog. No
Red Panda code or firmware was read or used. 1,593 DSP words and a 42-word
P table; `atomizer.asm` is proven BIT-IDENTICAL against an integer model of
the same arithmetic, `atomizer_ref.py`.

Author: MaMarko (Marko Brajković, [braikomarko-hub](https://github.com/braikomarko-hub)): the idea, the listening and the tests on the unit. **The code was written by Claude (Anthropic).**

The mono sum of the track goes into a ring (15,779 words, 358 ms, in RCYC;
8,192 words, 186 ms, in the other feedback modes, whose second half of the
slot is the aux line). Two grain voices read the ring through a
linear-interpolated position (9 fractional bits) and a window, and SPRD pans
each grain at random. What the MODE changes is where each grain starts, how
fast it reads and how often a new one starts:

| MODE | TIME | PARA | The grains |
| --- | --- | --- | --- |
| DDEN (delay + density) | delay | density | IOI from 4 L (PARA 0, the density floor) to L/2; overlapped grains get triangle windows |
| DLFO (delay + LFO) | scan range | LFO rate | the delay scans 0..TIME with a triangle LFO, 0.05..5 Hz |
| DREV (delay + reverse) | delay | direction | each grain plays backwards with probability PARA |
| DPCH (delay + pitch) | delay | jump | each grain jumps an octave up or down with probability PARA |
| DRND (delay + random) | delay | randomness | each grain starts somewhere between the delay and up to PARA x delay earlier |
| PDTN (pitch + detune) | pitch -12..+12 | detune | a pitch shifter; the two voices PARA (to half a semitone) apart |
| PLFO (pitch + LFO) | pitch -12..+12 | LFO rate | the pitch sweeps between unison and TIME with the LFO |
| PDEN (pitch + density) | pitch -12..+12 | density | the pitch shifter, thinned like DDEN |

Pitch uses a table of 512·2^(s/12), interpolated in 1/256 semitone. A grain
that reads faster than the input starts far enough back that it never
overtakes the write head.

## Knobs

| Page | Knob | Range (default) | What it does |
| --- | --- | --- | --- |
| main, A | CHOP | 0–127 (48) | Grain length L: CHOP²/2 + 64 samples, 1.5–184 ms; SYNC: 1/64 .. 1/4 of the tempo. Halved until it fits the MODE and the ring. |
| main, B | TIME | 0–127 (40) | The delay modes: the delay (SYNC: 1/64, 1/32, 3/64, 1/16, 3/32, 1/8, 3/16, 1/4). The pitch modes: -12..+12 semitones (64 is unison). |
| main, C | PARA | 0–127 (64) | The MODE's parameter (table above). |
| main, D | FDBK | 0–127 (0) | RCYC: the wet back into the ring (to 0.95). POST and PING: the post line's feedback. REP, R1/2, R1/4: the repeats, 0..8. RPCT: the probability of a repeat. |
| main, E | FREZ | 0–127 (0) | 0 off -- always releases, whatever came before. 1..126: the ring stops taking input while the track is quiet (a slow envelope under (FREZ/128)²/4). 127: frozen; the grains, the LFO and the scan go on over what the ring holds. |
| main, F | MIX | 0–127 (0) | 0 is exactly dry, and **at rest**: picked, AtoMizer starts there, so it never comes in abruptly; the ring keeps recording, nothing else runs, so AtoMizer costs almost nothing. To 64 the wet rises to unity over the whole dry; from 64 to 127 the dry fades out (the Particle 2.0.1 BLEND law). Leaving 0 starts a fresh grain. |
| SETUP, A | MODE | the eight above (DDEN) | Changing it moves no knob (the Particle 2.2 expert mode). |
| SETUP, B | TONE | 0–127 (127) | A one-pole low-pass in the feedback (RCYC, POST, PING): 0 dark, 127 open. |
| SETUP, C | FBMD | AUTO, RCYC, POST, PING, REP, R1/2, R1/4, RPCT (AUTO) | The feedback mode (below). Moving between RCYC and the others clears the slot: 62 calls of dry, about 22 ms. |
| SETUP, D | SPRD | 0–127 (0) | Random stereo spread of the grains. |
| SETUP, E | SYNC | FREE / SYNC | SYNC: CHOP and TIME are divisions of the Octatrack's tempo, and an attack in the input (a fast envelope over twice a slow one) restarts the grain and the REP slot. |
| SETUP, F | V1 | 0–127 (0) | Reserved for the FV-1's memory colour; does nothing yet. |

## Feedback modes (FBMD)

- **AUTO**: POST in DDEN, RCYC in every other MODE (the Particle 2.2.0 default).
- **RCYC**: recycle -- the ring takes the input plus FDBK x TONE(wet), so the
  repeats go back through the grains.
- **POST**: the grains go into a separate delay line (7,587 words) with FDBK x
  TONE feedback; its time is the delay (2 L in the pitch modes).
- **PING**: two lines of 3,793 words; the grains enter on the left and each
  repeat changes side.
- **REP**: slots of L samples: a live slot is captured, then the next N slots
  (FDBK: 0..8) replay it, then live again.
- **R1/2**, **R1/4**: a fresh capture every N + 1 slots; in between, each slot
  replays the capture with probability 1/2 or 1/4, else plays live.
- **RPCT**: each slot replays the last capture with probability FDBK, else
  plays live and is captured.

A replayed slot crossfades in and out over min(128, L/4) samples, so slot
edges do not click.

## Memory and cost

The FX2 slot from the allocator (read at init, `x:>$213`), up to +$3DA2:
15,779 words, DARK REV's extent (`stock.SLOT_EXTENT`). Above it, in the T7 and
T8 slots, sit the demand loader's entries, DLCOPY and LOAD METER's DSP half
(`docs/proposals/DEMAND_LOAD.md`). State in r7 + $00..$5f, all zeroed at init;
the slot is cleared (256 words a call, dry meanwhile) before the first wet
sample and on every layout change.

## STOP

`stop.s` (a detour at `0x40004d04`, the stop kill's mask test in the frame's DSP-record pass) makes the
transport reach AtoMizer, which the DSP cannot see by itself:

- **STOP** (the transport word `0x800065b8` is not 1): FREZ reads 0 in the record. The ring takes the
  input again, which is silence once the tracks stop, so the grains die away like a delay's tail
  (within the ring's 358 ms; longer with FDBK, as a delay's feedback rings). Before, a frozen ring (FREZ
  127, or 1..126 with the input quiet) played on after STOP until FREZ or MIX was turned down.
- **STOP, STOP** (the stop kill, as it silences the stock reverbs): MIX reads 0 too, and AtoMizer rests
  at once: dry, the ring recording silence.
- **PLAY**: the record is rebuilt from the Part every frame (0x4000cb4a), so FREZ comes back at PLAY
  and, after STOP, STOP, MIX at the track's next trig (the kill mask clears a track's bit when it
  triggers, as for the stock reverbs: a track with no trigs stays dry). The knobs never move.
- While stopped the ring still records whatever audio keeps flowing (thru inputs, other effects' tails),
  so the tail dies away once that input is quiet.

Live input through a stopped sequencer cannot be frozen: FREZ reads 0 while stopped.
`tools/verify/verify_atomizer_stop.py` checks the records under the port.

## Placement and id

0x1e is the id AtoMizer prefers; `registry.assign_ids` gives it the remix's
own, so it replaces no stock effect. Its code goes either into a harvested
donor run (1,635 words with the table, which takes SPRING REV, PLATE REV and
DARK REV) or into the shared window, loaded on demand while a track uses it
(`Remix.window_demand`). `remixes/test/atomizer` does the latter: the code at
`P:0x35000`, offset +$1000 of T8's FX2 slot on core A, beside all 14 stock
effects, with LOAD METER, DLPUMP and DLCOPY; the stock reverbs are wrapped by
DLWRAP.

Loaded on demand, the code lives inside one track's FX2 buffer, so AtoMizer
guards itself the way DLWRAP guards the reverbs: every call it reads DLCOPY's
four entries (`x:$33da3 + 8 k`: BOUND, the span) and, when `[base, base +
$3DA3)` covers a loaded span, passes the audio through and writes nothing.
In `test/atomizer` that is AtoMizer on **T8's FX2**: it stays dry there and
works on the other seven FX2 slots. When the range is free again the slot
clears and the engine restarts. A remix without the loader leaves those
words zero, so the check never fires.

AtoMizer is FX2 only (an FX1 slot holds 3,072 words), but a part saved under
another remix can put its id on an FX1 slot, and the loader would then load
it. On a base below Y:$4000 the instance passes the audio through and writes
nothing.

`cycle_count.py`: 547 cycles a sample per instance (599 before 27 Oct 2026),
pricing a grain start on every sample, both voices sounding and the worst
feedback mode; MIX 0's loop is 53. The manifest declares `max_per_core = 1`
(one instance per core: in acidtrack four AtoMizer beside four DISTORX on FX1
priced 3,552 at 599); the unit does not enforce it, so a remix README states it.

What is not heard is not computed (27 Oct 2026): a finished grain (its window
at 0) skips its voice until the next start; FREZ 0 and 127 are decided once a
block; the envelopes run only for SYNC or FREZ 1..126; MIX 0 rests. With the
knobs still, the sound is the same as before, bit for bit (the old and new
models agree on all 384 MODE x FBMD x FREZ x SYNC cases). Measured in
`dsp_host`, executed instructions per 32-frame block on core 0 with one
instance (the stock dispatcher included), before -> after:

| Setting | Mean | Worst block |
| --- | --- | --- |
| DDEN, the defaults | 5,429 -> 3,285 | 5,502 -> 5,131 |
| DDEN, PARA 0 (grains far apart) | 5,429 -> 3,094 | 5,502 -> 5,131 |
| DDEN, PARA 127 (dense) | 5,430 -> 5,061 | 5,502 -> 5,131 |
| DREV | 4,671 -> 3,310 | 4,740 -> 4,369 |
| PDTN (the voices always overlap) | 4,747 -> 4,378 | 4,816 -> 4,445 |
| RCYC, FDBK 90 | 4,680 -> 2,536 | 4,750 -> 4,379 |
| PING | 5,604 -> 3,460 | 5,678 -> 5,307 |
| the `dear` knobs | 5,403 -> 5,034 | 5,518 -> 5,147 |
| MIX 0 | 5,429 -> 779 | 5,502 -> 781 |

The worst block (both voices sounding) drops ~7 %; the mean drops up to 45 %
where the grains leave gaps. The pitch modes overlap their voices, so they
gain least.

## Measured

All gates of `tools/verify/verify_atomizer.py` pass on this tree, 26 Oct 2026
(`dsp_host`, a private image with the stock code built in and AtoMizer in the
space of DELAY, SPRING REV, PLATE REV and DARK REV):

- **reference**: every MODE, every FBMD, FREZ held and by threshold, SYNC with
  a tempo, SPRD, MIX and TONE: the DSP output is bit-identical to
  `atomizer_ref.py` over 1.6 s, on core 0 and (a set) on core 1.
- **automation**: every knob moving every 23 blocks, MODE and FBMD included
  (252 layout changes), with and without a trig split: bit-identical.
- **dry**: MIX 0 is the input sample for sample, knobs still and moving.
- **idle**: with FDBK 0 every feedback mode falls to exact digital silence.
- **isolation**: eight instances, four a core, under the write guard: no stray
  write, each identical alone. **garbage**: a garbage instance block renders as
  a zeroed one.
- **demand**: with a loaded effect's entry written into the dump (BOUND and a
  span, as DLCOPY publishes it): the slot that covers the span (AtoMizer's own
  code in T8's slot; a span on the slot's last word; a span in core B's T4
  slot) passes the input through sample for sample and writes no Y word; a
  span from +$3DA3 or ending at the base, and every other slot, render
  bit-identically to the dump without it; on an FX1 base the instance is dry
  and writes nothing. `dsp_host` keeps P and Y apart, so this proves the
  decision, not the chip's overwrite. Not covered: an instance going from dry
  back to wet when a span is withdrawn mid-render.

On `remixes/test/atomizer` the demand loader's own gates pass with AtoMizer
as the loaded effect: `verify_dlstub` (unbound dry, bound equal to the direct
render on FX2's first slot, 1,635 words at `P:0x35000`, a bad sum or a missing doorbell stays dry)
and `verify_dlwrap` (the three reverbs on every slot and payload).

What none of them can see: the unit itself (memory-contention stalls, the
real cycle wall with other effects loaded), and how it sounds -- the model is
the reference, not the pedal.

## Open

- **The unit.** Nothing has run on hardware: not the code from the window, not
  the cost beside other effects (LOAD METER will show it), not the ~25 ms of dry
  audio while the block arrives.
- **T8's FX2.** AtoMizer is silent there in `test/atomizer` (above). A toast
  like the loader's `NEEDS Tn FX2 FREE` would say why; not done.
- Not yet: the V1 colour (the FV-1's 1s3e10m memory and 32 kHz band limit),
  the LFO restart at the pattern start (the Particle's TAP), a smoothed MIX.
