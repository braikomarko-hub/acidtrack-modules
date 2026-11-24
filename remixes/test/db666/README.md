# `db666` — dB666 alone

dB666 (a model of the dbx 160) on FX1 and FX2 with an id of its own
(`0x1b` preferred, no `replaces`), beside the stock effects but PLATE REV:
its 404 words (338 code + 66 table) run in PLATE REV's 594, as TRANSIENT,
SHATTER and STUTTR do; the other 13 stay, EQUALIZER and COMPRESSOR included. KEY takes the
detector from any track over the side-chain bus, so a kick on T1 can duck a
bass on T5 in two knobs.

`make check REMIX=db666`.

Worst core: 8 dB666 (FX1 and FX2 on four tracks) = 1,280 cycles a sample by
`make cycles`, about 1,800 with COSTS.md's measured ~1.4 (inferred), plus
the tap's ~8 asleep, ~11 with one KEY (counted), against about 3,120 usable; the code has no branch
on a knob. Its slot cost on a unit is not read yet.

**Hardware:** this remix is not flashed yet. The module ran on the owner's MKI
on EQUALIZER's id in the `acidtrack` remix, images ACIDV72 to ACIDV81
(21–28 Oct 2026; module README "On the unit").
