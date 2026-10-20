# `dbx160` — DBX 160

The dbx 160 compressor/limiter (1976), modelled from its schematic and its
manual, as a per-track insert on EQUALIZER's id — with a side-chain KEY from
any track over a one-word-per-track bus.

The 160's character is its detector: dbx's true-RMS module (RMS 208, M2 on
the schematic; David Blackmer's log-domain RMS, US 3,681,618, one of the
patents printed on the schematic). Attack and release are not knobs on a 160:
they are that detector's single time constant. The manual gives the release
as 125 dB/s, which fixes it at τ = 10·log₁₀(e)/125 = 34.7 ms, and the same τ,
unchanged, gives the manual's attack times. THRESHOLD and COMPRESSION act in
dB on the detector's output and drive a VCA (dbx 200, M1) with the
difference: a hard knee, ratio 1/(1 − k) for a fraction k of the dB over
threshold.

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
block, with the track's 16 frames at X:$00–$1F. It writes ONE word, the
block's mean square, at its core's half of the shared window:

| tracks | written by | words |
|---|---|---|
| T1–T4 | payload B (core 1) | Y:$3BFF8–$3BFFB |
| T5–T8 | payload A (core 0) | Y:$33FF8–$33FFB |

A DBX 160 on either core reads the one word its KEY names, once per block.
One 24-bit store is atomic, so the two cores need no generation counter; a
word is at most one block (0.36 ms) old. The tap uses a, r0, r1, n1, x0 —
inside the set stock reloads after this site — and replays the displaced
`move x:>$208,r6`. Cost: 32 `mac`s and ten words per track per block, about
11 cycles per sample per core; SIDECHAIN_COMPRESSOR copies the whole block
twice per track to offer audio-rate keys and a key listen, which the 160's
RMS detector does not need. The words sit in the region SIDECHAIN_COMPRESSOR
measured as never written by stock code (the last $202 words of each half)
and that each payload's init zeroes; the ledger therefore refuses the two
modules together (the same hook site and words).

## Measured

✅ in a standalone DSP56300 harness (garbage in every register and state
slot; the tap run for all eight tracks before every block, both payloads'
variants), 11 Oct 2026:

- **Bit-exact** against `dbx160_ref.fixed()`, tap included: defaults, every
  knob at its ends, OverEasy, KEY from T1 (payload B's half) and T7
  (payload A's), KEY out of range, a split block, LFO-dirty page words, the
  other seven tracks carrying a loud square (a wrong word ducks).
- **The manual**: attack to 63 % of the reduction 15.8 / 6.7 / 2.8 ms for
  10 / 20 / 30 dB over threshold at infinity:1 (the manual: 15 / 5 / 3 ms);
  release 123 dB/s (125).
- **Ratios** on a tone 10 dB over threshold: 2:1 → +5.04 dB, 4:1 → +2.56,
  120:1 → +0.08, −1:1 → −10.00.
- **KEY**: a −6 dBFS word on T1 ducks a −30 dBFS tone by −18.63 dB, the float
  law's figure exactly; an empty word does nothing.
- Below threshold at OUT 0 dB, and at MIX 0, the output is the input exactly;
  silence comes out as zeros.
- **Cost**: 297 words of code (the tap's ~20 included) + 66 words of table;
  160 cycles per sample by the pricer, plus the tap.

## On the unit

✅ The owner's MKI, remix `acidtrack`, from 11 Oct 2026 (first flash) to image
ACIDV71 (20 Oct 2026): the side-chain ducking heard clearly from the first
flash (KEY on the kick), then hours of live use beside OCTA303, dEVILish and
DISTORX. `make check REMIX=acidtrack` (the tap inside the real dispatcher,
under the ColdFire port) passed on the owner's tree. By ear only: no
measurement of the ducking on the unit.

## Open

- A recording of the ducking on the unit, against the model's attack and
  release.
- Instruction forms without a stock site (`verify_dbx160` lists them).
- OverEasy's real width; the 160A's own curves are not published.

## Gates

`tools/verify/verify_dbx160.py`: generated source, bit-exact on eight
settings (the bus planted with `-pokey`), the passthroughs, the manual's
attack and release, the ratios, the key, silence, every knob.

## Files

| file | what |
|---|---|
| `manifest.py` | the module, the hook, the bus words, every constant |
| `dbx160.tmpl.asm` | the DSP code with `@NAME@` constants (`@COREBASE@`, `@SBASE@` per payload) |
| `generate_asm.py` | writes `dbx160.asm`; `--check` |
| `dbx160_ref.py` | the 160 in float (`DBX160`) and the module bit for bit (`fixed`, `tap`) |

## Sources

- dbx 160/161 manual and schematic (dbx Inc., c. 1976): the controls, the
  specifications (attack, ratio 1:1–120:1, threshold 10 mV–3 V), Figs. 4–5.
- dbx 160A cut sheet (Harman): release 125 dB/s, −1:1, OverEasy.
- D. E. Blackmer, US 3,681,618, printed on the schematic: the RMS
  detector.
- Zac-Kyoti, SIDECHAIN_COMPRESSOR (MIT): the dispatcher hook site and the
  shared-window region, measured on an MKI.
