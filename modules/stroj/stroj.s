| ============================================================================
| STROJ -- a drone machine for the Octatrack MKI's ColdFire (v1, 30 Oct 2026).
|
| Four "plates" in two nearly-tuned pairs with cross phase modulation (after SOMA's Lyra-8) and two
| sub-octaves that swell at their own rates (after Moog's Subharmonicon), a soft saturation and a
| state-variable low-pass.  One voice a FLEX track, rendered on the ColdFire in place of the
| track's sample; AMP, FX1 and FX2 stay stock after it.  Idea and listening: MaMarko; code: Claude.
|
| The voice (sj_init, sj_voice) is integer arithmetic mirrored line for line by
| tools/stroj/stroj_ref.py; tools/stroj/test_stroj.py runs this file's text under cfsim and
| requires bit-identical output.  Change both or neither.  Its tables are generated
| (modules/stroj/stroj_tables.inc, `python3 tools/stroj/stroj_ref.py --write`).
|
| The machine: row 5 of the track's machine list, stored as FLEX and signed 'S','J',1 in the
| track's NEIGHBOR PLAYBACK bytes (Part' + 0x3c + 30 * track), the seams repeat98 measured for
| ANALOG BD and OCTA303 v7.0 uses (modules/analog-bassdrum/machine.s).  Beside other machines
| (modules/hooks, machine_rows: HK_MACHINE_ROWS, MC_ROW, MC_HAS_* / MC_NEXT_*) STROJ is one link of
| Sam's chain: its row is MC_ROW, and every hook it has hands a row or a track that is not its own
| to the next machine's routine for the same hook, entered as at the site; the last replays stock.

| Audio follows OCTA303 (after Tim Hastie's SYNTH MACHINE 2.9): on a STROJ track the stock
| renderer writes the header with PTCH / RATE neutral and the carrier's positions pinned, then
| sj_voice writes the samples.  A START latches the track; the voice's phases never restart (a
| trig, a lock, a scene change the chord without a click).
|
| PLAYBACK  NOTE SPRD INTV FM  SUB  TONE    (FLEX's PTCH STRT LEN RATE RTRG RTIM slots)
| SETUP     VOIC SUB1 SUB2 BRTH RYTM WAVE   (FLEX's SETUP slots; the selects are indices)
| ============================================================================

        .text
        .include "remix.inc"            | HK_MACHINE_ROWS, MC_*: our place in HOOKS's machine chain

| ---- platform (OS 1.40C): the values OCTA303 uses (modules/octa303/octa303.s, check_platform.py)
        .set    VOICE_BASE,     0x800049d8      | the CF voice structs, VOICE_STRIDE apart
        .set    VOICE_STRIDE,   0xa8
        .set    V_POS,          64              | +64..+83: the voice's sample positions
        .set    CURSOR,         0x80001c80      | the header this call writes: byte 3 = samples, L/R longs from +16
        .set    NIBBLE,         0x46104d0c      | the packer's per-track event byte, bit 4 = a voice START
        .set    STOCK_RENDER,   0x40004008      | the stock FLEX renderer
        .set    RESOLVER_RET,   0x40031ed6      | the page resolver after its table load (sj_page)
        .set    FP_PTR,         0x800062a8      | the packer's per-track DSP parameter record (halfwords, raw<<8)
        .set    RS_PTR,         0x800062a4      | the packer's per-track render state (+4 = the latched retrig count)
        .set    RETRIG_RET,     0x4000c63c      | the frame builder after its command-byte copy (sj_retrig)
        .set    FLEX_P,         0x400d31ae      | the stock FLEX PLAYBACK descriptor
        .set    FLEX_DESC_LEN,  0x192
        .set    SJ_DLEN,        0x194
        .set    PART_OFF,       0x8ed80         | the bank blob's Part 0 (Part' = BANK + this + part * PART_SIZE)
        .set    PART_SIZE,      6322
        .set    BANK_PTR,       0x46c82456
        .set    PART_IDX,       0x100b14cf
        .set    CURVALS,        0x80000810      | the frame builder's live lane, 72 B a track, locks applied
        .set    CV_STRIDE,      72
        .set    LANE_SETUP,     0x20            | the live lane's SETUP bytes (+0x20..+0x25)
        .set    FMT_PLAIN,      0x4003c178      | stock fmt(buf, value) -> "%d"
        .set    SPRINTF,        0x40013a08
        .set    FMT_D,          0x400b465d      | its "%d"
        .set    NEUTRAL_PTCH,   0x4000
        .set    NEUTRAL_RATE,   0x7f00
        .set    NTRACKS,        8
        .if     HK_MACHINE_ROWS
        .set    SJ_ROW,         MC_ROW          | beside other machines: our place in the chain
        .if     MC_HAS_RENDER                   | the next renderer in the FLEX kind entry's chain
        .set    STOCK_RENDER,   MC_NEXT_RENDER
        .endif
        .else
        .set    SJ_ROW,         5               | the machine's row and UI type
        .endif
        .set    FLEX,           1
        .set    SIG_OFF,        0x3c            | Part' + 0x3c + 30*track: 'S', 'J', 1
        .set    SRAM_PART,      0x100a4ece      | the shadow of Part 0's Part'
        .set    SRC_CURSOR,     0x460d5c30      | SRC SETUP's selected row
        .set    PB_TABLE,       0x400d5f38      | the PLAYBACK records by UI type
        .set    STOCK_DEFS,     0x400d320c      | FLEX_P + 0x5e: FLEX's twelve defaults
        .set    PAGE2_GAP,      0x1b0           | SETUP bytes - PLAYBACK bytes
        .set    MACH_OFF,       0x8eda2         | Part + this + track: the track's machine (1 = FLEX)

        .global stroj_render, sj_voice, sj_init, sj_latched, sj_retrig
        .global sj_machine_name, sj_src_names, sj_name_a, sj_name_b, sj_setup_row, sj_chooser_row
        .global sj_setup_open, sj_chooser_open, sj_tick, sj_main_commit, sj_src_commit, sj_src_commit2
        .global sj_setup_edit6, sj_setup_draw6, sj_validate, sj_page, sj_row_type, sj_title
        .global sj_sig, sj_mdesc, sj_lfo_name, sj_chrom, sj_publish


| ============================================================================
| THE VOICE (sj_init, sj_voice): tools/stroj/stroj_ref.py Voice, sample for sample
| ============================================================================
| ---- the state block (longs)
        .set    S_PH,   0               | 4 plate phases
        .set    S_SP,   16              | 2 sub-octave phases
        .set    S_PREV, 24              | 4 plates' last outputs (the cross FM reads them)
        .set    S_LFO,  40              | the breath, 0..0x1FFFF
        .set    S_LO,   44              | the filter's low-pass state
        .set    S_BP,   48              | the filter's band-pass state
| ---- this call's control values (recomputed every call; kept here for the sample loop)
        .set    C_INC,  52              | 4 plate increments
        .set    C_FM,   68
        .set    C_S1,   72              | sub-octave increments
        .set    C_S2,   76
        .set    C_G1,   80              | sub-octave levels
        .set    C_G2,   84
        .set    C_MIX,  88              | the plates' mix gain, Q15
        .set    C_F,    92              | the filter's coefficient, Q15
        .set    C_VOIC, 96              | 1..4
        .set    C_PART, 100             | the partner plate's byte offset: 4 v ^ C_PART (8 with 3-4 plates, 4 with 1-2)
        .set    C_SUB,  104             | SUB level (0 = off)
        .set    C_TONE, 108             | the TONE knob (127 = off)
        .set    C_STEP, 112             | the breath's step (0 = still)
        .set    C_MIX2, 116             | the second pair's gain: C_MIX * 0.8
        .set    SJ_SIZE, 120

sj_init:
        moveq   #0,%d0
        moveq   #29,%d1                 | clear 30 longs
sj_i0:  move.l  %d0,(%a0,%d1.l*4)
        subq.l  #1,%d1
        bge.s   sj_i0
        move.l  #0x40000000,%d0
        move.l  %d0,S_PH+4(%a0)
        move.l  #0x15555555,%d0
        move.l  %d0,S_PH+8(%a0)
        move.l  #0x6AAAAAAA,%d0
        move.l  %d0,S_PH+12(%a0)
        rts

| ---- sj_inc: d0 = a note, semitones Q8 (MIDI * 256, >= 0) -> d0 = its phase increment.
|      Uses d1, a4.  o = p / 3072 (octaves), r = p - 3072 o; INC[r >> 2] << o.
sj_inc:
        move.l  %d2,-(%sp)
        move.l  %d3,-(%sp)
        move.l  %d0,%d1
        move.l  #3072,%d2
        divu.l  %d2,%d1                 | d1 = octave
        move.l  %d1,%d3
        mulu.l  %d2,%d3
        sub.l   %d3,%d0                 | d0 = r
        lsr.l   #2,%d0
        lea     sj_t_inc,%a4
        move.l  (%a4,%d0.l*4),%d0
        lsl.l   %d1,%d0
        move.l  (%sp)+,%d3
        move.l  (%sp)+,%d2
        rts

sj_voice:
        lea     -40(%sp),%sp
        movem.l %d2-%d7/%a2-%a5,(%sp)
        move.l  %d0,%d7                 | d7 = samples left

| ======================================================== once a call: the knobs become numbers
        | ---- base note, interval, spread
        mvz.b   0(%a1),%d3
        subi.l  #28,%d3
        moveq   #12,%d0
        cmp.l   %d0,%d3
        bge.s   sj_c1
        move.l  %d0,%d3
sj_c1:  moveq   #84,%d0
        cmp.l   %d0,%d3
        ble.s   sj_c2
        move.l  %d0,%d3
sj_c2:  lsl.l   #8,%d3                  | d3 = base (Q8)
        mvz.b   2(%a1),%d0
        lsr.l   #4,%d0
        lea     sj_t_intv,%a4
        move.l  (%a4,%d0.l*4),%d4       | d4 = interval (Q8)
        add.l   %d3,%d4                 | d4 = base + interval
        mvz.b   1(%a1),%d0
        lea     sj_t_sprd,%a4
        move.l  (%a4,%d0.l*4),%d5       | d5 = spread (Q8)
        | ---- the four plates' increments (all four: cheap, and the unused ones are never read)
        move.l  %d3,%d0
        add.l   %d5,%d0
        bsr     sj_inc
        move.l  %d0,C_INC(%a0)
        move.l  %d3,%d0
        sub.l   %d5,%d0
        bsr     sj_inc
        move.l  %d0,C_INC+4(%a0)
        move.l  %d4,%d0
        add.l   %d5,%d0
        bsr     sj_inc
        move.l  %d0,C_INC+8(%a0)
        move.l  %d4,%d0
        sub.l   %d5,%d0
        bsr     sj_inc
        move.l  %d0,C_INC+12(%a0)
        | ---- VOIC and the partner plate
        mvz.b   6(%a1),%d0
        lsr.l   #5,%d0
        addq.l  #1,%d0
        move.l  %d0,C_VOIC(%a0)
        lea     sj_t_mixg,%a4
        move.l  (%a4,%d0.l*4),%d1
        move.l  %d1,C_MIX(%a0)
        move.l  #26214,%d2
        mulu.l  %d1,%d2
        moveq   #15,%d1
        lsr.l   %d1,%d2
        move.l  %d2,C_MIX2(%a0)
        moveq   #4,%d1
        moveq   #2,%d2
        cmp.l   %d2,%d0
        ble.s   sj_c3
        moveq   #8,%d1
sj_c3:  move.l  %d1,C_PART(%a0)
        | ---- WAVE: a3 = the wave's table
        mvz.b   11(%a1),%d0
        lsr.l   #5,%d0
        moveq   #12,%d1
        lsl.l   %d1,%d0                 | 2048 shorts = 4096 bytes a wave
        lea     sj_t_wave,%a3
        add.l   %d0,%a3
        | ---- the breath: d6 = br (0..32767)
        mvz.b   9(%a1),%d0
        lea     sj_t_bstep,%a4
        move.l  (%a4,%d0.l*4),%d0
        move.l  %d0,C_STEP(%a0)
        move.l  #16384,%d6
        tst.l   %d0
        beq.s   sj_c5
        add.l   S_LFO(%a0),%d0
        andi.l  #0x1FFFF,%d0
        move.l  %d0,S_LFO(%a0)
        bsr     sj_tri
        move.l  %d0,%d6
sj_c5:  | ---- FM depth: (FM[k] * (8192 + 3 br / 4)) >> 15
        move.l  %d6,%d0
        move.l  %d0,%d1
        add.l   %d1,%d0
        add.l   %d1,%d0
        asr.l   #2,%d0
        addi.l  #8192,%d0
        mvz.b   3(%a1),%d1
        lea     sj_t_fm,%a4
        move.l  (%a4,%d1.l*4),%d1
        muls.l  %d1,%d0
        asr.l   #8,%d0
        asr.l   #7,%d0
        move.l  %d0,C_FM(%a0)
        | ---- the sub-octaves
        mvz.b   4(%a1),%d0
        move.l  #258,%d1
        mulu.l  %d1,%d0
        move.l  %d0,C_SUB(%a0)
        move.l  %d0,C_G1(%a0)
        move.l  %d0,C_G2(%a0)
        tst.l   %d0
        beq     sj_c9
        mvz.b   10(%a1),%d1             | RYTM: (k * 5) >> 7
        move.l  %d1,%d2
        lsl.l   #2,%d1
        add.l   %d2,%d1
        lsr.l   #7,%d1
        lea     sj_t_rya,%a4
        move.l  (%a4,%d1.l*4),%d2       | d2 = a
        beq.s   sj_c8
        tst.l   C_STEP(%a0)
        beq.s   sj_c8
        lea     sj_t_ryb,%a4
        move.l  (%a4,%d1.l*4),%d5       | d5 = b
        move.l  S_LFO(%a0),%d0
        mulu.l  %d2,%d0
        andi.l  #0x1FFFF,%d0
        bsr     sj_tri
        bsr     sj_swell
        move.l  %d0,C_G1(%a0)
        move.l  S_LFO(%a0),%d0
        mulu.l  %d5,%d0
        andi.l  #0x1FFFF,%d0
        bsr     sj_tri
        bsr     sj_swell
        move.l  %d0,C_G2(%a0)
sj_c8:  move.l  %d3,%d0                 | the sub-octaves divide the base note's increment
        bsr     sj_inc
        move.l  %d0,%d4
        mvz.b   7(%a1),%d1
        move.l  %d1,%d2
        lsl.l   #3,%d1
        sub.l   %d2,%d1                 | * 7
        lsr.l   #7,%d1
        addq.l  #2,%d1
        divu.l  %d1,%d0
        move.l  %d0,C_S1(%a0)
        move.l  %d4,%d0
        mvz.b   8(%a1),%d1
        move.l  %d1,%d2
        lsl.l   #3,%d1
        sub.l   %d2,%d1                 | * 7
        lsr.l   #7,%d1
        addq.l  #2,%d1
        divu.l  %d1,%d0
        move.l  %d0,C_S2(%a0)
sj_c9:  | ---- TONE
        mvz.b   5(%a1),%d0
        move.l  %d0,C_TONE(%a0)
        lea     sj_t_tone,%a4
        move.l  (%a4,%d0.l*4),%d0
        move.l  %d0,C_F(%a0)
        moveq   #14,%d1                 | the sub-octaves' levels, ready: g << 14 (= g * q / sign)
        move.l  C_G1(%a0),%d0
        lsl.l   %d1,%d0
        move.l  %d0,C_G1(%a0)
        move.l  C_G2(%a0),%d0
        lsl.l   %d1,%d0
        move.l  %d0,C_G2(%a0)

| ======================================================== every sample
        .macro  PLATE off, acc
        move.l  S_PH+\off(%a0),%d1
        add.l   C_INC+\off(%a0),%d1
        move.l  %d1,S_PH+\off(%a0)      | the phase moves on
        tst.l   %d4
        beq.s   sj_p\@
        moveq   #\off,%d0               | cross FM: the partner's last output
        eor.l   %d6,%d0
        move.l  S_PREV(%a0,%d0.l),%d2
        muls.l  %d4,%d2
        lsl.l   #4,%d2
        add.l   %d2,%d1
sj_p\@: moveq   #21,%d0
        lsr.l   %d0,%d1                 | the top 11 bits: the table index
        mvs.w   (%a3,%d1.l*2),%d2
        move.l  %d2,S_PREV+\off(%a0)
        add.l   %d2,\acc
        .endm
        .macro  CLAMP reg, lim          | \reg = clamp(\reg, -\lim, \lim)
        cmpi.l  #\lim,\reg
        ble.s   sj_ka\@
        move.l  #\lim,\reg
sj_ka\@: cmpi.l  #-\lim,\reg
        bge.s   sj_kb\@
        move.l  #-\lim,\reg
sj_kb\@:
        .endm

        move.l  C_FM(%a0),%d4           | d4 = FM depth (0 = no modulator)
        move.l  C_PART(%a0),%d6         | d6 = the partner's offset
sj_s0:  moveq   #0,%d3                  | d3 = the first pair
        moveq   #0,%d5                  | d5 = the second pair
        PLATE   0, %d3
        moveq   #1,%d0
        cmp.l   C_VOIC(%a0),%d0
        beq     sj_m0
        PLATE   4, %d3
        moveq   #2,%d0
        cmp.l   C_VOIC(%a0),%d0
        beq     sj_m0
        PLATE   8, %d5
        moveq   #3,%d0
        cmp.l   C_VOIC(%a0),%d0
        beq     sj_m0
        PLATE   12, %d5
sj_m0:  muls.l  C_MIX(%a0),%d3
        muls.l  C_MIX2(%a0),%d5
        add.l   %d5,%d3
        asr.l   #8,%d3
        asr.l   #7,%d3
        | ---- the sub-octaves: (q1 g1 + q2 g2) >> 15, q = +-16384 by each phase's top bit
        tst.l   C_SUB(%a0)
        beq.s   sj_q9
        move.l  S_SP(%a0),%d1
        add.l   C_S1(%a0),%d1
        move.l  %d1,S_SP(%a0)
        move.l  C_G1(%a0),%d0
        tst.l   %d1
        blt.s   sj_q1
        neg.l   %d0
sj_q1:  move.l  S_SP+4(%a0),%d1
        add.l   C_S2(%a0),%d1
        move.l  %d1,S_SP+4(%a0)
        move.l  C_G2(%a0),%d5
        tst.l   %d1
        blt.s   sj_q2
        neg.l   %d5
sj_q2:  add.l   %d5,%d0
        asr.l   #8,%d0
        asr.l   #7,%d0
        add.l   %d0,%d3
sj_q9:  | ---- saturation: 1.5 (x - x^3 / 3), x clamped to +-32767
        CLAMP   %d3, 32767
        move.l  %d3,%d0
        muls.l  %d3,%d0
        asr.l   #8,%d0
        asr.l   #7,%d0
        muls.l  %d3,%d0
        asr.l   #8,%d0
        asr.l   #7,%d0                  | x^3 (Q15)
        move.l  #10923,%d1
        muls.l  %d1,%d0
        asr.l   #8,%d0
        asr.l   #7,%d0                  | / 3
        sub.l   %d0,%d3
        move.l  %d3,%d0
        add.l   %d0,%d3
        add.l   %d0,%d3
        asr.l   #1,%d3                  | * 1.5
        | ---- TONE: the state-variable low-pass, skipped at 127
        moveq   #127,%d0
        cmp.l   C_TONE(%a0),%d0
        beq     sj_f9
        move.l  S_BP(%a0),%d0
        move.l  #23000,%d1
        muls.l  %d1,%d0
        asr.l   #8,%d0
        asr.l   #7,%d0
        sub.l   S_LO(%a0),%d3
        sub.l   %d0,%d3                 | hi
        CLAMP   %d3, 65535
        muls.l  C_F(%a0),%d3
        asr.l   #8,%d3
        asr.l   #7,%d3
        add.l   S_BP(%a0),%d3
        CLAMP   %d3, 65535
        move.l  %d3,S_BP(%a0)
        muls.l  C_F(%a0),%d3
        asr.l   #8,%d3
        asr.l   #7,%d3
        add.l   S_LO(%a0),%d3
        CLAMP   %d3, 65535
        move.l  %d3,S_LO(%a0)
        CLAMP   %d3, 32767
sj_f9:  | ---- out: the sample in the high word (already within +-32767)
        swap    %d3
        clr.w   %d3
        move.l  %d3,(%a2)+              | L
        move.l  %d3,(%a2)+              | R (the same: one voice)
        subq.l  #1,%d7
        bgt     sj_s0
        movem.l (%sp),%d2-%d7/%a2-%a5
        lea     40(%sp),%sp
        rts

| ---- sj_tri: d0 = a phase 0..0x1FFFF -> d0 = its triangle 0..32767
sj_tri:
        cmpi.l  #65536,%d0
        blt.s   sj_t1
        neg.l   %d0
        addi.l  #0x1FFFF,%d0
sj_t1:  lsr.l   #1,%d0
        rts

| ---- sj_swell: d0 = a triangle 0..32767 -> d0 = (SUB * (8192 + 3 d0 / 4)) >> 15
sj_swell:
        move.l  %d0,%d1
        add.l   %d1,%d0
        add.l   %d1,%d0
        asr.l   #2,%d0
        addi.l  #8192,%d0
        muls.l  C_SUB(%a0),%d0
        asr.l   #8,%d0
        asr.l   #7,%d0
        rts

| ---- the per-track state: the voice's block, then the renderer's fields
        .set    T_LATCHED,      SJ_SIZE         | 1 = a STROJ track (latched at a START)
        .set    T_WPTCH,        SJ_SIZE+4       | PTCH and RATE as the call found them
        .set    T_WRATE,        SJ_SIZE+8
        .set    T_POS,          SJ_SIZE+12      | the carrier's positions (20 bytes)
        .set    T_KNOBS,        SJ_SIZE+32      | this call's twelve knobs, 0..127 (12 bytes)
        .set    TS_SIZE,        SJ_SIZE+48      | 168

| ============================================================================
| stroj_render -- the FLEX renderer (the kind table's entry alone; a link of the chain beside others):
| render(track, ping, start, end) as the stock 0x40004008, its value returned.  On a STROJ track
| the stock renderer writes the header with PTCH / RATE neutral and the positions pinned (the
| frame's last call), then sj_voice writes the samples into it; every other track is stock.
| ============================================================================
stroj_render:
        lea     -48(%sp),%sp
        movem.l %d2-%d7/%a2-%a6,(%sp)
        move.l  CURSOR,%a2              | the header this call writes
        move.l  52(%sp),%d2             | track
        moveq   #NTRACKS-1,%d0
        cmp.l   %d0,%d2
        bhi     .Ls_stock
        move.l  #TS_SIZE,%d0
        muls.l  %d2,%d0
        lea     sj_tstate,%a3
        add.l   %d0,%a3
        move.l  FP_PTR,%a4
        moveq   #0,%d4                  | 1 = PTCH/RATE and the positions are neutralised for the call
        moveq   #16,%d1
        cmp.l   64(%sp),%d1             | the frame's last call?
        bne     .Ls_stock
        lea     NIBBLE,%a0
        add.l   %d2,%a0
        btst    #4,(%a0)                | a voice starts this frame: is the track STROJ?
        beq     .Ls_ison
        move.l  %d2,%d0
        bsr     sj_sigcur
        beq     .Ls_not
        tst.l   T_LATCHED(%a3)
        bne     .Ls_was
        move.l  %a3,%a0                 | a new STROJ track: the plates' phases spread
        bsr     sj_init
.Ls_was:
        moveq   #1,%d0
        move.l  %d0,T_LATCHED(%a3)
        move.l  RS_PTR,%a0
        clr.l   4(%a0)                  | the retrig count the packer latched: no stock retrigs
        bra     .Ls_ison
.Ls_not:
        clr.l   T_LATCHED(%a3)          | not ours: stock from here on
.Ls_ison:
        tst.l   T_LATCHED(%a3)
        beq     .Ls_stock
        bsr     sj_params               | this call's knobs, before the record is neutralised
        move.w  (%a4),%d0
        move.w  %d0,T_WPTCH+2(%a3)
        move.w  6(%a4),%d0
        move.w  %d0,T_WRATE+2(%a3)
        move.l  #NEUTRAL_PTCH,%d0       | the stock renderer computes rate 1.0 from these
        move.w  %d0,(%a4)
        move.l  #NEUTRAL_RATE,%d0
        move.w  %d0,6(%a4)
        bsr     sj_vpos                 | a0 = the voice's position fields
        lea     T_POS(%a3),%a1
        move.l  (%a0)+,(%a1)+
        move.l  (%a0)+,(%a1)+
        move.l  (%a0)+,(%a1)+
        move.l  (%a0)+,(%a1)+
        move.l  (%a0)+,(%a1)+
        moveq   #1,%d4
.Ls_stock:
        move.l  64(%sp),-(%sp)          | end
        move.l  64(%sp),-(%sp)          | start
        move.l  64(%sp),-(%sp)          | ping
        move.l  64(%sp),-(%sp)          | track
        jsr     STOCK_RENDER
        lea     16(%sp),%sp
        move.l  %d0,44(%sp)             | the stock return value, handed back
        move.l  52(%sp),%d2
        moveq   #NTRACKS-1,%d0
        cmp.l   %d0,%d2
        bhi     .Ls_done
        tst.l   %d4
        beq     .Ls_norest
        move.w  T_WPTCH+2(%a3),%d0      | restore PTCH and RATE for the DSP
        move.w  %d0,(%a4)
        move.w  T_WRATE+2(%a3),%d0
        move.w  %d0,6(%a4)
        bsr     sj_vpos                 | pin the carrier: the positions as they were before the call
        lea     T_POS(%a3),%a1
        move.l  (%a1)+,(%a0)+
        move.l  (%a1)+,(%a0)+
        move.l  (%a1)+,(%a0)+
        move.l  (%a1)+,(%a0)+
        move.l  (%a1)+,(%a0)+
        bra     .Ls_render
.Ls_norest:
        tst.l   T_LATCHED(%a3)
        beq     .Ls_done                | not a STROJ track: the stock samples stand
        bsr     sj_params               | a first call [0,n): the record is untouched
.Ls_render:
        moveq   #0,%d0
        move.b  3(%a2),%d0              | samples shipped by this call
        beq     .Ls_done
        move.l  %a3,%a0                 | the voice's block
        lea     T_KNOBS(%a3),%a1
        lea     16(%a2),%a2             | the L/R longs
        bsr     sj_voice
.Ls_done:
        move.l  44(%sp),%d0
        movem.l (%sp),%d2-%d7/%a2-%a6
        lea     48(%sp),%sp
        rts

| ---- sj_vpos: a0 := track d2's voice struct + V_POS.  Clobbers d0.
sj_vpos:
        move.l  #VOICE_STRIDE,%d0
        muls.l  %d2,%d0
        lea     VOICE_BASE,%a0
        add.l   %d0,%a0
        lea     V_POS(%a0),%a0
        rts

| ---- sj_params: the twelve knobs into T_KNOBS(a3).  PLAYBACK: the record's halfwords (raw << 8,
|      locks, scenes and LFOs applied), clamped 0..127.  SETUP: the live lane's six bytes; the
|      selects (VOIC SUB1 SUB2 RYTM WAVE) are indices, turned into the knob values the voice reads
|      (sj_selk: the smallest value in each index's zone).  d2 = track, a4 = FP.  Clobbers d0, d1, a0, a1.
sj_params:
        lea     T_KNOBS(%a3),%a1
        moveq   #0,%d1
.Lpa_pb:
        moveq   #0,%d0
        move.w  (%a4,%d1.l*2),%d0
        lsr.l   #8,%d0
        cmpi.l  #127,%d0
        bls     .Lpa_1
        moveq   #127,%d0
.Lpa_1:
        move.b  %d0,(%a1,%d1.l)
        addq.l  #1,%d1
        moveq   #6,%d0
        cmp.l   %d0,%d1
        blt     .Lpa_pb
        moveq   #CV_STRIDE,%d0
        muls.l  %d2,%d0
        lea     CURVALS+LANE_SETUP,%a0
        add.l   %d0,%a0
        move.l  %a2,-(%sp)
        lea     sj_selk,%a2             | 6 x 8 bytes: index -> knob value (BRTH: 0xff = as is)
        moveq   #0,%d1
.Lpa_su:
        moveq   #0,%d0
        move.b  (%a0,%d1.l),%d0
        cmpi.l  #127,%d0
        bls     .Lpa_2
        moveq   #127,%d0
.Lpa_2:
        tst.b   (%a2)                   | 0xff (BRTH): the byte is the knob
        bmi     .Lpa_3
        cmpi.l  #7,%d0
        bls     .Lpa_4
        moveq   #7,%d0
.Lpa_4:
        move.b  (%a2,%d0.l),%d0
.Lpa_3:
        move.b  %d0,6(%a1,%d1.l)
        addq.l  #8,%a2
        addq.l  #1,%d1
        moveq   #6,%d0
        cmp.l   %d0,%d1
        blt     .Lpa_su
        move.l  (%sp)+,%a2
        rts

| ============================================================================
| sj_retrig -- Detour 0x4000c634 (8 bytes: `moveal 114(sp),a1; moveb (a0,a1.l),d0`): the frame
| builder's copy of a track's DSP command byte.  On a STROJ track any START form becomes the clean
| 0x30 (OCTA303's o3_retrig, after Tim Hastie's po_retrig: a trig on a sounding voice is posted
| 0x10|n and the DSP crossfades its old voice under the new one).  Beside other machines it is a link
| of the RETRIG chain: a track that is not ours goes to the next machine's routine, entered as at the
| site.
| ============================================================================
sj_retrig:
        movea.l 114(%sp),%a1            | displaced: the track
        lea     -8(%sp),%sp
        movem.l %d1/%a2,(%sp)
        move.l  %a1,%d1
        bsr     sj_latched
        tst.l   %d1
        .if     HK_MACHINE_ROWS
        .if     MC_HAS_RETRIG
        beq     .Lrt_not                | not a STROJ track: the next machine's
        .else
        beq     .Lrt_out
        .endif
        .else
        beq     .Lrt_out                | not a STROJ track: stock's byte stands
        .endif
        moveq   #0,%d1
        move.b  (%a0,%a1.l),%d1
        andi.l  #0x30,%d1
        beq     .Lrt_out                | no START of any form
        moveq   #0x30,%d1
        move.b  %d1,(%a0,%a1.l)
.Lrt_out:
        movem.l (%sp),%d1/%a2
        lea     8(%sp),%sp
        move.b  (%a0,%a1.l),%d0         | displaced: the byte for the packer's nibble byte
        jmp     RETRIG_RET
        .if     HK_MACHINE_ROWS
        .if     MC_HAS_RETRIG
.Lrt_not:                               | entered as its own detour: it replays the load of a1
        movem.l (%sp),%d1/%a2
        lea     8(%sp),%sp
        jmp     MC_NEXT_RETRIG
        .endif
        .endif

| ---- sj_latched: d1 = track -> d1 = 1 when it is a latched STROJ track, else 0.  Everything else kept.
sj_latched:
        cmpi.l  #NTRACKS,%d1
        bcc     .Lla_no
        move.l  %a2,-(%sp)
        move.l  %d0,-(%sp)
        move.l  #TS_SIZE,%d0
        muls.l  %d1,%d0
        lea     sj_tstate,%a2
        move.l  T_LATCHED(%a2,%d0.l),%d1
        move.l  (%sp)+,%d0
        move.l  (%sp)+,%a2
        rts
.Lla_no:
        moveq   #0,%d1
        rts

| ============================================================================
| THE MACHINE: row 5 of the track's machine list.  ANALOG BD's seams and contracts
| (modules/analog-bassdrum/machine.s) for one machine with no engine pool; the signature, the
| record and the validator in OCTA303 v7.0's form (modules/octa303/octa303.s).
| ============================================================================

| ---- sj_sig: a0 = Part', d0 = track -> d0 = 1 when the track is STROJ (FLEX, signed), else 0
|      (flags set).  Clobbers d1.
sj_sig:
        move.l  %a1,-(%sp)
        moveq   #7,%d1
        cmp.l   %d1,%d0
        bhi     .Lsg_no
        moveq   #0,%d1
        move.b  0x22(%a0,%d0.l),%d1
        subq.l  #1,%d1                  | FLEX
        bne     .Lsg_no
        moveq   #30,%d1
        muls.l  %d0,%d1
        move.l  %a0,%a1
        add.l   %d1,%a1
        moveq   #0,%d1
        move.b  SIG_OFF(%a1),%d1
        cmpi.l  #0x53,%d1               | 'S'
        bne     .Lsg_no
        move.b  SIG_OFF+1(%a1),%d1
        cmpi.l  #0x4a,%d1               | 'J'
        bne     .Lsg_no
        move.b  SIG_OFF+2(%a1),%d1
        cmpi.l  #1,%d1
        bne     .Lsg_no
        moveq   #1,%d0
        bra     .Lsg_x
.Lsg_no:
        moveq   #0,%d0
.Lsg_x:
        move.l  (%sp)+,%a1
        tst.l   %d0
        rts

| ---- sj_curpart: a0 = the current part's Part', d1 = 1 (0 when the bank pointer is not set).
sj_curpart:
        move.l  BANK_PTR,%d1
        cmpi.l  #0x40000000,%d1
        bcs     .Lcp_no
        move.l  %d1,%a0
        adda.l  #PART_OFF,%a0
        mvz.b   PART_IDX,%d1
        andi.l  #3,%d1
        move.l  %d0,-(%sp)
        move.l  #PART_SIZE,%d0
        muls.l  %d0,%d1
        add.l   %d1,%a0
        move.l  (%sp)+,%d0
        moveq   #1,%d1
        rts
.Lcp_no:
        moveq   #0,%d1
        rts

| ---- sj_sigcur: d0 = track -> d0 = 1 (flags set) when it is STROJ in the current part.  Clobbers d1, a0.
sj_sigcur:
        bsr     sj_curpart
        tst.l   %d1
        bne     sj_sig
        moveq   #0,%d0
        rts

| ---- sj_row_type (ANALOG BD's ab_row_type): d0 = a machine byte, a0 = where it was read ->
|      d0 = SJ_ROW for the current part's machine byte of a signed track, else d0 unchanged; beside
|      other machines the next one's row type for a track that is not ours.  Everything but d0 kept.
sj_row_type:
        lea     -12(%sp),%sp
        movem.l %d1/%a0-%a1,(%sp)
        moveq   #FLEX,%d1
        cmp.l   %d1,%d0
        bne     .Lty_x
        move.l  %a0,%a1
        bsr     sj_curpart
        tst.l   %d1
        beq     .Lty_1
        move.l  %a1,%d1
        sub.l   %a0,%d1
        subi.l  #0x22,%d1               | the track, if a1 is a machine byte
        cmpi.l  #7,%d1
        bhi     .Lty_1
        move.l  %d1,%d0
        bsr     sj_sig
        beq     .Lty_1
        moveq   #SJ_ROW,%d0
        bra     .Lty_x
.Lty_1:
        moveq   #FLEX,%d0
.Lty_x:
        movem.l (%sp),%d1/%a0-%a1
        lea     12(%sp),%sp
        .if     HK_MACHINE_ROWS
        .if     MC_HAS_TYPE
        cmpi.l  #SJ_ROW,%d0
        beq     .Lty_rts
        jmp     MC_NEXT_TYPE            | not ours: the next machine's (it keeps all but d0)
.Lty_rts:
        .endif
        .endif
        rts

| ---- sj_sigwrite: a0 = Part' (in the bank blob), d0 = track, d1 = 1 sign / 0 unsign, in the Part and
|      its shadow.  Signing an unsigned copy first writes STROJ's twelve defaults into its FLEX PLAYBACK
|      and SETUP bytes; unsigning clears our signature only.  A signed track of the current part gets
|      its twelve bytes into the live lane too.  Everything kept.
sj_sigwrite:
        lea     -20(%sp),%sp
        movem.l %d0-%d2/%a0-%a1,(%sp)
        moveq   #30,%d2
        muls.l  %d2,%d0
        move.l  %a0,%a1
        add.l   %d0,%a1
        lea     SIG_OFF(%a1),%a1
        bsr     .Lsw_one
        move.l  %a1,%d2                 | the shadow: Part' - BANK - PART_OFF + SRAM_PART
        sub.l   BANK_PTR,%d2
        subi.l  #PART_OFF,%d2
        addi.l  #SRAM_PART,%d2
        move.l  %d2,%a1
        bsr     .Lsw_one
        tst.l   %d1                     | signed, in the current part: the live lane now, as the Part
        beq     .Lsw_done
        move.l  12(%sp),%a1             | Part'
        bsr     sj_curpart
        tst.l   %d1
        beq     .Lsw_done
        cmp.l   %a0,%a1
        bne     .Lsw_done
        move.l  (%sp),%d0               | the track
        moveq   #CV_STRIDE,%d2
        muls.l  %d0,%d2
        lea     CURVALS,%a0
        add.l   %d2,%a0
        moveq   #30,%d2
        muls.l  %d0,%d2
        add.l   %d2,%a1
        lea     0x30(%a1),%a1           | the FLEX PLAYBACK bytes
        moveq   #6,%d0
.Lsw_l:
        move.b  PAGE2_GAP(%a1),%d2
        move.b  %d2,LANE_SETUP(%a0)
        move.b  (%a1)+,%d2
        move.b  %d2,(%a0)+
        subq.l  #1,%d0
        bne     .Lsw_l
.Lsw_done:
        movem.l (%sp),%d0-%d2/%a0-%a1
        lea     20(%sp),%sp
        rts
.Lsw_one:                               | a1 = a copy's signature; clobbers d0, d2, a0
        moveq   #0,%d0                  | d0 = 1: this copy is signed
        moveq   #0,%d2
        move.b  (%a1),%d2
        cmpi.l  #0x53,%d2
        bne     .Lsw_s
        move.b  1(%a1),%d2
        cmpi.l  #0x4a,%d2
        bne     .Lsw_s
        move.b  2(%a1),%d2
        cmpi.l  #1,%d2
        bne     .Lsw_s
        moveq   #1,%d0
.Lsw_s:
        tst.l   %d1
        beq     .Lsw_clr
        tst.l   %d0
        bne     .Lsw_x                  | signed already: the author's knobs stand
        lea     sj_mdefs,%a0
        lea     -12(%a1),%a1            | the FLEX PLAYBACK bytes (Part' + 0x30 + 30*track)
        moveq   #6,%d0
.Lsw_d:
        move.b  6(%a0),%d2
        move.b  %d2,PAGE2_GAP(%a1)      | SETUP
        move.b  (%a0)+,%d2
        move.b  %d2,(%a1)+              | PLAYBACK
        subq.l  #1,%d0
        bne     .Lsw_d
        lea     6(%a1),%a1
        moveq   #0x53,%d2
        move.b  %d2,(%a1)
        moveq   #0x4a,%d2
        move.b  %d2,1(%a1)
        moveq   #1,%d2
        move.b  %d2,2(%a1)
        rts
.Lsw_clr:
        tst.l   %d0
        beq     .Lsw_x
        clr.b   (%a1)
        clr.b   1(%a1)
        clr.b   2(%a1)
.Lsw_x:
        rts

| ---- sj_mdesc: d0 = the machine's record, a RAM clone of the stock FLEX record with sj_mover's
|      fields replaced (built once, from the user's own ROM).  Clobbers d0, d1, a0, a1.
sj_mdesc:
        lea     -12(%sp),%sp
        movem.l %d2/%a2-%a3,(%sp)
        lea     sj_desc,%a2
        tst.b   sj_built
        bne     .Lcl_have
        lea     FLEX_P,%a0
        move.l  %a2,%a3
        move.l  #FLEX_DESC_LEN,%d1
.Lcl_cp:
        move.b  (%a0)+,(%a3)+
        subq.l  #1,%d1
        bne     .Lcl_cp
        lea     sj_mover,%a1
.Lcl_patch:
        mvs.w   (%a1)+,%d0
        bmi     .Lcl_built
        mvz.w   (%a1)+,%d1
        move.l  (%a1)+,%a0
        tst.l   %d1
        beq     .Lcl_patch
        move.l  %a2,%a3
        add.l   %d0,%a3
.Lcl_b:
        move.b  (%a0)+,(%a3)+
        subq.l  #1,%d1
        bne     .Lcl_b
        bra     .Lcl_patch
.Lcl_built:
        moveq   #1,%d0
        move.b  %d0,sj_built
.Lcl_have:
        move.l  %a2,%d0
        movem.l (%sp),%d2/%a2-%a3
        lea     12(%sp),%sp
        rts

| ---- the hooks -----------------------------------------------------------------------------------
| sj_machine_name -- Detour 0x400334d8 (`move.l d2,-(sp); move.l 8(sp),d1`): name(row) -> d0.
sj_machine_name:
        move.l  4(%sp),%d0
        cmpi.l  #SJ_ROW,%d0
        beq     .Lmn_sj
        .if     HK_MACHINE_ROWS
        .if     MC_HAS_NAME
        jmp     MC_NEXT_NAME            | not our row: the next machine's
        .endif
        .endif
        move.l  %d2,-(%sp)
        move.l  8(%sp),%d1
        jmp     0x400334de
.Lmn_sj:
        lea     sj_title,%a0
        move.l  %a0,%d0
        rts

| sj_src_names -- the lea at 0x4003c928: SRC SETUP's names, six rows (5 + the machines beside others).
        .align  4
sj_src_names:
        .long   0x400b3eac, 0x400b3e98, 0x400b7c67, 0x400b5413, 0x400b7a63, sj_title
        .if     HK_MACHINE_ROWS
        mc_names_tail                   | the other machines' names, in row order (the head's only)
        .endif

| sj_name_a / sj_name_b -- Detours 0x4003d718 / 0x4004c36a (`lea 0x400a78c8,a0`; then d1 = name[d0]).
sj_name_a:
        bsr     sj_name_pick
        jmp     0x4003d722
sj_name_b:
        bsr     sj_name_pick
        jmp     0x4004c374
sj_name_pick:
        bsr     sj_row_type
        lea     sj_src_names,%a0
        move.l  (%a0,%d0.l*4),%d1
        rts

| sj_setup_row -- Detour 0x4003c980 (`mvs.b (a0),d0; lea 24(sp),sp`).
sj_setup_row:
        mvs.b   (%a0),%d0
        lea     24(%sp),%sp
        bsr     sj_row_type
        jmp     0x4003c986

| sj_chooser_row -- Detour 0x400786c8 (`mvs.b (a0),d0; cmp.l d0,d2; bne 0x400786fc`); beside other
| machines HOOKS's box test takes this site.
sj_chooser_row:
        mvs.b   (%a0),%d0
        bsr     sj_row_type
        cmp.l   %d0,%d2
        bne     .Lcr_no
        jmp     0x400786ce
.Lcr_no:
        jmp     0x400786fc

| sj_setup_open -- Detour 0x400585dc (`move.b (a0),d3; mvs.b d3,d4; pea 0x400bb704`).
sj_setup_open:
        move.b  (%a0),%d3
        move.l  %d0,-(%sp)
        mvs.b   %d3,%d0
        bsr     sj_row_type
        move.l  %d0,%d3
        move.l  (%sp)+,%d0
        mvs.b   %d3,%d4
        pea     0x400bb704
        jmp     0x400585e6

| sj_chooser_open -- Detour 0x40078886 (`mvs.b (a0),d0; move.l d0,-(sp); pea 0x460e7386`).
sj_chooser_open:
        mvs.b   (%a0),%d0
        bsr     sj_row_type
        move.l  %d0,-(%sp)
        pea     0x460e7386
        jmp     0x40078890

| sj_tick -- Detour 0x4005221e (`jsr 0x4005213c; jsr 0x4007e940`): publish the machine's record as UI
| type 5's (the SETUP editor and drawer index PB_TABLE by the type sj_row_type returns); as the
| chain's head, every other machine's record as its row's.
sj_tick:
        jsr     0x4005213c
        jsr     0x4007e940
        bsr     sj_mdesc
        move.l  %d0,PB_TABLE+4*SJ_ROW
        .if     HK_MACHINE_ROWS
        mc_publish                      | each other machine's record as its row's type (the head's)
        .endif
        jmp     0x40052228

| sj_publish -- the same record from the head's tick hook, beside other machines.
sj_publish:
        bsr     sj_mdesc
        move.l  %d0,PB_TABLE+4*SJ_ROW
        rts

| sj_main_commit -- Detour 0x4007981c (`mvs.b (a0),d3; move.b d4,(a0); add.l d1,d0`): the machine
| list's commit, a1 = bank, d0 = part * PART_SIZE, d1 = track, d4 = the row.  Our row signs the track
| and stores FLEX; any other row unsigns it (beside other machines, then the next one's commit).
sj_main_commit:
        lea     -12(%sp),%sp
        movem.l %d0-%d1/%a0,(%sp)
        movea.l %a1,%a0
        adda.l  %d0,%a0
        adda.l  #PART_OFF,%a0
        move.l  %d1,%d0
        cmpi.l  #SJ_ROW,%d4
        bne     .Lmc_other
        moveq   #1,%d1
        bsr     sj_sigwrite
        moveq   #FLEX,%d4
        bra     .Lmc_store
.Lmc_other:
        moveq   #0,%d1
        bsr     sj_sigwrite
        .if     HK_MACHINE_ROWS
        .if     MC_HAS_MAIN_COMMIT
        movem.l (%sp),%d0-%d1/%a0
        lea     12(%sp),%sp
        jmp     MC_NEXT_MAIN_COMMIT     | the next machine signs its row; the last stores stock's
        .endif
        .endif
.Lmc_store:
        movem.l (%sp),%d0-%d1/%a0
        lea     12(%sp),%sp
        mvs.b   (%a0),%d3
        move.b  %d4,(%a0)
        add.l   %d1,%d0
        jmp     0x40079822

| sj_src_commit / 2 -- Detours 0x4005a616 / 0x4005a850 (`move.l SRC_CURSOR,d1`, then `move.b d1,(a0)`):
| SRC SETUP's two commits, a1 = bank, d0 = part * PART_SIZE, d2 = track.
sj_src_commit:
        pea     0x4005a61c
        bra     .Lsrc
sj_src_commit2:
        pea     0x4005a856
.Lsrc:
        move.l  SRC_CURSOR,%d1
        lea     -12(%sp),%sp
        movem.l %d0/%d2/%a0,(%sp)
        movea.l %a1,%a0
        adda.l  %d0,%a0
        adda.l  #PART_OFF,%a0
        move.l  %d2,%d0
        cmpi.l  #SJ_ROW,%d1
        bne     .Lsrc_o
        moveq   #1,%d1
        bsr     sj_sigwrite
        moveq   #FLEX,%d1
        bra     .Lsrc_go
.Lsrc_o:
        move.l  %d1,-(%sp)
        moveq   #0,%d1
        bsr     sj_sigwrite
        move.l  (%sp)+,%d1
        .if     HK_MACHINE_ROWS
        .if     MC_HAS_SRC_COMMIT
        movem.l (%sp),%d0/%d2/%a0
        lea     12(%sp),%sp
        move.l  (%sp)+,%d1              | our continuation: the next machine's commit pushes its own
        cmpi.l  #0x4005a61c,%d1
        bne     .Lsrc_2
        jmp     MC_NEXT_SRC_COMMIT
.Lsrc_2:
        jmp     MC_NEXT_SRC_COMMIT2
        .endif
        .endif
.Lsrc_go:
        movem.l (%sp),%d0/%d2/%a0
        lea     12(%sp),%sp
        rts

| sj_setup_edit6 / sj_setup_draw6 -- Detours 0x4003a52e / 0x4003cd98 (6 * machine): SETUP's editor and
| drawer address our row's bytes (beside other machines, every machine row's: 5 .. MC_ROWS_END - 1)
| as FLEX's.
sj_setup_edit6:
        .if     HK_MACHINE_ROWS
        cmpi.l  #5,%d2
        bcs     .Le6
        cmpi.l  #MC_ROWS_END,%d2
        bcc     .Le6
        .else
        cmpi.l  #SJ_ROW,%d2
        bne     .Le6
        .endif
        moveq   #FLEX,%d2
.Le6:
        move.l  %d2,%d0
        lsl.l   #3,%d0
        add.l   %d2,%d2
        sub.l   %d2,%d0
        jmp     0x4003a536
sj_setup_draw6:
        .if     HK_MACHINE_ROWS
        cmpi.l  #5,%d6
        bcs     .Ld6
        cmpi.l  #MC_ROWS_END,%d6
        bcc     .Ld6
        .else
        cmpi.l  #SJ_ROW,%d6
        bne     .Ld6
        .endif
        moveq   #FLEX,%d6
.Ld6:
        move.l  %d6,%d7
        lsl.l   #3,%d7
        add.l   %d6,%d6
        sub.l   %d6,%d7
        jmp     0x4003cda0

| sj_page -- Detour 0x40031ece (6 bytes: `move.l 0(a0,d0.l*4),d0; bra.s 0x40031ed6`), the page
| resolver's PLAYBACK table load (OCTA303's o3_page contract): d0 = machine, a0 = table, d3 = track,
| d1 = part index, a1 = bank blob; d0/d1/a0/a1 scratch, d2-d5 restored by the resolver's epilogue.
| A STROJ track (stored FLEX, signed) gets the machine's record; beside other machines a track that
| is not ours goes to the next machine's resolver with the entry state, as its own detour.
sj_page:
        .if     HK_MACHINE_ROWS
        .if     MC_HAS_PAGE
        lea     -12(%sp),%sp
        movem.l %d0-%d1/%a0,(%sp)
        .endif
        .endif
        move.l  0(%a0,%d0.l*4),%d0      | displaced: the machine's descriptor
        cmpi.l  #FLEX_P,%d0
        bne     .Lpg_not
        move.l  %d0,%d5
        move.l  #PART_SIZE,%d2
        muls.l  %d1,%d2
        add.l   %a1,%d2                 | the Part
        move.l  %d2,%a0
        adda.l  #PART_OFF,%a0
        move.l  %d3,%d0
        bsr     sj_sig
        beq     .Lpg_flex
        bsr     sj_mdesc                | ours: the machine's record
        bra     .Lpg_done
.Lpg_flex:
        move.l  %d5,%d0
.Lpg_not:
        .if     HK_MACHINE_ROWS
        .if     MC_HAS_PAGE
        movem.l (%sp),%d0-%d1/%a0       | not ours: the next machine's resolver, as its own detour
        lea     12(%sp),%sp
        jmp     MC_NEXT_PAGE
        .endif
        .endif
.Lpg_done:
        .if     HK_MACHINE_ROWS
        .if     MC_HAS_PAGE
        lea     12(%sp),%sp
        .endif
        .endif
        jmp     RESOLVER_RET

| sj_validate -- Detour 0x40002318 (the Part validator's entry): validate(Part'): the stock validator
| sees FLEX's defaults in each STROJ track's twelve PLAYBACK and SETUP bytes; ours are restored after
| (beside other machines the next one's validator runs in between, for its own tracks, then stock's).
sj_validate:
        lea     -112(%sp),%sp           | 96: the saved bytes (12 a track), 16: d2, d3, a2, a3
        movem.l %d2-%d3/%a2-%a3,96(%sp)
        move.l  116(%sp),%a2            | Part'
        moveq   #0,%d3                  | the signed tracks' mask
        moveq   #0,%d2
.Lv_t:
        move.l  %d2,%d0
        move.l  %a2,%a0
        bsr     sj_sig
        beq     .Lv_n
        moveq   #1,%d0
        lsl.l   %d2,%d0
        or.l    %d0,%d3
        bsr     sj_vptr                 | a0 = the PLAYBACK bytes, a1 = the save slot
        lea     STOCK_DEFS,%a3
        moveq   #6,%d1
.Lv_s:
        move.b  (%a0),%d0
        move.b  %d0,(%a1)
        move.b  PAGE2_GAP(%a0),%d0
        move.b  %d0,6(%a1)
        move.b  (%a3),%d0
        move.b  %d0,(%a0)
        move.b  6(%a3),%d0
        move.b  %d0,PAGE2_GAP(%a0)
        addq.l  #1,%a0
        addq.l  #1,%a1
        addq.l  #1,%a3
        subq.l  #1,%d1
        bne     .Lv_s
.Lv_n:
        addq.l  #1,%d2
        moveq   #8,%d0
        cmp.l   %d0,%d2
        blt     .Lv_t
        move.l  %a2,-(%sp)
        jsr     sj_stock_validate
        addq.l  #4,%sp
        move.l  %d0,%a3                 | the validator's result
        moveq   #0,%d2
.Lv_r:
        btst    %d2,%d3
        beq     .Lv_rn
        bsr     sj_vptr
        moveq   #6,%d1
.Lv_rr:
        move.b  (%a1),%d0
        move.b  %d0,(%a0)
        move.b  6(%a1),%d0
        move.b  %d0,PAGE2_GAP(%a0)
        addq.l  #1,%a0
        addq.l  #1,%a1
        subq.l  #1,%d1
        bne     .Lv_rr
.Lv_rn:
        addq.l  #1,%d2
        moveq   #8,%d1
        cmp.l   %d1,%d2
        blt     .Lv_r
        move.l  %a3,%d0
        movem.l 96(%sp),%d2-%d3/%a2-%a3
        lea     112(%sp),%sp
        rts
sj_vptr:                                | d2 = track, a2 = Part' -> a0 = Part' + 0x30 + 30*track, a1 = 4 + sp + 12*track
        moveq   #30,%d0
        muls.l  %d2,%d0
        lea     0x30(%a2),%a0
        add.l   %d0,%a0
        moveq   #12,%d0
        muls.l  %d2,%d0
        lea     4(%sp),%a1
        add.l   %d0,%a1
        rts
sj_stock_validate:
        .if     HK_MACHINE_ROWS
        .if     MC_HAS_VALIDATE
        jmp     MC_NEXT_VALIDATE        | the next machine's tracks, then stock
        .endif
        .endif
        lea     -96(%sp),%sp
        movem.l %d2-%d7/%a2-%a6,(%sp)
        jmp     0x40002320

| sj_lfo_name -- Detour 0x4003bff0 (`mvs.b (a0),d0; lea 0x400d5f38,a0`, 8 bytes; beside other machines
| a link of the LFO chain): the LFO PMTR formatter's PLAYBACK names.
| a0 = Part + 0x8eda2 + track, d1 = the track.  On a STROJ track the machine's record goes to a2
| (NOTE SPRD INTV FM SUB TONE) and the formatter resumes at 0x4003c058; else the displaced
| instructions and 0x4003c054.  The formatter keeps d1, d2, a4 across here; scratch d0, a0, a1.
sj_lfo_name:
        mvs.b   (%a0),%d0               | displaced: the machine
        moveq   #FLEX,%d3
        cmp.l   %d3,%d0
        bne     .Llf_stock
        move.l  %d1,-(%sp)
        suba.l  %d1,%a0
        suba.l  #0x22,%a0               | Part' (Part + 0x8ed80)
        move.l  %d1,%d0
        bsr     sj_sig                  | (clobbers d1)
        beq     .Llf_flex
        bsr     sj_mdesc                | d0 = the machine's record (keeps d2, a2, a3)
        move.l  (%sp)+,%d1
        movea.l %d0,%a2
        jmp     0x4003c058
.Llf_flex:
        move.l  (%sp)+,%d1
        .if     HK_MACHINE_ROWS
        .if     MC_HAS_LFO
        adda.l  %d1,%a0                 | not ours: the next machine's, entered as at the site
        adda.l  #0x22,%a0               | (a0 = Part + 0x8eda2 + track again)
        jmp     MC_NEXT_LFO
        .endif
        .endif
        moveq   #FLEX,%d0
.Llf_stock:
        lea     PB_TABLE,%a0            | displaced
        jmp     0x4003c054

| sj_chrom -- Detour 0x4004fc58 (jsr over 10 bytes: `lea (4,a2,a2.l*4),a2; mvz.b 0x100b14cf,d0`;
| beside other machines a link of the CHROM chain): the CHROMATIC key ->
| pitch, track d2, key index a2 = 0..24 (12 = TRIG 13).  On a STROJ track NOTE is semitones, so the
| key is too: raw = 52 + idx (TRIG 13 = the NOTE knob's 64 = C2); every other track the stock
| 5 * idx + 4.  Scratch: d0, d1, a0, a1.
sj_chrom:
        movea.l BANK_PTR,%a0
        mvz.b   PART_IDX,%d0
        move.l  #PART_SIZE,%d1
        muls.l  %d1,%d0
        adda.l  %d0,%a0                 | the Part
        move.l  %a0,%a1
        adda.l  #MACH_OFF,%a1
        mvz.b   (%a1,%d2.l),%d0
        cmpi.l  #FLEX,%d0
        bne     .Lch_stock
        adda.l  #PART_OFF,%a0
        move.l  %d2,%d0
        bsr     sj_sig
        beq     .Lch_stock
        lea     64-12(%a2),%a2          | semitones: raw = 52 + idx
        bra     .Lch_out
.Lch_stock:
        .if     HK_MACHINE_ROWS
        .if     MC_HAS_CHROM
        jmp     MC_NEXT_CHROM           | not ours: the next machine's, entered as at the site
        .endif
        .endif
        move.l  %a2,%d0                 | displaced (as plain arithmetic): raw = 5 * idx + 4
        lsl.l   #2,%d0
        add.l   %a2,%d0
        addq.l  #4,%d0
        move.l  %d0,%a2
.Lch_out:
        mvz.b   PART_IDX,%d0            | displaced: the part
        rts

| ---- the formatters: fmt(buf, value) -> length (stock's contract; scratch d0, d1, a0, a1)
sj_fmt_note:                            | raw 40..112 = C0..C6 (the voice: MIDI = raw - 28)
        move.l  8(%sp),%d0
        subi.l  #40,%d0
        bpl     .Lfn_lo
        moveq   #0,%d0
.Lfn_lo:
        moveq   #95,%d1
        cmp.l   %d1,%d0
        ble     .Lfn_hi
        move.l  %d1,%d0
.Lfn_hi:
        suba.l  %a1,%a1                 | the octave
.Lfn_oct:
        moveq   #12,%d1
        cmp.l   %d1,%d0
        blt     .Lfn_name
        sub.l   %d1,%d0
        addq.l  #1,%a1
        bra     .Lfn_oct
.Lfn_name:
        move.l  %a1,%d1
        lea     sj_notes,%a1
        add.l   %d0,%a1
        add.l   %d0,%a1                 | two bytes a name
        move.l  4(%sp),%a0
        move.b  (%a1)+,(%a0)+
        moveq   #0,%d0
        move.b  (%a1),%d0
        cmpi.l  #0x20,%d0               | "C " or "C#"
        beq     .Lfn_dig
        move.b  %d0,(%a0)+
.Lfn_dig:
        addi.l  #0x30,%d1
        move.b  %d1,(%a0)+
        clr.b   (%a0)
        move.l  %a0,%d0
        sub.l   4(%sp),%d0
        rts
sj_fmt_intv:                            | 8 zones of 16
        move.l  8(%sp),%d0
        lsr.l   #4,%d0
        lea     sj_lintv,%a1
        moveq   #7,%d1
        bra     .Lfl_idx
sj_fmt_tone:                            | 127 = OFF (the filter is not computed)
        moveq   #127,%d0
        cmp.l   8(%sp),%d0
        bne     .Lft_n
        lea     sj_loff,%a1
        moveq   #0,%d1
        moveq   #0,%d0
        bra     .Lfl_idx
.Lft_n:
        jmp     FMT_PLAIN
sj_fmt_brth:                            | 0 = OFF (the breath stands still)
        tst.l   8(%sp)
        bne     .Lfb_n
        lea     sj_loff,%a1
        moveq   #0,%d1
        moveq   #0,%d0
        bra     .Lfl_idx
.Lfb_n:
        jmp     FMT_PLAIN
sj_fmt_voic:                            | index + 1
        moveq   #1,%d0
        add.l   8(%sp),%d0
        lea     FMT_D,%a0
        bra     .Lfv_p
sj_fmt_sub:                             | "/2" .. "/8"
        moveq   #2,%d0
        add.l   8(%sp),%d0
        lea     sj_f_div,%a0
.Lfv_p:
        move.l  %d0,-(%sp)
        move.l  %a0,-(%sp)
        move.l  12(%sp),-(%sp)
        jsr     SPRINTF
        lea     12(%sp),%sp
        rts
sj_fmt_rytm:
        lea     sj_lrytm,%a1
        moveq   #4,%d1
        bra     sj_fmt_lbl
sj_fmt_wave:
        lea     sj_lwave,%a1
        moveq   #3,%d1
sj_fmt_lbl:                             | a1 = labels, 6 bytes each, d1 = the last
        move.l  8(%sp),%d0
.Lfl_idx:                               | d0 = the index
        tst.l   %d0
        bpl     .Lfl_1
        moveq   #0,%d0
.Lfl_1:
        cmp.l   %d1,%d0
        ble     .Lfl_2
        move.l  %d1,%d0
.Lfl_2:
        moveq   #6,%d1
        muls.l  %d1,%d0
        add.l   %d0,%a1
        move.l  4(%sp),%a0
        moveq   #0,%d0
.Lfl_3:
        move.b  (%a1)+,%d1
        move.b  %d1,(%a0)+
        beq     .Lfl_4
        addq.l  #1,%d0
        bra     .Lfl_3
.Lfl_4:
        rts

| ============================================================================
| the machine's record: sj_mover's fields over the stock FLEX record (OCTA303's o3_mover layout:
| offset, length, source; PLAYBACK P+0x16 names, P+0x5f defaults of slots 1..5, P+0x6a / P+0x9a slot
| 0's minimum and count, P+0xca formatters, P+0x12a slot 0's knob handler; SETUP P+0x3a names,
| P+0x64 defaults, P+0x82 minimums, P+0xb2 counts, P+0xe2 formatters, P+0x112 / P+0x142 list
| handlers, P+0x18a slot flags).  NOTE is raw 40..112 = C0..C6, one raw a detent.
| ============================================================================
        .align  4
sj_mover:
        .short  0x009, 9
        .long   sj_title
        .short  0x016, 36
        .long   sj_names
        .short  0x05f, 5
        .long   sj_mdefs+1
        .short  0x06a, 4
        .long   sj_note_min
        .short  0x09a, 4
        .long   sj_note_cnt
        .short  0x0ca, 24
        .long   sj_fmts
        .short  0x12a, 4
        .long   sj_zero6
        .short  0x03a, 36
        .long   sj_mnames
        .short  0x064, 6
        .long   sj_mdefs+6
        .short  0x082, 24
        .long   sj_zero6
        .short  0x0b2, 24
        .long   sj_mcnt
        .short  0x0e2, 24
        .long   sj_mfmts
        .short  0x112, 24
        .long   sj_zero6
        .short  0x142, 24
        .long   sj_zero6
        .short  0x18a, 8
        .long   sj_mflags
        .short  -1, 0
        .long   0
sj_note_min:
        .long   40
sj_note_cnt:
        .long   73
sj_zero6:
        .long   0, 0, 0, 0, 0, 0
sj_fmts:
        .long   sj_fmt_note, FMT_PLAIN, sj_fmt_intv, FMT_PLAIN, FMT_PLAIN, sj_fmt_tone
sj_mcnt:                                | VOIC 1-4, SUB1 /2../8, SUB2, BRTH 0..127, RYTM 5, WAVE 4
        .long   4, 7, 7, 128, 5, 4
sj_mfmts:
        .long   sj_fmt_voic, sj_fmt_sub, sj_fmt_sub, sj_fmt_brth, sj_fmt_rytm, sj_fmt_wave
sj_mflags:                              | OCTA303's: SETUP's six plain, PLAYBACK's as FLEX's
        .long   0x00001111, 0x11311311
sj_title:
        .ascii  "STROJ"
        .byte   0, 0, 0, 0
sj_names:                               | slots 0..5 (PTCH STRT LEN RATE RTRG RTIM), 6 bytes each
        .ascii  "NOTE"
        .byte   0, 0
        .ascii  "SPRD"
        .byte   0, 0
        .ascii  "INTV"
        .byte   0, 0
        .ascii  "FM"
        .byte   0, 0, 0, 0
        .ascii  "SUB"
        .byte   0, 0, 0
        .ascii  "TONE"
        .byte   0, 0
sj_mnames:
        .ascii  "VOIC"
        .byte   0, 0
        .ascii  "SUB1"
        .byte   0, 0
        .ascii  "SUB2"
        .byte   0, 0
        .ascii  "BRTH"
        .byte   0, 0
        .ascii  "RYTM"
        .byte   0, 0
        .ascii  "WAVE"
        .byte   0, 0
sj_mdefs:                               | a new STROJ track (the model's defaults): PLAYBACK, SETUP (indices)
        .byte   64, 40, 64, 40, 50, 90
        .byte   3, 0, 1, 40, 1, 0
sj_selk:                                | SETUP index -> the knob value the voice reads (8 a knob)
        .byte   0, 32, 64, 96, 96, 96, 96, 96           | VOIC: k >> 5
        .byte   0, 19, 37, 55, 74, 92, 110, 110         | SUB1: (k * 7) >> 7
        .byte   0, 19, 37, 55, 74, 92, 110, 110         | SUB2
        .byte   0xff, 0, 0, 0, 0, 0, 0, 0               | BRTH: the byte as it is
        .byte   0, 26, 52, 77, 103, 103, 103, 103       | RYTM: (k * 5) >> 7
        .byte   0, 32, 64, 96, 96, 96, 96, 96           | WAVE: k >> 5
sj_lintv:
        .asciz  "UNI"
        .byte   0, 0
        .asciz  "MIN3"
        .byte   0
        .asciz  "MAJ3"
        .byte   0
        .asciz  "4TH"
        .byte   0, 0
        .asciz  "5TH"
        .byte   0, 0
        .asciz  "MIN7"
        .byte   0
        .asciz  "OCT"
        .byte   0, 0
        .asciz  "OCT5"
        .byte   0
sj_lrytm:
        .asciz  "OFF"
        .byte   0, 0
        .asciz  "3:4"
        .byte   0, 0
        .asciz  "4:5"
        .byte   0, 0
        .asciz  "3:5"
        .byte   0, 0
        .asciz  "5:7"
        .byte   0, 0
sj_lwave:
        .asciz  "SIN"
        .byte   0, 0
        .asciz  "TRI"
        .byte   0, 0
        .asciz  "SAW"
        .byte   0, 0
        .asciz  "SQR"
        .byte   0, 0
sj_loff:
        .asciz  "OFF"
        .byte   0, 0
sj_f_div:
        .asciz  "/%d"
sj_notes:
        .ascii  "C C#D D#E F F#G G#A A#B "

| ---- the voice's tables (generated)
        .include "modules/stroj/stroj_tables.inc"

| ---- runtime state: zeros, depacked by the loader at every boot
        .align  4
sj_tstate:
        .fill   TS_SIZE*NTRACKS, 1, 0
sj_desc:
        .fill   SJ_DLEN, 1, 0
sj_built:
        .fill   4, 1, 0
