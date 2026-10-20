# `octa303` — the OCTA-303 machine

One ColdFire module and the stock effects. For anyone who wants a TB-303 voice on the Octatrack MKI
without samples.

## What is in it

- **OCTA303** — row 5 of the track's machine list, **OCTA-303**: a circuit-modelled TB-303 voice
  calibrated against recordings of a real TB-303 (PLAYBACK: TUNE CUT RES ENV DEC ACC; SETUP: WAVE
  GATE FINE SLID DRIV ACCV). `modules/octa303/README.md`.
- the 14 stock FX2 effects, listed so the chooser is stock's.

`devilish` (the Devil Fish modifications, an FX read by the voice) and `distorx` are not in this
remix; the owner's set carries them beside OCTA303.

## Status

OCTA303 v7.0 on the author's MKI in his remix `acidtrack` (ACIDV70, BUILD 87, 19 Oct 2026): the
machine list, the SETUP page, save / power-cycle / reload and the 303 gate. This remix itself is
built and its UI gate run under the port (`tools/verify/verify_octa303_ui.py`), not flashed.
Not measured: the ColdFire load (CF METER).

## Build

```bash
make image REMIX=octa303 BUILD=1    # -> out/OCTATRACK_OCTABAM1.bin
```

[BUILDING.md](../../../docs/guide/BUILDING.md) is the walk-through from a fresh machine to a flashed
unit. `make check REMIX=octa303` runs every gate first.
