| AtoMizer -- STOP reaches AtoMizer.
|
| Stock 0x40004d04..0x40004d0b, in the frame's DSP-record pass (0x40004bd4), once a frame for each
| track (d4) and its record (a2, 0x80000110 + ping * 0x200 + 64 * track):
|     movel %sp@(50),%d2 ; btst %d4,%d2 ; beqs 0x40004d2e
| the stop kill's mask test (0x8000184b: all eight tracks from stop-and-rewind, STOP + STOP; one
| cleared when its track triggers again). 0x40004d0c then zeroes slots A, F and 11 of a stock
| reverb (bbd's kill.s hooks there).
|
| For a track whose FX2 is AtoMizer (record +56, the id the pass wrote last time, as stock reads it):
|   - the transport is not running (the longword 0x800065b8 is not 1; 2 after the STOP key, 0 after
|     stop-and-rewind, docs/firmware/STEM_REC.md 1.0): FREZ (slot E, record +32) reads 0, so the ring
|     takes the input again (silence) and the grains die away like a delay's tail;
|   - the track is in the kill mask as well: MIX (slot F, +34) reads 0 too, and AtoMizer rests at
|     once (atomizer.asm: MIX 0 leaves the block dry and only the ring records).
| The record is rebuilt every frame (0x4000cb4a), so FREZ comes back at PLAY and, after STOP, STOP, MIX
| at the track's next trig (0x4000bf28 clears its kill bit then, as for the stock reverbs). The knobs
| themselves never move. A track whose FX2 is anything else takes the stock path unchanged.
|
| Cost: a few instructions a track a frame. Live input through a stopped sequencer cannot be frozen
| (FREZ reads 0 while stopped).

        .include "remix.inc"                    | ATM_ID
        .text
        .globl  atm_stop

        .set    TRANSPORT, 0x800065b8           | longword: 1 running, 2 stopped (STOP), 0 rewound

atm_stop:
        mvz.w   56(%a2),%d0                     | the track's FX2 id
        moveq   #ATM_ID,%d1                     | the id this remix gave AtoMizer
        cmp.l   %d1,%d0
        bne.s   9f
        moveq   #1,%d1
        cmp.l   TRANSPORT,%d1
        beq.s   1f
        clr.w   32(%a2)                         | stopped: FREZ 0, the tail dies away
1:      move.l  50(%sp),%d2                     | displaced: the kill mask
        btst    %d4,%d2
        beq.s   2f
        clr.w   34(%a2)                         | STOP, STOP: MIX 0, rest now
        clr.w   32(%a2)
2:      jmp     0x40004d2e                      | not a stock reverb: past their test
9:      move.l  50(%sp),%d2                     | displaced, for every other effect
        btst    %d4,%d2
        bne.s   3f
        jmp     0x40004d2e
3:      jmp     0x40004d0c                      | stock: the reverbs' id test (or bbd's kill.s)
