"""aCiDtRacK: OCTA303 + dEVILish + DISTORX + dB666 + USB AUDIO OUT (MASTER) + BRAIN (REMIX SWITCH), DARK REV the one reverb."""
from remix.schema import Proof, Remix

REMIX = Remix(
    name="acidtrack", family="machines", proof=Proof.HARDWARE,
    proof_note="the author's MKI, images ACIDV68..ACIDV71 (October 2026): hours of live use with two or three "
               "OCTA-303 tracks, dEVILish, DISTORX (v9 also on T1) and dB666; make check passed on the author's tree. "
               "This file follows octabam of 20 October 2026: USB with MASTER on and MIDI on (was USB MIDI + USB AUDIO OUT "
               "MASTER), dEVILish on 0x10 replacing PHASER (was 0x1f; 0x1e is RESONATOR's since 21 Oct), DISTORX on 0x0a (was 0x1b); BRAIN and MEMORY on the unit as ACIDV72 (21 Oct 2026, dEVILish then on 0x1e): defaults and templates work, the project record is not read back (issue filed)",
    doc="aCiDtRacK: OCTA303 + dEVILish + DISTORX (BOSS SD-1 + Pro Co RAT + Turbo RAT) + dB666 (side-chain from any track) + USB AUDIO OUT MASTER + BRAIN (switch remixes from the card); DARK REV the one reverb.",
    modules=('OCTA303', 'DEVILISH', 'USB', 'BRAIN', 'MEMORY', 'FILTER', 'SPATIALIZER', 'DJ EQ', 'FLANGER',
             'COMB FILTER', 'COMPRESSOR', 'LO-FI', 'DELAY', 'DARK REV', 'DISTORX', 'DB666'),
    fx1=('FILTER', 'DJ EQ', 'FLANGER', 'COMB FILTER', 'COMPRESSOR', 'LO-FI', 'DEVILISH', 'DISTORX', 'DB666'),
    fallback='NONE',
    settings={("octabam.usb", "TRACKS"): "OFF", ("octabam.usb", "MAIN"): 0,
              ("octabam.usb", "CUE"): 0, ("octabam.usb", "MASTER"): 1,
              ("octabam.usb", "IN"): "OFF", ("octabam.usb", "MIDI"): 1},
)
