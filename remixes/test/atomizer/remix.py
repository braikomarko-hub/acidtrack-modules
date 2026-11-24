"""AtoMizer loaded on demand into the shared window, beside all 14 stock effects.

AtoMizer's code sits at P:0x35000 (offset 0x1000 of T8's FX2 slot on core A) and is copied
there by DLPUMP and DLCOPY while a track uses it (docs/proposals/DEMAND_LOAD.md); the stock
reverbs are wrapped so they never run over it, and AtoMizer on T8's FX2 passes the audio
through for the same reason (atomizer.asm). LOAD METER carries the pump and measures the cost."""
from remix.schema import Pin, Proof, Remix
STOCK14 = ("FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER", "CHORUS", "SPATIALIZER",
           "COMB FILTER", "COMPRESSOR", "LO-FI", "DELAY", "SPRING REV", "PLATE REV", "DARK REV")
REMIX = Remix(family="effects", proof=Proof.CHECK, proof_note="",
              name="atomizer",
              doc="AtoMizer loaded on demand into the shared window, beside all 14 stock effects.",
              modules=("USB", "LOAD METER", "DLPUMP", "DLCOPY", "ATOMIZER") + STOCK14,
              fx1=("FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER", "CHORUS", "SPATIALIZER",
                   "COMB FILTER", "COMPRESSOR", "LO-FI"),
              window=(("DLCOPY", 0x33DC3), ("ATOMIZER", 0x35000), ("LOAD METER", 0x37DA3),
                      ("LOAD METER:B", 0x37E50)),
              window_demand=("ATOMIZER",),
              window_guard=("PLATE REV", "DARK REV", "SPRING REV"),
              window_loader=0x33E56,
              fallback="NONE",
              settings={("octabam.dlpump", "GRACE"): Pin("2 S"),   # verify_dlload's withdraw scenario, as test/dlspike
                        ("octabam.usb", "TRACKS"): "PRE", ("octabam.usb", "MAIN"): 0,
                        ("octabam.usb", "CUE"): 0, ("octabam.usb", "MASTER"): 0,
                        ("octabam.usb", "IN"): "OFF"})
