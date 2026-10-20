#!/usr/bin/env python3
"""OCTA303 v6.7 (dEVILish) test suite -- python3 tools/octa303/sim/test_octa303.py  (~1 min; OCTA303_FULL=1: ~4 min)

1. gen_tables --check; 2. cfsim lint (ColdFire limits; not an assembler);
3. BIT-EXACT: sy_render executed from the source text == ref303.render_call, every sample:
   saw/square, with and without the pedal, accents, trigless slides, carrier switches, split
   frames ([0,n) + [n,16)), extreme knobs;
4. the integration as poly.s 2.9 does it: four arguments re-pushed and the stock return handed
   back; PTCH/RATE = 0x4000/0x7f00 for the stock call on the frame's last call of a 303 track,
   restored after; the carrier's positions pinned; the retrig count cleared at a 303 START;
   ordinary samples, first calls of other tracks and dead voices untouched;
5. o3_retrig and o3_page / o3_pgdesc executed against their stock contexts.
"""
import os, sys, random, subprocess
FULL = os.environ.get("OCTA303_FULL") == "1"     # the gate runs the quick set; FULL=1 the whole one
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *

results = []
def check(name, ok, detail=''):
    results.append(bool(ok)); print(('PASS  ' if ok else 'FAIL  ') + name + (('   [' + detail + ']') if detail else ''))

r = subprocess.run([sys.executable, os.path.join(HERE, '..', 'gen_tables.py'), '--check'], capture_output=True, text=True)
check('tables_up_to_date', r.returncode == 0, r.stdout.strip())
try:
    rig = Rig(); check('coldfire_lint', True, '%d instructions' % len(rig.cpu.prog))
except Exception as e:
    check('coldfire_lint', False, str(e)); sys.exit(1)

NAMES = {'saw': 'TB303.WAV', 'square': 'TB303SQ.WAV', 'saw_dist': 'TB303D.WAV', 'square_dist': 'tb303sqd.wav'}
def W(tune=0, cut=64, res=64, env=64, dec=64, acc=0):
    return [0x4000 + tune * 256, cut << 8, res << 8, env << 8, dec << 8, acc << 8]

def run(script, track=0, rig=None):
    """script: frames (words, start_at or None, filename, alive).  start_at = sub-frame offset of a
    START this frame (0 = one call [0,16)).  Returns (asm, ref, first mismatch or None)."""
    rig = rig or Rig(); st = R.Track(); A = []; B = []
    for f, fr in enumerate(script):
        w, start_at, fname, alive = fr[:4]; df = fr[4] if len(fr) > 4 else None; fxslot = fr[5] if len(fr) > 5 else 1
        sq = fr[6] if len(fr) > 6 else None
        rdf = fr[7] if len(fr) > 7 else df                            # v6.7.2: the knobs the 303 should hear
        su = fr[8] if len(fr) > 8 else None                           # v7.0: the TB-303 machine's SETUP bytes
        sslot = 3 + (f % 2)                                          # the sample's FLEX slot
        rig.path(sslot, '/AUDIO/ACID/' + fname); rig.voice(track, alive, sslot)
        if su is not None: rig.machine(track, su)
        calls = [(0, 16)] if not start_at else [(0, start_at), (start_at, 16)]
        for (a, b) in calls:
            last = b == 16
            L, Rr = rig.call(track, w, a, b, start_at is not None, SILENCE, df, fxslot, sq)
            if L != Rr: return A, B, 'L != R'
            code = T.name_code(fname) if (last and start_at is not None) else None
            if su is not None and code is not None: code = min(su[0], 3)         # the machine: SETUP's WAVE
            ref = R.render_call(st, w, last and start_at is not None, -1 if code is None else code, b - a,
                               alive or su is not None, rdf if fxslot in (1, 2) else None, last=last, seq=sq,
                               setup=su)
            ref = [0] * (b - a) if ref is None else ref
            A += L; B += ref
            if L != ref:
                return A, B, len(A) - (b - a) + next(i for i in range(b - a) if L[i] != ref[i])
    return A, B, None

def scenario(fname, seed, frames=360, knobs=False):
    rnd = random.Random(seed); sc = []; w = W(); df = None; slot = 1
    for f in range(frames):
        start = None
        if f == 0 or rnd.random() < 0.05:
            start = rnd.choice([0, 0, 0, 5, 11])
            w = W(rnd.randint(-12, 24), rnd.randint(0, 127), rnd.randint(0, 127), rnd.randint(0, 127),
                  rnd.randint(0, 127), rnd.choice([0, 0, 64, 127]))
        elif rnd.random() < 0.03:
            w = list(w); w[0] = 0x4000 + rnd.randint(-12, 24) * 256      # a trigless PTCH lock: a slide
        if knobs and rnd.random() < 0.05:                                   # dEVILish moved, locked, taken away
            df = None if rnd.random() < 0.2 else tuple(rnd.choice([0, 1, 2, 3, 25, 50, 64, 100, 127, rnd.randint(0, 127)]) for _ in range(12))
            slot = rnd.choice([1, 2])
        sc.append((w, start, fname, True, df, slot))
    return sc

for nm, fn in NAMES.items():
    bad = None; total = 0
    for seed in range(2 if FULL else 1):
        A, B, mm = run(scenario(fn, seed * 31 + len(nm), 360 if FULL else 120))
        total += len(A)
        if mm is not None: bad = (seed, mm); break
    check('bit_exact_' + nm, bad is None, '%d samples' % total if bad is None else 'seed %d first mismatch @%s' % bad)

for nm, fn in NAMES.items():
    A, B, mm = run(scenario(fn, 77 + len(nm), 360 if FULL else 150, knobs=True))
    check('bit_exact_devilish_' + nm, mm is None, '%d samples' % len(A) if mm is None else 'mismatch @%s' % mm)
dfx = []
EXT = ((0,) * 12, (127,) * 12, (127, 127, 127, 127, 127, 0, 127, 1, 0, 2, 1, 1),
       (0, 127, 127, 0, 127, 127, 0, 2, 2, 1, 0, 1), (127, 127, 0, 127, 0, 50, 64, 0, 1, 0, 0, 0),
       (100, 127, 0, 96, 127, 50, 0, 1, 1, 0, 0, 0), T.DF_NEUTRAL)
for fn in ('TB303.WAV', 'TB303D.WAV'):
    for df in EXT:
        for slot in (1, 2):
            sc = [(W(12, 0, 127, 127, 0, 127), 0, fn, True, df, slot)] + [(W(12, 0, 127, 127, 0, 127), None, fn, True, df, slot)] * (40 if FULL else 12)
            sc += [(W(-12, 127, 127, 0, 127, 127), 5, fn, True, df, slot)] + [(W(-12, 127, 127, 0, 127, 0), None, fn, True, df, slot)] * (30 if FULL else 10)
            A, B, mm = run(sc); dfx.append(mm is None)
check('bit_exact_devilish_extremes_fx1_fx2', all(dfx))
_sc = lambda fx: [(W(0, 40, 115, 90, 50, 127), 0, 'TB303.WAV', True, (110, 127, 60, 96, 127, 50, 0, 1, 2, 1, 1, 1), fx)] + \
                 [(W(5, 40, 115, 90, 50, 0), None, 'TB303.WAV', True, (110, 127, 60, 96, 127, 50, 0, 1, 2, 1, 1, 1), fx)] * 12
_a1, _b1, _m1 = run(_sc(1)); _a2, _b2, _m2 = run(_sc(2)); _a0, _b0, _m0 = run(_sc(0))
check('devilish_fx1_and_fx2_both_read', _m1 is None and _m2 is None and _a1 == _a2 and _a1 != _a0)
st_a = R.Track(); st_b = R.Track(); same = True
for f in range(200):
    w = W(3, 60, 100, 90, 50, 127 if f % 7 == 0 else 0)
    same &= R.render_call(st_a, w, f % 9 == 0, 0, 16, True, None) == R.render_call(st_b, w, f % 9 == 0, 0, 16, True, T.DF_NEUTRAL)
check('devilish_neutral_is_absent', same)

# v6.7.2: dEVILish's page 1 through the scenes and the crossfader (MIDI.md Appendix C), as the frame
# builder morphs every effect's knobs on their way to the DSP
from harness import scene_morph
_lane = (25, 0, 0, 64, 0, 50, 0, 0, 1, 0, 0, 0)
def _pairs(slot, a, b):
    p = [0xFF] * 64
    for i in range(6):
        if a[i] is not None: p[2 * (slot + i)] = a[i]
        if b[i] is not None: p[2 * (slot + i) + 1] = b[i]
    return p
_A = (None, 127, 127, 0, None, 127); _B = (127, 0, None, 127, None, 3)
_ok = []
for fx, lslot in ((1, 18), (2, 24)):
    for xf, ao, bo in ((0, 0, 0), (127, 0, 0), (64, 0, 0), (1, 0, 0), (126, 0, 0), (64, 1, 0), (64, 0, 1), (64, 1, 1)):
        pr = _pairs(lslot, _A, _B)
        if fx == 1: pr[2 * 24] = 0; pr[2 * 24 + 1] = 0      # FX2's slot locked: FX1 must not read it
        rig = Rig(); rig.scene(0, pr, xf, ao, bo)
        exp = scene_morph(_lane[:6], pr, lslot, xf, ao, bo) + _lane[6:]
        sc = [(W(0, 60, 100, 90, 50, 127), 0, 'TB303.WAV', True, _lane, fx, None, exp)] + \
             [(W(0, 60, 100, 90, 50, 0), None, 'TB303.WAV', True, _lane, fx, None, exp)] * (20 if FULL else 6)
        A, B, mm = run(sc, rig=rig); _ok.append(mm is None)
check('devilish_scene_morph_bit_exact', all(_ok), '%d/%d' % (sum(_ok), len(_ok)))
_p = _pairs(18, _A, _B)
check('scene_morph_endpoints', scene_morph(_lane[:6], _p, 18, 127) == (25, 127, 127, 0, 0, 127)
      and scene_morph(_lane[:6], _p, 18, 0) == (127, 0, 0, 127, 0, 3)
      and scene_morph(_lane[:6], _p, 18, 64) == (76, 64, 64, 63, 0, 65))
check('scene_morph_no_locks_is_the_knob', all(scene_morph((k,) * 6, [0xFF] * 64, 18, xf) == (k,) * 6
                                               for k in range(128) for xf in (0, 1, 63, 64, 126, 127)))
_A2 = (127,) * 6; _B2 = (0,) * 6
rig = Rig(); rig.path(3, '/AUDIO/ACID/TB303.WAV'); rig.voice(0, True, 3); _l = []; st = R.Track()
for xf in list(range(0, 128, 9)) + [127]:                          # the fader moving under a held note
    rig.scene(0, _pairs(24, _A2, _B2), xf)
    exp = scene_morph(_lane[:6], _pairs(24, _A2, _B2), 24, xf) + _lane[6:]
    L, Rr = rig.call(0, W(0, 60, 100, 90, 50, 0), 0, 16, xf == 0, SILENCE, _lane, 2)
    ref = R.render_call(st, W(0, 60, 100, 90, 50, 0), xf == 0, T.name_code('TB303.WAV') if xf == 0 else -1, 16, True, exp, last=True)
    _l.append(L == ref)
check('devilish_scene_fader_moving', all(_l), '%d/%d' % (sum(_l), len(_l)))

ex = []
for fn in NAMES.values():
    for v in ((0, 0, 0, 0, 0, 127), (127, 127, 127, 127, 127, 127), (0, 127, 127, 0, 127, 127), (127, 0, 0, 127, 0, 0)):
        sc = [(W(12, *v[:4], v[4]), 0, fn, True)] + [(W(12, *v[:4], v[4]), None, fn, True)] * (80 if FULL else 25)
        sc += [(W(-12, *v[:4], 127), 7, fn, True)] + [(W(-12, *v[:4], 127), None, fn, True)] * (40 if FULL else 12)
        A, B, mm = run(sc); ex.append(mm is None)
check('bit_exact_extremes', all(ex))
sc = []
for k in range(8):
    fn = list(NAMES.values())[k % 4]
    sc += [(W(k, 90, 100, 80, 30, 127 * (k & 1)), 0, fn, True)] + [(W(k + 3, 90, 100, 80, 30, 0), None, fn, True)] * 30
A, B, mm = run(sc); check('bit_exact_carrier_switch', mm is None)

# ---------------------------------------------------------------- integration
rig = Rig(); feed = sample_feed(1)
rig.path(2, '/AUDIO/KICK.WAV'); rig.voice(1, True, 2); rig.seen.clear()
L, _ = rig.call(1, W(5), 0, 16, True, feed)
args, words = rig.seen[-1]
check('ordinary_sample_untouched', L == [feed(i) for i in range(16)])
check('args_repushed_return_handed_back', args == [1, 0x800000e4, 0, 16])
check('ordinary_sample_record_untouched', words == W(5))

rig = Rig(); rig.path(4, '/AUDIO/TB303.WAV'); rig.voice(2, True, 4)
rig.cpu.mem.w(RS + 4, 'l', 7)
pos0 = rig.positions(2); w = W(5, 90, 100); rig.seen.clear()
rig.call(2, w, 0, 16, True, SILENCE)
_, words_seen = rig.seen[-1]
check('neutral_ptch_rate_for_the_stock_call', words_seen[0] == 0x4000 and words_seen[3] == 0x7f00, '%04x %04x' % (words_seen[0], words_seen[3]))
check('ptch_rate_restored_after', [rig.cpu.mem.r(FRAME + 2 * i, 'w') for i in range(6)] == w)
check('carrier_positions_pinned', rig.positions(2) == pos0)
check('retrig_count_cleared_at_303_start', rig.cpu.mem.r(RS + 4, 'l') == 0)
rig.cpu.mem.w(RS + 4, 'l', 7)
rig.call(2, w, 0, 5, True, SILENCE)                       # a first call: nothing neutralised
_, words_first = rig.seen[-1]
check('first_call_not_neutralised', words_first == w)
check('retrig_count_kept_without_start', rig.cpu.mem.r(RS + 4, 'l') == 7)

rig = Rig(); rig.path(4, '/AUDIO/TB303.WAV'); rig.voice(3, True, 4)
rig.call(3, W(), 0, 16, True, SILENCE)
rig.voice(3, False, 4); feed = sample_feed(5)
L, _ = rig.call(3, W(), 0, 16, False, feed)
check('dead_voice_left_to_stock', L == [feed(i) for i in range(16)])

rig = Rig(); rig.path(4, '/AUDIO/TB303.WAV'); rig.path(6, '/AUDIO/LOOP.WAV')
rig.voice(0, True, 4); rig.call(0, W(), 0, 16, True, SILENCE)
rig.voice(0, True, 6); feed = sample_feed(8)
L, _ = rig.call(0, W(), 0, 16, True, feed)
L2, _ = rig.call(0, W(), 0, 16, False, feed)
check('slot_lock_back_to_a_sample_releases', L == [feed(i) for i in range(16)] and L2 == L)

rig = Rig(); rig.voice(4, True, None); feed = sample_feed(2)
L, _ = rig.call(4, W(), 0, 16, True, feed)
check('null_settings_pointer_ignored', L == [feed(i) for i in range(16)])

rig = Rig(); feed = sample_feed(3); ok = True; st = R.Track()
rig.path(4, '/AUDIO/TB303.WAV'); rig.path(5, '/AUDIO/HATS.WAV')
for f in range(30):
    rig.voice(0, True, 4); L, _ = rig.call(0, W(3, 80, 90), 0, 16, f == 0, SILENCE)
    ref = R.render_call(st, W(3, 80, 90), f == 0, 0, 16)
    rig.voice(7, True, 5); L2, _ = rig.call(7, W(), 0, 16, f % 4 == 0, feed)
    ok &= (L == ref) and (L2 == [feed(i) for i in range(16)])
check('tracks_independent', ok)

def level(fn, acc):
    st = R.Track(); out = []
    for f in range(320):
        r = R.render_call(st, W(0, 70, 100, 90, 60, acc), f == 0, T.name_code(fn), 16); out += [R.s32(x) >> 16 for x in r]
    return max(abs(x) for x in out), (sum(x * x for x in out) / len(out)) ** .5
for nm, fn in NAMES.items():
    pk, rms = level(fn, 0); pka, rmsa = level(fn, 127)
    check('audible_bounded_' + nm, 1000 < rms and pk < 32767, 'peak %d rms %.0f' % (pk, rms))
    if 'dist' not in nm: check('accent_louder_' + nm, rmsa > rms * 1.05, 'rms %.0f -> %.0f' % (rms, rmsa))

# ---------------------------------------------------------------- o3_retrig (detour 0x4000c634)
CMD = 0x46104d15
def retrig(track, byte, latched):
    rig = Rig(); c = rig.cpu; m = c.mem
    if latched:
        rig.path(4, '/AUDIO/TB303.WAV'); rig.voice(track, True, 4); rig.call(track, W(), 0, 16, True, SILENCE)
    m.w(CMD + track, 'b', byte)
    c.a[7] = STACK; m.w(STACK - 4 + 114, 'l', track)   # the detour is a jmp: cfsim's call() pushes a return address first
    c.a[0] = CMD; c.d[1] = 0x5151; c.a[2] = 0x6262; c.d[0] = 0
    got = []
    c.hooks[0x4000c63c] = lambda cpu: got.append(1)
    c.call('o3_retrig')
    return m.r(CMD + track, 'b'), c.d[0] & 0xFF, c.a[1], c.d[1], c.a[2], got
b, d0, a1, d1, a2, got = retrig(3, 0x15, True)
check('retrig_303_start_becomes_0x30', b == 0x30 and d0 == 0x30 and a1 == 3 and got)
check('retrig_registers_kept', d1 == 0x5151 and a2 == 0x6262)
b, d0, *_ = retrig(3, 0x15, False)
check('retrig_other_track_untouched', b == 0x15 and d0 == 0x15)
b, d0, *_ = retrig(3, 0x02, True)
check('retrig_non_start_untouched', b == 0x02 and d0 == 0x02)

# ---------------------------------------------------------------- o3_page (detour 0x40031ece) + o3_pgdesc
FLEX_P, TABLE, BANK = 0x400d31ae, 0x400d5f38, 0x41000000
def page(path, track=2, part=1, machine=1, slot=5, tblval=FLEX_P):
    rig = Rig(); c = rig.cpu; m = c.mem
    for i in range(0x192): m.w(FLEX_P + i, 'b', (i * 7 + 3) & 0xFF)
    m.w(TABLE + 4 * machine, 'l', tblval)
    m.w(BANK + part * 6322 + 0x8f04b + track * 5, 'b', slot)
    rig.path(slot, path)
    c.d[0], c.a[0], c.d[3], c.d[1], c.a[1] = machine, TABLE, track, part, BANK
    for r in (6, 7): c.d[r] = 0x7777 + r
    for r in range(2, 7): c.a[r] = 0x6600 + r
    c.a[7] = STACK; done = []
    c.hooks[0x40031ed6] = lambda cpu: done.append(1)
    c.call('o3_page')
    kept = all(c.d[r] == 0x7777 + r for r in (6, 7)) and all(c.a[r] == 0x6600 + r for r in range(2, 7)) and c.a[7] == STACK
    return c, c.d[0], kept and bool(done)
c, d0, kept = page('/AUDIO/ACID/TB303.WAV')
desc = c.consts['o3_desc']
check('page_tb303_gets_clone', d0 == desc and kept)
clone = bytes(c.mem.r(desc + i, 'b') for i in range(0x192)); stock = bytes((i * 7 + 3) & 0xFF for i in range(0x192))
exp = bytearray(stock); exp[0x9:0x12] = b'OCTA-303\0'
exp[0x16:0x3a] = b'TUNE\0\0CUT\0\0\0RES\0\0\0ENV\0\0\0DEC\0\0\0ACC\0\0\0'; exp[0x5f:0x64] = bytes([64, 64, 64, 64, 0])
for k in range(5): exp[0xce + 4 * k:0xd2 + 4 * k] = (0x4003c178).to_bytes(4, 'big')
exp[0xca:0xce] = c.consts['o3_fmt_tune'].to_bytes(4, 'big')            # v6.4: TUNE in semitones
exp[0x6a:0x6e] = (64 + T.TUNE_LO).to_bytes(4, 'big'); exp[0x9a:0x9e] = (T.TUNE_HI - T.TUNE_LO + 1).to_bytes(4, 'big')
exp[0x12a:0x12e] = bytes(4)
check('page_clone_fields', clone == bytes(exp), 'diff at %s' % [hex(i) for i in range(0x192) if clone[i] != exp[i]][:6])
check('page_stock_record_untouched', bytes(c.mem.r(FLEX_P + i, 'b') for i in range(0x192)) == stock)
check('page_tune_three_octaves', clone[0x16:0x1c] == b'TUNE\0\0' and clone[0x5e] == stock[0x5e]
      and int.from_bytes(clone[0x6a:0x6e], 'big') == 40 and int.from_bytes(clone[0x9a:0x9e], 'big') == 49
      and 4 <= 40 and 40 + 49 - 1 <= 124, 'raw 40..88 = -24..+24, inside the Part validator\'s 4..124')

# ---------------------------------------------------------------- v6.9: o3_stamp (a new 303 track's knobs at 64)
PBF, SHB, LANE = 0x8edb0, 0x1001614e, 0x80000810
def stamp(knobs, track=2, part=1, cur=1, slot=5, seen=None, path='/AUDIO/ACID/TB303.WAV', bankptr=True):
    rig = Rig(); c = rig.cpu; m = c.mem
    for i in range(0x192): m.w(FLEX_P + i, 'b', (i * 7 + 3) & 0xFF)
    m.w(TABLE + 4, 'l', FLEX_P)
    P = BANK + part * 6322
    m.w(P + 0x8f04b + track * 5, 'b', slot); rig.path(slot, path)
    if bankptr: m.w(0x46c82456, 'l', BANK)
    m.w(0x100b14cf, 'b', cur)
    rec = P + PBF + 30 * track; sh = rec + SHB - BANK; ln = LANE + 72 * track
    for k in range(6): m.w(rec + k, 'b', knobs[k]); m.w(sh + k, 'b', 0xEE); m.w(ln + k, 'b', 0xDD)
    if seen is not None: m.w(c.consts['o3_lastslot'] + track, 'b', seen + 1)
    c.d[0], c.a[0], c.d[3], c.d[1], c.a[1] = 1, TABLE, track, part, BANK
    for r in (6, 7): c.d[r] = 0x7777 + r
    for r in range(2, 7): c.a[r] = 0x6600 + r
    c.a[7] = STACK; done = []
    c.hooks[0x40031ed6] = lambda cpu: done.append(1)
    c.call('o3_page')
    kept = all(c.d[r] == 0x7777 + r for r in (6, 7)) and all(c.a[r] == 0x6600 + r for r in range(2, 7)) and c.a[7] == STACK
    g = lambda a: [m.r(a + k, 'b') for k in range(6)]
    return g(rec), g(sh), g(ln), kept and bool(done) and c.d[0] == c.consts['o3_desc'], m.r(c.consts['o3_lastslot'] + track, 'b')
z = [64, 0, 0, 0, 0, 0]
r, sh, ln, ok, seen = stamp(z)
check('stamp_new_track_knobs_64', r == [64, 64, 64, 64, 64, 0] and sh == [0xEE, 64, 64, 64, 64, 0xEE]
      and ln == [0xDD, 64, 64, 64, 64, 0xDD] and ok and seen == 6, 'part %s shadow %s lane %s' % (r, sh, ln))
r, sh, ln, ok, _ = stamp([64, 0, 0, 0, 0, 0], part=2, cur=0)
check('stamp_other_part_no_lane', r[1:5] == [64] * 4 and sh[1:5] == [64] * 4 and ln == [0xDD] * 6 and ok)
r, sh, ln, ok, _ = stamp([64, 0, 7, 0, 0, 0])
check('stamp_set_knobs_untouched', r == [64, 0, 7, 0, 0, 0] and sh == [0xEE] * 6 and ln == [0xDD] * 6 and ok)
r, sh, ln, ok, _ = stamp(z, seen=5)
check('stamp_same_slot_untouched', r == z and sh == [0xEE] * 6 and ln == [0xDD] * 6 and ok, 'the author set them to 0 himself')
r, sh, ln, ok, _ = stamp(z, bankptr=False)
check('stamp_outside_bank_part_only', r[1:5] == [64] * 4 and sh == [0xEE] * 6 and ln == [0xDD] * 6 and ok)
r, sh, ln, ok, seen = stamp(z, path='/AUDIO/KICK.WAV')
check('stamp_ordinary_sample_untouched', r == z and sh == [0xEE] * 6 and seen == 0)
r, sh, ln, ok, seen = stamp(z, track=7, part=3, cur=3, slot=127)
check('stamp_track8_part4', r[1:5] == [64] * 4 and sh[1:5] == [64] * 4 and ln[1:5] == [64] * 4 and seen == 128 and ok)

# ---------------------------------------------------------------- v7.0: o3_fmt_tune (TUNE as a note name)
def fmt_tune(v):
    rig = Rig(); c = rig.cpu; m = c.mem; called = []
    c.hooks[0x40013a08] = lambda cpu: called.append(1)
    buf = 0x81000000
    for i in range(8): m.w(buf + i, 'b', 0xAA)
    c.a[7] = STACK; m.w(STACK - 4, 'l', v); m.w(STACK - 8, 'l', buf); c.a[7] = STACK - 8
    for r in range(2, 7): c.d[r] = 0x7700 + r
    for r in range(2, 7): c.a[r] = 0x6600 + r
    c.call('o3_fmt_tune')
    b = b''
    for i in range(8):
        x = m.r(buf + i, 'b')
        if not x: break
        b += bytes([x])
    return b.decode('latin1'), c.d[0], c.a[7] == STACK - 8, all(c.d[r] == 0x7700 + r for r in range(2, 7)) and all(c.a[r] == 0x6600 + r for r in range(2, 7)), not called
ok = True; seen = []
for v, want in ((40, 'C1'), (52, 'C2'), (63, 'B2'), (64, 'C3'), (65, 'C#3'), (67, 'D#3'), (69, 'F3'), (73, 'A3'), (85, 'A4'), (88, 'C5'), (0, 'C0'), (127, 'B7')):
    txt, n, sp_ok, regs, nosp = fmt_tune(v)
    seen.append(txt); ok &= txt == want and n == len(want) and sp_ok and regs and nosp
check('fmt_tune_prints_note_names', ok, ' '.join(seen))

# ---------------------------------------------------------------- v6.4: o3_chrom (detour 0x4004fc58)
def chrom(path, idx, track=3, machine=1, slot=6, part=2):
    rig = Rig(); c = rig.cpu; m = c.mem
    m.w(0x46c82456, 'l', BANK); m.w(0x100b14cf, 'b', part)
    P = BANK + part * 6322
    m.w(P + 0x8eda2 + track, 'b', machine); m.w(P + 0x8f04b + track * 5, 'b', slot)
    rig.path(slot, path)
    c.d[2] = track; c.a[2] = idx; c.a[7] = STACK
    for r in (3, 4, 5, 6, 7): c.d[r] = 0x5500 + r
    for r in (3, 4, 5, 6): c.a[r] = 0x6600 + r
    c.call('o3_chrom')
    kept = all(c.d[r] == 0x5500 + r for r in (3, 4, 5, 6, 7)) and all(c.a[r] == 0x6600 + r for r in (3, 4, 5, 6)) \
        and c.a[7] == STACK and c.d[2] == track
    return c.a[2], c.d[0], kept
ok303 = all(chrom('/AUDIO/ACID/TB303.WAV', i)[:2] == (52 + i, 2) and chrom('/AUDIO/ACID/TB303.WAV', i)[2] for i in (0, 11, 12, 13, 24))
check('chrom_303_keys_are_semitones', ok303, 'idx 0/12/24 -> raw 52/64/76 = -12/0/+12')
check('chrom_303_square_dist_too', chrom('/AUDIO/tb303sqd.wav', 15)[0] == 67)
okst = all(chrom(p, i, **kw)[:2] == (5 * i + 4, 2) and chrom(p, i, **kw)[2]
           for i in (0, 12, 24) for p, kw in (('/AUDIO/KICK.WAV', {}), ('/AUDIO/SYNTH.WAV', {}),
                                               ('/AUDIO/TB303.WAV', {'machine': 0}), ('/AUDIO/TB303.WAV', {'slot': 200})))
check('chrom_stock_for_other_tracks', okst, 'raw = 5 * idx + 4')

# ---------------------------------------------------------------- v6.4: the pitch is semitones, three octaves
def f0(tune):
    st = R.Track(); R.render_call(st, W(tune, 127, 0, 0, 127, 0), True, 0, 16)
    return st.inc * 44100 / 2 ** 32
check('tune_semitones_four_octaves', abs(f0(0) - 130.81) < 0.2 and abs(f0(-12) - 65.41) < 0.1 and abs(f0(-24) - 32.70) < 0.1
      and abs(f0(24) - 523.25) < 0.8 and abs(f0(7) - 196.0) < 0.3, '%.1f %.1f %.1f Hz' % (f0(-12), f0(0), f0(24)))
check('tune_clamped_for_old_bytes', abs(f0(60) - f0(36)) < 0.01 and abs(f0(-60) - f0(-36)) < 0.01)
for p, nm in (('/AUDIO/tb303sqd.wav', 'lowercase_variant'), ):
    _, d0, kept = page(p); check('page_' + nm, d0 == desc and kept)
for p, nm, kw in (('/AUDIO/KICK.WAV', 'ordinary_sample', {}), ('/AUDIO/SYNTH.WAV', 'synth_name', {}),
                  ('/AUDIO/TB303.WAV', 'recorder_slot', {'slot': 200}),
                  ('/AUDIO/TB303.WAV', 'other_machine', {'tblval': 0x400d4000})):
    _, d0, kept = page(p, **kw)
    check('page_stock_for_' + nm, d0 == kw.get('tblval', FLEX_P) and kept)

# ---------------------------------------------------------------- dEVILish's id and the remix without it
import re as _re
_dm = open(os.path.join(ROOT, 'modules', 'devilish', 'manifest.py')).read()
_fx = int(_re.search(r'^FX_ID = (0x[0-9a-fA-F]+)', _dm, _re.M).group(1), 16)
_om = open(os.path.join(ROOT, 'modules', 'octa303', 'manifest.py')).read()
_ox = int(_re.search(r'^DEVIL_ID = (0x[0-9a-fA-F]+)', _om, _re.M).group(1), 16)
check('devilish_id_agrees', _fx == _ox == DEVIL_ID, 'devilish 0x%x, octa303 0x%x, harness 0x%x' % (_fx, _ox, DEVIL_ID))
_names = _re.findall(r'Param\(b"(\w+)"', _dm)
check('devilish_knob_order_is_the_engines', tuple(_names) == T.DF_NAMES, str(_names))
_defs = tuple(int(x) for x in _re.findall(r'Param\(b"\w+", (\d+)', _dm))
check('devilish_defaults_are_neutral', _defs == T.DF_NEUTRAL, str(_defs))
# a remix without dEVILish (remix.inc: DEVIL_ID 0x100): the knobs on FX2 are someone else's, neutral
rig = Rig(source(devilish=False)); rig.path(4, '/AUDIO/TB303.WAV'); rig.voice(0, True, 4)
st = R.Track(); ok = True
for f in range(40):
    w = W(0, 60, 110, 90, 50, 127 if f % 5 == 0 else 0)
    L, _r = rig.call(0, w, 0, 16, f == 0, SILENCE, (127, 127, 127, 0, 127, 0, 127, 2, 2, 2, 1, 1), 2)
    ok &= L == R.render_call(st, w, f == 0, 0, 16, True, None)
check('no_devilish_in_remix_is_neutral', ok)

# ---------------------------------------------------------------- v6.5 / v7.0: the 303's gate (SETUP's GATE)
GF = ('gmode', 'gate', 'glvl', 'gstep', 'lstep', 'ltick', 'idle', 'kmax', 'tps', 'gnew', 'gel', 'gend',
      'gsel', 'fcnt', 'fpt', 'fseen', 'gelf')
GOFF = {'gmode': 248, 'gate': 252, 'glvl': 256, 'gstep': 260, 'lstep': 264, 'ltick': 268, 'idle': 272,
        'kmax': 276, 'tps': 280, 'gnew': 284, 'gel': 288, 'gend': 292,
        'gsel': 344, 'fcnt': 348, 'fpt': 352, 'fseen': 356, 'gelf': 360}
check('gate_state_offsets_are_the_sources', all(Rig().cpu.consts['S_' + f.upper()] == GOFF[f] for f in GF))
def gate_fuzz(n, seed):
    """o3_gate run on random states and inputs == ref303.gate_frame, every field"""
    rnd = random.Random(seed); rig = Rig(); c = rig.cpu; m = c.mem; base = c.consts['o3_state']
    for it in range(n):
        t = rnd.randrange(8); L = rnd.choice([16, 16, 32, 64, 1, 2, 7, 0, 99])
        st = R.Track()
        LL = L if 1 <= L <= 64 else 16
        st.gmode = rnd.randint(0, 1); st.gate = rnd.randint(0, 1); st.glvl = rnd.randint(0, 32767)
        st.gstep = rnd.randrange(LL); st.lstep = rnd.randrange(LL); st.ltick = rnd.randrange(6)
        st.idle = rnd.choice([0, 1, 5, T.GATE_IDLE - 1, T.GATE_IDLE]); st.kmax = rnd.randrange(12)
        st.tps = rnd.choice([0, 3, 6, 12]); st.gnew = rnd.randint(0, 1)
        st.gel = rnd.choice([0, 1, 2, 3, 5, 9, 4095, 4096]); st.gend = rnd.choice([0, 3, 6, 7, 12, 18, 30])
        st.gsel = rnd.choice([0, 1, 1]); st.fseen = rnd.randint(0, 1)
        st.fcnt = rnd.choice([0, 1, 2, 3, 4094, 4095]); st.fpt = rnd.choice([0, 0, 1, 2, 3, 7, 40])
        st.gelf = rnd.choice([0, 1, 5, 6, 7, 13, 14, 15, 65534, 65535])
        step = rnd.choice([st.lstep, (st.lstep + 1) % LL, st.gstep, (st.gstep + 1) % LL, rnd.randrange(300)])
        tick = rnd.choice([st.ltick, rnd.randrange(12)])
        seq = (rnd.choice([127, 0, 64]), step, tick, rnd.getrandbits(64), L)
        a3 = base + t * 512
        for f in GF: m.w(a3 + GOFF[f], 'l', getattr(st, f) & M32)
        rig.seq(t, seq)
        c.d[2] = t; c.a[3] = a3; c.a[7] = STACK
        for r in (3, 4, 5, 6): c.d[r] = 0x4400 + r
        c.call('o3_gate')
        R.gate_frame(st, seq)
        got = {f: R.s32(m.r(a3 + GOFF[f], 'l')) for f in GF}
        want = {f: getattr(st, f) for f in GF}
        if got != want or any(c.d[r] != 0x4400 + r for r in (3, 4, 5, 6)) or c.a[7] != STACK:
            return 'case %d: %s' % (it, {f: (got[f], want[f]) for f in GF if got[f] != want[f]})
    return None
bad = gate_fuzz(3000 if FULL else 800, 5)
check('gate_state_machine_bit_exact', bad is None, bad or 'random states and inputs, every field')

PATG = [(0, 1, 0), (12, 0, 1), (7, 0, 0), (None, 0, 0), (0, 0, 1), (3, 1, 1), (5, 0, 0), (0, 0, 0)] * 2
SLIDES = sum(1 << ((i + 1) % 16) for i, p in enumerate(PATG) if p[2])
def gate_script(fname, steps=32, tf=2, setup=None, alive=True):
    """the sequencer sped up: 6 ticks a step, tf frames a tick; PATG's trigs, slides as trigless steps;
    setup = the TB-303 machine's SETUP bytes (None: a TB303* sample)"""
    sc = []
    for f in range(steps * 6 * tf):
        k = f // tf; sq = (127, k // 6, k % 6, SLIDES, 16)
        st_i = (k // 6) % 16; first = f % (6 * tf) == 0
        n, acc, sl = PATG[st_i]; prev = PATG[(st_i - 1) % 16]
        trig = first and n is not None and not prev[2]
        tune = n if n is not None else (prev[0] or 0)
        if not trig and prev[2] and n is not None: tune = n            # the slide's lock
        w = W(tune, 30, 110, 80, 40, 120 if acc else 0)
        sc.append((w, 0 if trig else None, fname, alive, None, 1, sq, None, setup))
    return sc
okg = True
for wv in (0, 1, 2, 3):
    A, B, mm = run(gate_script('KICK.WAV', setup=(wv, 1, 64, 0, 0, 64))); okg &= mm is None
check('bit_exact_machine_gate_303', okg, 'WAVE SAW SQR SAW+D SQR+D, GATE 303, slides, rests, 32 steps')
A0, _, mm0 = run(gate_script('KICK.WAV', setup=(1, 0, 90, 60, 100, 20), alive=False))
check('bit_exact_machine_gate_off_dead_voice', mm0 is None, 'GATE OFF, FINE/SLID/DRIV/ACCV moved, no sample voice')
st_a = R.Track(); st_b = R.Track(); same = True
for f, fr in enumerate(gate_script('TB303.WAV')):
    ra = R.render_call(st_a, fr[0], fr[1] is not None, 0, 16, True, None, last=True, seq=fr[6])
    rb = R.render_call(st_b, fr[0], fr[1] is not None, 0, 16, True, None)
    same &= ra == rb
check('gate_off_for_a_tb303_sample', same, 'no machine: the AMP decides, v6.9 sample for sample')
_, _, mm1 = run(gate_script('TB303SQD.WAV'))
check('bit_exact_tb303_sample_with_sequencer', mm1 is None)
def gate_len(tf, setup=(0, 1, 64, 0, 0, 64)):
    """frames from a START to the gate's close, the sequencer at tf frames a tick (no slide)"""
    st = R.Track(); n = None
    for f in range(6 * tf * 4):
        k = f // tf; sq = (127, k // 6, k % 6, 0, 16)
        R.render_call(st, W(), f == 0 or f == 6 * tf * 2, 0, 16, True, None, last=True, seq=sq, setup=setup)
        if f >= 6 * tf * 2 and n is None and st.gate == 0: n = f - 6 * tf * 2
    return n
_gl = [gate_len(tf) for tf in (2, 3, 4)]
check('gate_303_is_3_5_of_6_clocks', _gl == [7, 11, 14], 'closes after %s frames at 12/18/24 frames a step (Whittle: 58%%)' % _gl)
check('gate_off_never_closes', gate_len(2, (0, 0, 64, 0, 0, 64)) is None)

# ---------------------------------------------------------------- v7.0: the TB-303 machine's bit-exact runs
def mscen(seed, frames):
    rnd = random.Random(seed); sc = []; w = W(); su = [0, 0, 64, 0, 0, 64]; df = None; slot = 1
    for f in range(frames):
        start = None
        if f == 0 or rnd.random() < 0.06:
            start = rnd.choice([0, 0, 5, 11])
            w = W(rnd.randint(-24, 24), rnd.randint(0, 127), rnd.randint(0, 127), rnd.randint(0, 127),
                  rnd.randint(0, 127), rnd.choice([0, 0, 64, 127]))
        if rnd.random() < 0.05:                                            # SETUP moved or locked
            i = rnd.randrange(6); su = list(su)
            su[i] = rnd.choice([0, 1, 2, 3, 4, 63, 64, 65, 127, 200, rnd.randint(0, 127)])
        if rnd.random() < 0.03:
            df = None if rnd.random() < 0.4 else tuple(rnd.randint(0, 127) for _ in range(12)); slot = rnd.choice([1, 2])
        k = f // 2; sq = (127, k // 6, k % 6, rnd.getrandbits(16), 16)
        sc.append((w, start, 'KICK.WAV', rnd.random() < 0.7, df, slot, sq, df, tuple(su)))
    return sc
_bad = None
for seed in range(3 if FULL else 1):
    A, B, mm = run(mscen(900 + seed, 400 if FULL else 160))
    if mm is not None: _bad = (seed, mm); break
check('bit_exact_machine_setup_page', _bad is None, 'WAVE GATE FINE SLID DRIV ACCV moved, dEVILish on/off, dead voices'
      if _bad is None else 'seed %d mismatch @%s' % _bad)
def _setup_effect(i, v):
    sc = [(W(0, 40, 100, 80, 60, 127), 0, 'KICK.WAV', True, None, 1, None, None, tuple(v if j == i else T.SETUP_NEUTRAL[j] for j in range(6)))]
    sc += [(W(0, 40, 100, 80, 60, 0), None, 'KICK.WAV', True, None, 1, None, None, sc[0][8])] * 30
    A, B, mm = run(sc); return A if mm is None else None
_n = _setup_effect(0, 0)
_eff = {nm: _setup_effect(i, v) for i, v, nm in ((0, 1, 'WAVE'), (2, 100, 'FINE'), (3, 100, 'SLID'), (4, 127, 'DRIV'), (5, 0, 'ACCV'))}
check('machine_setup_knobs_act', _n is not None and all(a is not None and a != _n for nm, a in _eff.items() if nm != 'SLID'),
      'WAVE FINE DRIV ACCV change the sound (SLID: the next slide)')
_sm = run([(W(0, 40, 100, 80, 60, 0), 0, 'TB303.WAV', True, None, 1, None, None, T.SETUP_NEUTRAL)] +
          [(W(0, 40, 100, 80, 60, 0), None, 'TB303.WAV', True, None, 1, None, None, T.SETUP_NEUTRAL)] * 30)
_ss = run([(W(0, 40, 100, 80, 60, 0), 0, 'TB303.WAV', True)] + [(W(0, 40, 100, 80, 60, 0), None, 'TB303.WAV', True)] * 30)
check('machine_neutral_is_the_tb303_sample', _sm[2] is None and _ss[2] is None and _sm[0] == _ss[0])

# ---------------------------------------------------------------- v7.0: the machine's registration helpers
PP = lambda part: BANK + 0x8ed80 + part * 6322
def mrig(part=1, cur=None, sig=((2, b'TB\x01'),), types=None):
    rig = Rig(); c = rig.cpu; m = c.mem
    m.w(0x46c82456, 'l', BANK); m.w(0x100b14cf, 'b', part if cur is None else cur)
    P = PP(part)
    for t in range(8): m.w(P + 0x22 + t, 'b', (types or [1] * 8)[t])
    for t, b in sig:
        for i, x in enumerate(b): m.w(P + 0x3c + 30 * t + i, 'b', x)
    return rig, c, m, P
def sig(t, **kw):
    rig, c, m, P = mrig(**kw); c.a[0] = P; c.d[0] = t; c.a[7] = STACK; c.a[1] = 0x1234
    c.call('o3_sig'); return c.d[0], c.a[1] == 0x1234
check('sig_reads_the_signature', sig(2) == (1, True) and sig(3)[0] == 0 and sig(2, sig=((2, b'TB\x02'),))[0] == 0
      and sig(2, sig=((2, b'AB\x01'),))[0] == 0 and sig(2, types=[1, 1, 3, 1, 1, 1, 1, 1])[0] == 0 and sig(9)[0] == 0,
      'FLEX + T B 1 only (ANALOG BD\'s A B 1 is not ours)')
def otype(v, off, **kw):
    rig, c, m, P = mrig(**kw); c.a[0] = P + 0x22 + off if off is not None else 0x80001234; c.d[0] = v
    a0 = c.a[0]; c.d[1] = 0x77; c.a[1] = 0x88; c.a[7] = STACK
    c.call('o3_type'); return c.d[0], (c.a[0], c.d[1], c.a[1], c.a[7]) == (a0, 0x77, 0x88, STACK)
check('type_maps_signed_flex_to_row_5', otype(1, 2) == (5, True) and otype(1, 3) == (1, True) and otype(0, 2)[0] == 0
      and otype(1, None) == (1, True) and otype(1, 2, cur=0)[0] == 1 and otype(1, 9)[0] == 1)
def swrite(t, flag, pre=None, part=1, cur=None):
    rig, c, m, P = mrig(part=part, cur=cur, sig=pre or ())
    for i in range(72): m.w(CURVALS + 72 * t + i, 'b', 0xDD)
    sh = P - BANK - 0x8ed80 + 0x100a4ece
    for k in range(6):
        for base in (P, sh): m.w(base + 0x30 + 30 * t + k, 'b', 0x11 + k); m.w(base + 0x1e0 + 30 * t + k, 'b', 0x21 + k)
    if pre:
        for tt, b in pre:
            for i, x in enumerate(b): m.w(sh + 0x3c + 30 * tt + i, 'b', x)
    c.a[0] = P; c.d[0] = t; c.d[1] = flag; c.d[2] = 0x55; c.a[1] = 0x66; c.a[7] = STACK
    c.call('o3_sigwrite')
    kept = (c.a[0], c.d[0], c.d[1], c.d[2], c.a[1], c.a[7]) == (P, t, flag, 0x55, 0x66, STACK)
    g = lambda a, n: bytes(m.r(a + i, 'b') for i in range(n))
    swrite.lane = (g(CURVALS + 72 * t, 6), g(CURVALS + 72 * t + 0x20, 6), g(CURVALS + 72 * t + 6, 26))
    return [(g(b + 0x3c + 30 * t, 3), g(b + 0x30 + 30 * t, 6), g(b + 0x1e0 + 30 * t, 6)) for b in (P, sh)], kept
_w, _k = swrite(4, 1)
_d1, _d2 = bytes([64, 64, 64, 64, 64, 0]), bytes(T.SETUP_NEUTRAL)
check('sigwrite_new_machine_defaults', _k and all(x == (b'TB\x01', _d1, _d2) for x in _w), str(_w))
check('sigwrite_current_part_lane', swrite.lane == (_d1, _d2, b'\xdd' * 26), str(swrite.lane))
_w, _k = swrite(4, 1, cur=0)
check('sigwrite_other_part_no_lane', _k and swrite.lane == (b'\xdd' * 6, b'\xdd' * 6, b'\xdd' * 26) and all(x[0] == b'TB\x01' for x in _w))
_w, _k = swrite(4, 1, pre=((4, b'TB\x01'),))
check('sigwrite_reselect_keeps_the_knobs', _k and all(x == (b'TB\x01', bytes(range(0x11, 0x17)), bytes(range(0x21, 0x27))) for x in _w))
_w, _k = swrite(4, 0, pre=((4, b'TB\x01'),), part=3)
check('sigwrite_other_machine_unsigns', _k and all(x[0] == b'\0\0\0' and x[1] == bytes(range(0x11, 0x17)) for x in _w))
_w, _k = swrite(4, 0, pre=((4, b'AB\x01'),))
check('sigwrite_leaves_analog_bd_alone', _k and all(x[0] == b'AB\x01' for x in _w))
def validate():
    rig, c, m, P = mrig(sig=((2, b'TB\x01'), (7, b'TB\x01')))
    stock = [(i * 13 + 1) & 0x7F for i in range(12)]
    for i in range(12): m.w(0x400d320c + i, 'b', stock[i])
    for t in range(8):
        for k in range(6): m.w(P + 0x30 + 30 * t + k, 'b', 100 + k); m.w(P + 0x1e0 + 30 * t + k, 'b', 110 + k)
    seen = []
    def hook(cpu):
        mm = cpu.mem; sp = cpu.a[7]
        part = mm.r(sp + 96 + 4, 'l')
        seen.append([[mm.r(part + 0x30 + 30 * t + k, 'b') for k in range(6)] + [mm.r(part + 0x1e0 + 30 * t + k, 'b') for k in range(6)] for t in range(8)])
        regs = [mm.r(sp + 4 * i, 'l') for i in range(11)]
        for i, r in enumerate(range(2, 8)): cpu.d[r] = regs[i]
        for i, r in enumerate(range(2, 7)): cpu.a[r] = regs[6 + i]
        cpu.a[7] = sp + 96; cpu.d[0] = 0xAB
    c.hooks[0x40002320] = hook
    c.a[7] = STACK - 8; m.w(STACK - 8, 'l', P)
    for r in range(2, 8): c.d[r] = 0x3300 + r
    for r in range(2, 7): c.a[r] = 0x4400 + r
    c.call('o3_validate')
    kept = all(c.d[r] == 0x3300 + r for r in range(2, 8)) and all(c.a[r] == 0x4400 + r for r in range(2, 7)) and c.a[7] == STACK - 8
    after = [[m.r(P + 0x30 + 30 * t + k, 'b') for k in range(6)] + [m.r(P + 0x1e0 + 30 * t + k, 'b') for k in range(6)] for t in range(8)]
    own = list(range(100, 106)) + list(range(110, 116))
    return seen and all(seen[0][t] == (stock if t in (2, 7) else own) for t in range(8)) and after == [own] * 8 and kept and c.d[0] == 0xAB
check('validate_sees_flex_defaults_then_restores', validate())
def mdesc_built():
    rig = Rig(); c = rig.cpu; m = c.mem
    for i in range(0x192): m.w(FLEX_P + i, 'b', (i * 7 + 3) & 0xFF)
    c.a[7] = STACK; c.call('o3_mdesc'); d = c.d[0]
    return c, d, bytes(m.r(d + i, 'b') for i in range(0x192))
c, d, md = mdesc_built()
_pb = bytes(c.mem.r(c.consts['o3_desc'] + i, 'b') for i in range(0x192))
exp = bytearray(clone)
exp[0x3a:0x5e] = b''.join(n.encode().ljust(6, b'\0') for n in T.SETUP_NAMES); exp[0x64:0x6a] = bytes(T.SETUP_NEUTRAL)
for k in range(6):
    exp[0x82 + 4 * k:0x86 + 4 * k] = bytes(4); exp[0xb2 + 4 * k:0xb6 + 4 * k] = T.SETUP_COUNT[k].to_bytes(4, 'big')
    exp[0x112 + 4 * k:0x116 + 4 * k] = bytes(4); exp[0x142 + 4 * k:0x146 + 4 * k] = bytes(4)
exp[0xe2:0xfa] = b''.join(c.consts[n].to_bytes(4, 'big') for n in ('o3_fmt_wave', 'o3_fmt_gate', 'o3_fmt_fine')) + (0x4003c178).to_bytes(4, 'big') * 3
exp[0x18a:0x192] = bytes.fromhex('0000111111311311')
check('machine_record_fields', d == c.consts['o3_desc'] + 0x194 and md == bytes(exp) and _pb == bytes(0x192),
      'diff at %s' % [hex(i) for i in range(0x192) if md[i] != exp[i]][:6])
def mpage(signed, path='/AUDIO/KICK.WAV'):
    rig = Rig(); c = rig.cpu; m = c.mem
    for i in range(0x192): m.w(FLEX_P + i, 'b', (i * 7 + 3) & 0xFF)
    m.w(TABLE + 4, 'l', FLEX_P); part, track = 2, 5
    m.w(BANK + part * 6322 + 0x8f04b + track * 5, 'b', 9); rig.path(9, path)
    P = PP(part); m.w(P + 0x22 + track, 'b', 1)
    for i, x in enumerate(b'TB\x01' if signed else b'\0\0\0'): m.w(P + 0x3c + 30 * track + i, 'b', x)
    c.d[0], c.a[0], c.d[3], c.d[1], c.a[1] = 1, TABLE, track, part, BANK
    for r in (6, 7): c.d[r] = 0x7777 + r
    for r in range(2, 7): c.a[r] = 0x6600 + r
    c.a[7] = STACK; done = []
    c.hooks[0x40031ed6] = lambda cpu: done.append(1)
    c.call('o3_page')
    kept = all(c.d[r] == 0x7777 + r for r in (6, 7)) and all(c.a[r] == 0x6600 + r for r in range(2, 7)) and c.a[7] == STACK
    return c.d[0] - c.consts['o3_desc'] if c.d[0] != FLEX_P else 'stock', kept and bool(done)
check('page_machine_gets_its_record', mpage(True) == (0x194, True) and mpage(True, '/AUDIO/TB303.WAV') == (0x194, True)
      and mpage(False) == ('stock', True) and mpage(False, '/AUDIO/TB303.WAV') == (0, True))
def mchrom(signed, idx=0):
    rig = Rig(); c = rig.cpu; m = c.mem; part, track = 2, 3
    m.w(0x46c82456, 'l', BANK); m.w(0x100b14cf, 'b', part)
    P = BANK + part * 6322
    m.w(P + 0x8eda2 + track, 'b', 1); m.w(P + 0x8f04b + track * 5, 'b', 0xff)
    for i, x in enumerate(b'TB\x01' if signed else b'\0\0\0'): m.w(P + 0x8ed80 + 0x3c + 30 * track + i, 'b', x)
    c.d[2] = track; c.a[2] = idx; c.a[7] = STACK
    c.call('o3_chrom'); return c.a[2]
check('chrom_machine_keys_are_semitones', mchrom(True, 0) == 52 and mchrom(True, 24) == 76 and mchrom(False, 24) == 124)
def fmt(name, v):
    rig = Rig(); c = rig.cpu; m = c.mem; buf = 0x81000000; out = []
    c.hooks[0x40013a08] = lambda cpu: out.append((cpu.mem.r(cpu.a[7], 'l'), cpu.mem.r(cpu.a[7] + 4, 'l'), R.s32(cpu.mem.r(cpu.a[7] + 8, 'l'))))
    for i in range(8): m.w(buf + i, 'b', 0xAA)
    m.w(STACK - 4, 'l', v & M32); m.w(STACK - 8, 'l', buf); c.a[7] = STACK - 8
    for r in range(2, 7): c.d[r] = 0x7700 + r; c.a[r] = 0x6600 + r
    c.call(name)
    ok = c.a[7] == STACK - 8 and all(c.d[r] == 0x7700 + r and c.a[r] == 0x6600 + r for r in range(2, 7))
    if out: return out[0], ok
    b = b''
    for i in range(8):
        x = m.r(buf + i, 'b')
        if not x: break
        b += bytes([x])
    return (b.decode(), c.d[0]), ok
_fw = [fmt('o3_fmt_wave', v) for v in (0, 1, 2, 3, 9, -1)]
_fg = [fmt('o3_fmt_gate', v) for v in (0, 1, 5)]
check('fmt_wave_gate_labels', [x[0][0] for x in _fw] == ['SAW', 'SQR', 'SAW+D', 'SQR+D', 'SQR+D', 'SAW']
      and all(x[1] and x[0][1] == len(x[0][0]) for x in _fw + _fg) and [x[0][0] for x in _fg] == ['OFF', '303', '303'])
_ff = [fmt('o3_fmt_fine', v) for v in (0, 64, 127)]
c0 = Rig().cpu
check('fmt_fine_signed', [x[0] for x in _ff] == [(0x81000000, 0x400b465d, -64), (0x81000000, 0x400b465d, 0), (0x81000000, c0.consts['o3_f_plus'], 63)]
      and all(x[1] for x in _ff))

n = sum(results); print('\n%d/%d PASS' % (n, len(results))); sys.exit(0 if n == len(results) else 1)
