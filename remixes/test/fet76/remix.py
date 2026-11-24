"""FET76 (the 1176LN) on FX1 and FX2, beside the stock effects (CHORUS, SPATIALIZER, PLATE REV and SPRING REV give up their words)."""

from remix.schema import Proof, Remix

REMIX = Remix(
    name="fet76",
    family="effects",
    proof=Proof.CHECK,
    proof_note="verify_fet76 (dsp_host, bit-exact against the fixed-point model); not yet on a unit",
    doc="FET76 (a model of the UREI 1176LN FET limiter) on FX1 and FX2, beside the stock effects but CHORUS, SPATIALIZER, PLATE REV and SPRING REV.",
    modules=(
        "FET76",
        "FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER",
        "COMB FILTER", "COMPRESSOR", "LO-FI",
        "DELAY", "DARK REV",
    ),
    fx1=("FET76",
         "FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER",
         "COMB FILTER", "COMPRESSOR", "LO-FI"),
    fallback="NONE",
)
