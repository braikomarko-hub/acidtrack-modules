"""STROJ -- a drone machine on the ColdFire: four plates and two sub-octaves.

Row 5 of the track's machine list (a FLEX track, signed 'S','J',1), its own PLAYBACK page NOTE SPRD
INTV FM SUB TONE and SETUP page VOIC SUB1 SUB2 BRTH RYTM WAVE.  Four "plates" in two nearly-tuned pairs
with cross phase modulation (after SOMA's Lyra-8), two sub-octaves (1/2..1/8 of the note) that swell at
their own rates (after Moog's Subharmonicon), a soft saturation and a state-variable low-pass; the
delay and the reverb are the track's FX.  The voice is integer arithmetic on the ColdFire, bit-exact
against tools/stroj/stroj_ref.py (test_stroj under cfsim).

The machine row takes the seams repeat98 measured for ANALOG BD (modules/analog-bassdrum) and OCTA303
v7.0 uses; the audio OCTA303's road (after Tim Hastie's SYNTH MACHINE 2.9): the kind table's FLEX
renderer, PTCH / RATE neutral and the carrier's positions pinned around the stock call, then the
voice's samples.  Beside other machines STROJ is the last link of HOOKS's machine_rows chain (its row
after theirs): each of its hooks hands what is not its own to the next machine's routine, entered as
at the site.  LFO SETUP's names and CHROMATIC are two links of their own (OCTA303 then STROJ).

Idea and listening: MaMarko.  Code: Claude (Anthropic).
"""
import os

from remix.schema import Category, Detour, Gate, Kind, Linked, Module, Poke, Proof, SymbolRef

H = bytes.fromhex
_HERE = os.path.relpath(os.path.dirname(os.path.realpath(__file__)))
_TOOLS = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "tools", "stroj")

KIND_TABLE_FLEX = 0x400D6438             # the kind table's FLEX entry (kind 1)
STOCK_RENDERER = 0x40004008              # its stock value, the sample renderer
RETRIG_HOOK = 0x4000C634                 # `movea.l 114(sp),a1; move.b (a0,a1.l),d0` (OCTA303's o3_retrig site)
RETRIG_STOCK = H("226f0072" "10309800")


def remix_inc(modules, remix=None):
    """remix.inc for stroj.s: modules/hooks's flags (machine_rows: the head beside OCTA303)."""
    from remix import hooks_flags
    return hooks_flags.inc("STROJ", modules)


MODULE = Module(
    name="stroj",
    key="STROJ",
    kind=Kind.CF_PATCH,
    category=Category.MACHINES,
    author="MaMarko",
    author_url="https://github.com/braikomarko-hub",
    doc=("STROJ: a drone machine (row 5 of the machine list, no sample needed). Four plates in two "
         "nearly-tuned pairs with cross phase modulation (Lyra-8) and two sub-octaves that swell at "
         "their own rates (Subharmonicon). PLAYBACK NOTE SPRD INTV FM SUB TONE, SETUP VOIC SUB1 SUB2 "
         "BRTH RYTM WAVE. A trig or a lock changes the chord without restarting the plates."),
    proof=Proof.PORT,
    proof_note=("the voice bit-exact against tools/stroj/stroj_ref.py under cfsim (test_stroj); the list, "
                "SETUP / PLAYBACK pages, signing and the audio at the outputs under the ColdFire port "
                "(verify_stroj_port, alone and beside OCTA303); not yet run on a unit"),
    linked=(
        Linked("stroj", os.path.join(_HERE, "stroj.s"), dram=True, include=remix_inc),
    ),
    symbol_refs=(
        SymbolRef(KIND_TABLE_FLEX, STOCK_RENDERER, "stroj", "stroj_render",
                  "kind table FLEX renderer -> STROJ stroj_render (a STROJ track plays the drone; "
                  "every other track the stock renderer)"),
    ),
    detours=(
        Detour(RETRIG_HOOK, RETRIG_STOCK, "stroj", "sj_retrig",
               "the frame builder's DSP command-byte copy: a START on a sounding STROJ track is "
               "posted as the clean 0x30 (no DSP crossfade of the one continuous stream)",
               kind="jmp", pad_to=8),
        Detour(0x4003BFF0, H("711041f9400d5f38"), "stroj", "sj_lfo_name",
               "LFO SETUP's destination names: a STROJ track's PLAYBACK row from the machine's record"),
        Detour(0x4004FC58, H("45f2ac04" "71b9100b14cf"), "stroj", "sj_chrom",
               "CHROMATIC key -> pitch: on a STROJ track NOTE is semitones (raw = 52 + key index), every "
               "other track the stock 5 * index + 4", kind="jsr", pad_to=10),
        Detour(0x40031ECE, H("20300c00" "6002"), "stroj", "sj_page",
               "page resolver PLAYBACK table load: a STROJ track gets the machine's record", kind="jmp"),
        # ANALOG BD's measured seams (modules/analog-bassdrum/manifest.py), the same sites and bytes
        Detour(0x400334D8, H("2f02222f0008"), "stroj", "sj_machine_name",
               "format machine row 5 as STROJ"),
        Detour(0x4003C928, H("4bf9400a78c8"), "stroj", "sj_src_names",
               "point SRC SETUP at six machine names", kind="lea"),
        Detour(0x4003D718, H("41f9400a78c8"), "stroj", "sj_name_a",
               "main page name lookup for the signed STROJ track"),
        Detour(0x4004C36A, H("41f9400a78c8"), "stroj", "sj_name_b",
               "second main page name lookup for the signed STROJ track"),
        Detour(0x4003C980, H("71104fef0018"), "stroj", "sj_setup_row",
               "SRC SETUP row highlights STROJ on a signed FLEX track"),
        Detour(0x400786C8, H("7110b480662e"), "stroj", "sj_chooser_row",
               "main chooser row highlights STROJ on a signed FLEX track"),
        Detour(0x400585DC, H("161079034879400bb704"), "stroj", "sj_setup_open",
               "SRC SETUP opens on STROJ for the signed track", pad_to=10),
        Detour(0x4005221E, H("4ebaff1c4eb94007e940"), "stroj", "sj_tick",
               "publish the STROJ record as UI type 5's", pad_to=10),
        Detour(0x40078886, H("71102f004879460e7386"), "stroj", "sj_chooser_open",
               "the track's machine list opens on STROJ for the signed track", pad_to=10),
        Detour(0x4007981C, H("77101084d081"), "stroj", "sj_main_commit",
               "admit STROJ at main chooser commit (stored as FLEX, signed)"),
        Detour(0x4005A616, H("2239460d5c30"), "stroj", "sj_src_commit",
               "admit STROJ at SRC SETUP commit"),
        Detour(0x4005A850, H("2239460d5c30"), "stroj", "sj_src_commit2",
               "the same at SRC SETUP's second commit path"),
        Detour(0x4003A52E, H("2002e788d4829082"), "stroj", "sj_setup_edit6",
               "SETUP's editor stores STROJ's row in the track's FLEX slot", pad_to=8),
        Detour(0x4003CD98, H("2e06e78fdc869e86"), "stroj", "sj_setup_draw6",
               "SETUP's drawer reads STROJ's row from the track's FLEX slot", pad_to=8),
        Detour(0x40002318, H("4fefffa048d77cfc"), "stroj", "sj_validate",
               "the Part validator reads a STROJ track's FLEX bytes as FLEX defaults", pad_to=8),
    ),
    pokes=(
        Poke(0x40079248, H("48780005"), H("48780006"), "machine chooser has six rows, STROJ the last"),
        Poke(0x400585FA, H("48780005"), H("48780006"), "SRC SETUP selector has six rows"),
        Poke(0x4003C950, H("7204"), H("7205"), "SRC SETUP name lookup admits STROJ"),
        Poke(0x40078678, H("7004"), H("7005"), "machine chooser draws STROJ"),
        Poke(0x400786CE, H("7004"), H("7005"), "machine chooser highlights STROJ"),
        Poke(0x40079904, H("7604"), H("7605"), "machine chooser persists STROJ"),
    ),
    conflicts=(
        ("SYNTH MACHINE", "both own the FLEX renderer entry 0x400d6438 and the command-byte copy 0x4000c634"),
        ("BLACKPYRAMIDS_303", "both are machine row 5 (the chooser, SRC SETUP and validator sites)"),
        ("SCALE QUANTIZER", "both take the CHROMATIC key -> pitch 0x4004fc58 (HOOKS's chrom_pitch joins "
                            "OCTA303 to it, not STROJ)"),
    ),
    gates=(
        Gate(os.path.join(_TOOLS, "test_stroj.py"), remix_arg=False),
        Gate("tools/verify/verify_stroj_port.py", remix_arg=False, stage="image"),
    ),
)
