"""STROJ and OCTA303 in one image: HOOKS gives the track's machine list seven rows, STROJ on row 5 (the head, in ANALOG BD's place) and OCTA-303 on row 6."""

from remix.schema import Proof, Remix

REMIX = Remix(
    name="stroj-303",
    family="mods", proof=Proof.CHECK,
    proof_note="the image builds and boots under the port",
    doc="STROJ and OCTA303 in one image: HOOKS gives the track's machine list seven rows, STROJ on row 5 (the head, in ANALOG BD's place) and OCTA-303 on row 6.",
    modules=("STROJ", "OCTA303",
             "FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER",
             "CHORUS", "SPATIALIZER", "COMB FILTER", "COMPRESSOR", "LO-FI",
             "DELAY", "PLATE REV", "SPRING REV", "DARK REV"),
    fallback="NONE",
)
