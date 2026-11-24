#!/usr/bin/env python3
"""test_stroj -- modules/stroj/stroj.s's voice == tools/stroj/stroj_ref.py, sample for sample.

The module's text runs under cfsim (tools/octa303/sim/cfsim.py), linted whole against the ColdFire
encoding limits, with every HOOKS flag 0 (STROJ alone): sj_voice against stroj_ref.Voice with each
knob at 0 and 127, many voices whose knobs change every call (and odd call lengths), a held drone;
the generated tables against stroj_ref's; and the ColdFire instructions a call costs.
Usage: python3 tools/stroj/test_stroj.py [voices]
"""
import ast
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'octa303', 'sim'))
import cfsim  # noqa: E402
import stroj_ref as R  # noqa: E402

SRC_PATH = os.path.join(ROOT, 'modules', 'stroj', 'stroj.s')
TAB_PATH = os.path.join(ROOT, 'modules', 'stroj', 'stroj_tables.inc')
STATE, KNOBS, OUT, STACK = 0x54000000, 0x54001000, 0x54002000, 0x5F000000

fails = 0
def check(name, ok, detail=''):
    global fails
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else '  ' + detail))
    fails += not ok


def hooks_flags():
    tree = ast.parse(open(os.path.join(ROOT, 'modules', 'hooks', 'manifest.py')).read())
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(getattr(t, 'id', None) == 'FLAGS' for t in n.targets)).values()


def source():
    """The module's text as STROJ alone builds it: every HOOKS flag 0, the tables inlined
    (cfsim has neither .include nor conditional assembly)."""
    flags = set(hooks_flags())
    s = open(SRC_PATH).read()
    assert s.count('        .include "remix.inc"') == 1
    s = s.replace('        .include "remix.inc"', ''.join('        .set    %s, 0\n' % f for f in flags), 1)
    s = s.replace('        .include "modules/stroj/stroj_tables.inc"', open(TAB_PATH).read(), 1)
    out, keep = [], [True]
    for line in s.split('\n'):
        tok = line.split('|')[0].split()
        if tok[:1] == ['.if']:
            if tok[1:] and tok[1] not in flags and not tok[1].startswith('MC_HAS_'):
                raise ValueError('.if on ' + ' '.join(tok[1:]) + ', not a HOOKS flag')
            keep.append(False)
        elif tok[:1] == ['.else']:
            keep[-1] = not keep[-1]
        elif tok[:1] == ['.endif']:
            keep.pop()
        elif all(keep):
            out.append(line)
    return '\n'.join(out)


# ---- 0. the tables in the module are the ones stroj_ref makes
import tempfile  # noqa: E402
with tempfile.TemporaryDirectory() as d:
    R.write_inc(os.path.join(d, 't.inc'))
    fresh = open(os.path.join(d, 't.inc')).read() == open(TAB_PATH).read()
check('modules/stroj/stroj_tables.inc is stroj_ref.py\'s (python3 tools/stroj/stroj_ref.py --write)', fresh)

try:
    CPU = cfsim.CPU(source())          # loads and lints the whole module
    check('the whole module assembles under cfsim and passes its ColdFire lint', True)
except Exception as e:  # noqa: BLE001
    check('the whole module assembles under cfsim and passes its ColdFire lint', False, str(e))
    print('RESULT 1 FAIL'); sys.exit(1)


def run_voice(seq, ns=None):
    cpu = CPU
    cpu.a[7] = STACK; cpu.a[0] = STATE
    cpu.call('sj_init')
    ref = R.Voice(); costs = []
    for i, k in enumerate(seq):
        n = ns[i] if ns else 16
        for j, v in enumerate(k): cpu.mem.w(KNOBS + j, 'b', v)
        cpu.a[0], cpu.a[1], cpu.a[2], cpu.d[0], cpu.a[7] = STATE, KNOBS, OUT, n, STACK
        keep = list(cpu.d[2:8]) + list(cpu.a[2:6])
        c0 = cpu.icount
        cpu.call('sj_voice')
        costs.append(cpu.icount - c0)
        if list(cpu.d[2:8]) + list(cpu.a[2:6]) != keep:
            return 'call %d: registers not restored' % i, costs
        L = [cpu.mem.r(OUT + 8 * s, 'l') for s in range(n)]
        Rr = [cpu.mem.r(OUT + 8 * s + 4, 'l') for s in range(n)]
        got = [cfsim.s32(x) >> 16 for x in L]
        want = ref.render(k, n)
        if got != want or L != Rr or any(x & 0xFFFF for x in L):
            s = next((s for s in range(n) if got[s] != want[s] or L[s] != Rr[s]), 0)
            return ('call %d sample %d: asm %d ref %d (L %08x R %08x), knobs %s'
                    % (i, s, got[s], want[s], L[s], Rr[s], k)), costs
    return None, costs


rnd = random.Random(30102026)
base = R.knobs({})
bad = None
for j in range(12):
    for v in (0, 127):
        k = list(base); k[j] = v
        err, _ = run_voice([k] * 6)
        if err: bad = bad or '%s=%d: %s' % (R.NAMES[j], v, err)
check('each knob at 0 and 127 (24 voices x 6 calls)', bad is None, bad or '')

voices = int(sys.argv[1]) if len(sys.argv) > 1 else 40
bad = None
for t in range(voices):
    seq = [[rnd.randrange(128) for _ in range(12)] for _ in range(8)]
    ns = [rnd.choice((16, 16, 16, 1, 7, 15)) for _ in range(8)]
    err, _ = run_voice(seq, ns)
    if err: bad = 'voice %d: %s' % (t, err); break
check('%d voices x 8 calls, random knobs every call' % voices, bad is None, bad or '')

err, _ = run_voice([R.knobs({'BRTH': 1, 'RYTM': 120, 'SUB': 127, 'FM': 127})] * 400)
check('held drone, 400 calls, fastest breath', err is None, err or '')

cheap = R.knobs({'VOIC': 0, 'FM': 0, 'SUB': 0, 'TONE': 127})
_, c1 = run_voice([cheap] * 4); _, c2 = run_voice([base] * 4)
print('COST instructions a 16-sample call (sj_voice): cheapest %d, defaults (all on) %d' % (c1[-1], c2[-1]))

print('RESULT', 'OK' if not fails else '%d FAIL' % fails)
sys.exit(1 if fails else 0)
