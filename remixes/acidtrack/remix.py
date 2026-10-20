"""aCiDtRacK: OCTA303 + dEVILish + DISTORX + DBX 160 + USB AUDIO OUT (MASTER), DARK REV the one reverb."""
from remix.schema import Pin, Proof, Remix

REMIX = Remix(
    name="acidtrack", family="machines", proof=Proof.HARDWARE,
    proof_note="the author's MKI, images ACIDV68..ACIDV71 (October 2026): hours of live use with two or three "
               "OCTA-303 tracks, dEVILish, DISTORX (v9 also on T1) and DBX 160; make check passed on the author's tree. "
               "This file follows octabam of mid-October 2026: USB AUDIO OUT with LAYOUT MASTER (was USB AUDIO OUT "
               "MASTER) and dEVILish on 0x1e (was 0x1f)",
    doc="aCiDtRacK: OCTA303 + dEVILish + DISTORX (BOSS SD-1 + Pro Co RAT + Turbo RAT) + DBX 160 (side-chain from any track) + USB AUDIO OUT MASTER; DARK REV the one reverb.",
    modules=('OCTA303', 'DEVILISH', 'USB MIDI', 'USB AUDIO OUT', 'FILTER', 'SPATIALIZER', 'DJ EQ', 'FLANGER',
             'COMB FILTER', 'COMPRESSOR', 'LO-FI', 'DELAY', 'DARK REV', 'DISTORX', 'DBX 160'),
    fx1=('FILTER', 'DJ EQ', 'FLANGER', 'COMB FILTER', 'COMPRESSOR', 'LO-FI', 'DEVILISH', 'DISTORX', 'DBX 160'),
    fallback='NONE',
    settings={("octabam.usb-audio-out", "LAYOUT"): Pin("MASTER")},
)
