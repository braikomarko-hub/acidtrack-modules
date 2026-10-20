#!/usr/bin/env python3
"""Cross-check OCTA303's firmware facts against what is already proven in your checkout.

Run from the octabam root (after `make os && make recon`, submodules initialised):
    python3 tools/octa303/check_platform.py

A. every platform constant octa303.s shares (by name) with SYNTH MACHINE's poly.s must have the
   same value there -- poly.s 2.9 is the hardware-proven source of these addresses;
B. your stock image (out/raw/section_3_MAIN_OS.bin): the bytes at both detour sites, the kind
   table's FLEX entry, the stock formatter, and the descriptor fields the page clone replaces.
Nothing is written.  Exit status 1 on any FAIL.
"""
import re, sys
from pathlib import Path
ROOT = Path.cwd()
OURS = ROOT / 'modules/octa303/octa303.s'
TIM = ROOT / 'modules/synth/upstream/synth/poly.s'
IMG = ROOT / 'out/raw/section_3_MAIN_OS.bin'
BASE = 0x40000400
fail = 0
def say(ok, msg):
    global fail
    print(('  ok    ' if ok else '  FAIL  ') + msg); fail += (not ok)
def sets(path):
    out = {}
    for m in re.finditer(r'^\s*\.set\s+(\w+)\s*,\s*([^|\n]+)', path.read_text(errors='replace'), re.M):
        out[m.group(1)] = m.group(2).strip()
    return out
def val(v, table):
    try: return int(eval(v, {}, {k: val(x, table) for k, x in table.items() if k in v and k != v}))
    except Exception: return None

print('A. constants shared with poly.s', TIM)
if not OURS.exists() or not TIM.exists():
    print('  FAIL  missing %s' % (OURS if not OURS.exists() else TIM)); sys.exit(1)
a, b = sets(OURS), sets(TIM)
shared = sorted(set(a) & set(b) - {'ST_STRIDE', 'S_INC', 'S_PHC'})
platform = [k for k in shared if not k.startswith(('S_', 'T_', 'V_', 'CK_', 'RT_', 'CR_'))]
for k in platform:
    va, vb = val(a[k], a), val(b[k], b)
    say(va is not None and va == vb, '%-16s ours %-12s poly.s %s' % (k, a[k], b[k]))
for k in ('RS_PTR', 'VOICE_BASE', 'CURSOR', 'NIBBLE', 'FP_PTR', 'SETTINGS_BASE', 'FLEX_P', 'RESOLVER_RET',
          'CURVALS', 'CV_STRIDE'):
    say(k in platform, '%s is checked against poly.s' % k)

print('\nB. stock image', IMG)
if not IMG.exists():
    print('  FAIL  missing: run `make os && make recon`'); sys.exit(1)
img = IMG.read_bytes()
def at(x, n): return img[x - BASE:x - BASE + n]
say(at(0x40031ECE, 6) == bytes.fromhex('20300c006002'), 'resolver hook 0x40031ece = move.l 0(a0,d0.l*4),d0; bra.s')
say(at(0x4000C634, 8) == bytes.fromhex('226f007210309800'), 'command-byte copy 0x4000c634 = movea.l 114(sp),a1; move.b (a0,a1.l),d0')
say(int.from_bytes(at(0x400D6438, 4), 'big') == 0x40004008, 'kind table FLEX entry 0x400d6438 = 0x40004008')
say(at(0x4003C178, 2) != b'\0\0', 'FMT_PLAIN 0x4003c178 is code')
say(at(0x4004FC58, 10) == bytes.fromhex('45f2ac0471b9100b14cf'), 'CHROMATIC key -> pitch 0x4004fc58 = lea (4,a2,a2.l*4),a2; mvz.b 0x100b14cf,d0 (v6.4)')
say(at(0x40013A08, 2) != b'\0\0', 'SPRINTF 0x40013a08 is code (v6.4)')
say(at(0x4009BE96, 6) == bytes.fromhex('33c0800065b2'), 'the sequencer writes its step word 0x800065b2 at 0x4009be96 (v6.5 gate)')
say(at(0x4009BEBE, 6) == bytes.fromhex('13c1800065b6'), 'the sequencer writes its tick byte 0x800065b6 at 0x4009bebe (v6.5 gate)')
say(at(0x400B465D, 3) == b'%d\0', 'FMT_D 0x400b465d = "%d" (v6.4)')
d = at(0x400D31AE, 0x192)
names = [d[0x16 + 6 * i:0x1c + 6 * i].split(b'\0')[0].decode('latin1') for i in range(6)]
say(names == ['PTCH', 'STRT', 'LEN', 'RATE', 'RTRG', 'RTIM'], 'FLEX names at P+0x16: %s' % names)
say(int.from_bytes(d[0x6a:0x6e], 'big') == 4 and int.from_bytes(d[0x9a:0x9e], 'big') == 121,
    'stock PTCH range raw 4 + 121 values (5 units a semitone, +-12)')
print('\n%s' % ('ALL CHECKS PASSED' if not fail else '%d CHECK(S) FAILED' % fail))
sys.exit(1 if fail else 0)
