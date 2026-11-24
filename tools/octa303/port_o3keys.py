#!/usr/bin/env python3
"""port_o3keys: OCTA303 v7.1's three panel changes under the ColdFire port, keys on the emulated panel.

    .venv/bin/python3 tools/octa303/port_o3keys.py [--remix octa303] [--project DIR]

Builds the remix and stages the project as tools/site/capture_manual.py does (its prepare()), boots it
under ot_emu with the panel (tools/verify/stems_panel.MenuPort), makes T1 an OCTA-303 track (SRC SETUP's
sixth row), turns GRID RECORDING on and reads the step locks of T1 in the current pattern
(bank + pattern * 0x8ed8 + 0x59 + step * 32, byte 0 = TUNE; docs/firmware/STEP_LOCKS.md):

1. TRIG 1 places a trig; [TRIG 1] + [UP] locks its TUNE an octave up (Part TUNE 64 -> 76).
2. [FUNC] + [TRIG 2] places a trigless lock on step 2: it gets step 1's note (76) at once.
3. TRIG 3, then [TRIG 3] + [DOWN]: 64 -> 52.
4. T2, a FLEX track: [TRIG 1] + [UP] leaves its locks alone (stock: the sample-lock list; NO closes it).
5. LFO SETUP on T1: a PNG, its PLAYBACK destinations to read as TUNE CUT RES ENV DEC ACC.

PNGs go to out/octa303/port_o3keys (O3KEYS_SHOTS=<dir> elsewhere)."""
import argparse, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'site')); sys.path.insert(0, str(ROOT / 'tools' / 'verify'))
sys.path.insert(0, str(ROOT / 'tools'))
import capture_manual as cm          # noqa: E402  (prepare: build + stage the card)
from stems_panel import MenuPort     # noqa: E402

BANK_PTR, PAT_IDX = 0x46c82456, 0x100b14d0
fails = 0


def check(name, ok, info=''):
    global fails
    print(('  [PASS] ' if ok else '  [FAIL] ') + name + (('  ' + info) if info else ''), flush=True)
    if not ok:
        fails += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--remix', default='octa303')
    cfg = Path.home() / '.octabam_project'
    ap.add_argument('--project', default=os.environ.get('OT_PROJECT') or (cfg.read_text().strip() if cfg.is_file() else ''))
    a = ap.parse_args()
    if not a.project:
        print('  [SKIP] port_o3keys: no project (OT_PROJECT=<dir>, --project or ~/.octabam_project)')
        return 0
    shots = Path(os.environ.get('O3KEYS_SHOTS', str(ROOT / 'out' / 'octa303' / 'port_o3keys')))
    shots.mkdir(parents=True, exist_ok=True)
    cm.OUT.mkdir(parents=True, exist_ok=True)
    work = cm.prepare(a.remix, Path(a.project), [])
    with MenuPort((work / 'image.bin').resolve(), (work / 'card.img').resolve(), 'MANUAL', 'SCREENS', False,
                  log_path=work / 'port_o3keys.log') as p:
        p.settle()
        shot = lambda name: p.png(shots / (name + '.png'))
        press = lambda name, n=1: [p.press(name, settle=80) for _ in range(n)]

        def rec(track):
            return p.long(BANK_PTR) + (p.peek(PAT_IDX, 1)[0] & 15) * 0x8ed8 + track * 0x91a

        def lock(track, step):
            return p.peek(rec(track) + 0x59 + 32 * step, 1)[0]

        def bits(track, off, step):
            return (p.peek(rec(track) + off + 7 - step // 8, 1)[0] >> (step % 8)) & 1

        # T1 an OCTA-303 track (capture_manual's capture_octa303)
        press('t1'); p.chord('func', 'pg_playback'); press('down', 5); press('yes'); press('no')
        press('pg_playback')
        shot('0_source')
        press('rec')                                     # GRID RECORDING
        # 1. a trig, then TRIG + UP
        press('trig1')
        check('trig 1 placed', bits(0, 0, 0) == 1)
        before = lock(0, 0)
        p.key('trig1', True); p.run(120); p.press('up', settle=120)
        shot('1_trig_up')
        p.key('trig1', False); p.run(200)
        check('[TRIG 1] + [UP]: TUNE an octave up', before == 0xff and lock(0, 0) == 76,
              'lock %s -> %s' % (before, lock(0, 0)))
        # 2. FUNC + TRIG 2: a trigless lock that ties into step 1's note
        p.chord('func', 'trig2'); p.run(200)
        tl = (bits(0, 8, 1), bits(0, 16, 1), bits(0, 0, 1))
        check('[FUNC] + [TRIG 2]: a trigless step', tl[0] or tl[1], 'trigless trig/lock/trig bits %s' % (tl,))
        check('the trigless step gets the previous note', lock(0, 1) == 76, 'lock %s' % lock(0, 1))
        shot('2_trigless')
        # 3. TRIG 3, then TRIG + DOWN
        press('trig3')
        p.key('trig3', True); p.run(120); p.press('down', settle=120)
        p.key('trig3', False); p.run(200)
        check('[TRIG 3] + [DOWN]: TUNE an octave down', lock(0, 2) == 52, 'lock %s' % lock(0, 2))
        # 4. a FLEX track: stock
        press('t2'); press('trig1')
        b2 = lock(1, 0)
        p.key('trig1', True); p.run(120); p.press('up', settle=200)
        shot('4_flex_trig_up')
        p.key('trig1', False); p.run(200); press('no')
        check('T2 (FLEX): [TRIG] + [UP] leaves its locks', lock(1, 0) == b2, 'lock %s -> %s' % (b2, lock(1, 0)))
        press('rec')                                     # GRID RECORDING off
        # 5. LFO SETUP on T1
        press('t1'); press('pg_lfo'); p.chord('func', 'pg_lfo'); p.run(300)
        shot('5_lfo_setup')
        press('no')
    print('port_o3keys: %d failure(s); PNGs in %s' % (fails, shots), flush=True)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
