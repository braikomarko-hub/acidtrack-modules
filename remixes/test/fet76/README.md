# test/fet76

FET76 (`modules/fet76`, a model of the UREI 1176LN FET limiting amplifier) on FX1 and FX2, beside the stock
effects; CHORUS, SPATIALIZER, PLATE REV and SPRING REV are left out for its words.

Proof: `tools/verify/verify_fet76.py` (dsp_host, bit-exact against `modules/fet76/fet76_ref.fixed()`).
Not yet on a unit.
