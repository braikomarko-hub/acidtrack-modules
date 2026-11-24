"""STROJ alone: the drone machine on row 5 of the machine list, with stock's effects."""

from remix.schema import Proof, Remix

REMIX = Remix(
    name="stroj",
    family="mods", proof=Proof.CHECK,
    proof_note="test_stroj: the voice bit-exact under cfsim; the image builds and boots under the port",
    doc="STROJ alone: the drone machine on row 5 of the machine list, with stock's effects.",
    modules=("STROJ",
             "FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER",
             "CHORUS", "SPATIALIZER", "COMB FILTER", "COMPRESSOR", "LO-FI",
             "DELAY", "PLATE REV", "SPRING REV", "DARK REV"),
    fallback="NONE",
)
