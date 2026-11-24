"""dB666 (the dbx 160) on FX1 and FX2 with an id of its own, beside the stock effects but PLATE REV, whose words it runs in."""

from remix.schema import Proof, Remix

REMIX = Remix(
    name="db666",
    family="effects",
    proof=Proof.PORT,
    proof_note="this remix: make check REMIX=test/db666 on Sam's main bc14452, 29 Oct 2026 (cloud, no project, no .venv); "
               "not yet flashed. The module itself: the owner's MKI on EQUALIZER's id, acidtrack images from 11 Oct 2026 to ACIDV81 (28 Oct)",
    doc="dB666 on FX1 and FX2 with its own id, beside the stock effects but PLATE REV, whose words it runs in.",
    modules=(
        "DB666",
        "FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER",
        "CHORUS", "SPATIALIZER", "COMB FILTER", "COMPRESSOR", "LO-FI",
        "DELAY", "SPRING REV", "DARK REV",
    ),
    fx1=("DB666",
         "FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER",
         "CHORUS", "SPATIALIZER", "COMB FILTER", "COMPRESSOR", "LO-FI"),
    fallback="NONE",
)
