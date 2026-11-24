#!/usr/bin/env python3
"""AtoMizer's render gates, through the native builder and dsp_host. Not hardware.

    python3 tools/verify/verify_atomizer.py

Needs your own OS 1.40C extraction at out/raw/section_3_MAIN_OS.bin and the patched DSP56300 tools
(vendor/dsp56300). It builds a private image in a temporary folder: the stock code built in and
AtoMizer in the space of DELAY, SPRING REV, PLATE REV and DARK REV (see DONORS: AtoMizer's 1,465
words need the run DARK REV's kept SPRING REV routine would otherwise split). The image, dumps and
renders are deleted.

Gates:
  source      init leaves r1/n1/m1 alone (verify_init_regs.py's scan); cycle_count.py prices the
              per-sample loop (dispatch + the worst feedback mode) and four instances fit a core's
              3120 usable cycles
  placement   the image builds and AtoMizer sits in the donor run on both payloads
  dry         MIX 0 is the input sample for sample: knobs still, every knob moving (MODE and FBMD
              too, so the slot clears mid-run), and with a trig split
  reference   the DSP against atomizer_ref.py, BIT-IDENTICAL: every MODE, every FBMD, FREZ held
              and by threshold, SYNC with a tempo, SPRD, on core 0; a set again on core 1
  automation  every knob moving every few blocks (MODE and FBMD included) with a split of 7:
              bit-identical to the model fed the same calls
  idle        FDBK 0: after the input stops, every FBMD falls to exact digital silence
  isolation   eight instances, four per core, own knobs and input, under -guard 0x4000
              -guard-shared -dirty 0x5a: no stray write or clobber, each identical alone
  garbage     from an instance block pre-filled with garbage (verify_dirty_state.py's fills),
              a render is identical to one from a zeroed block (init zeroes $00..$5f, the clear
              zeroes the Y slot before the first wet sample)
  demand      with a loaded window effect's entry written into the dump (BOUND and its span at
              x:$33da3, as DLCOPY publishes it; verify_dlwrap's method): the instance whose slot
              covers the span passes the input through sample for sample and writes nothing to Y;
              a span one word past either end of the slot's +$0000..$3DA2, and every other slot,
              render bit-identically to the dump without it; the entry is tried as effect 0 and 3.
              On an FX1 base (dsp_host -alloc 0, Y:0x1000) the instance is dry and writes nothing.
              dsp_host keeps P and Y apart, so this proves the decision, not that the chip's code
              would have been overwritten. Not covered: the stub's path (verify_dlstub) and an
              instance going from dry back to wet when a span is withdrawn mid-render (dsp_host
              cannot change the dump between blocks; DEMAND_LOAD.md "Open").
"""
import array
import contextlib
import importlib
import io
import math
import os
import pathlib
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'modules/atomizer'
STOCK = ROOT / 'out/raw/section_3_MAIN_OS.bin'
HOST = ROOT / 'vendor/dsp56300/build/source/dsp_host/dsp_host'
for need, how in ((STOCK, 'your own OS 1.40C MAIN OS: make os, then make recon'),
                  (HOST, 'the patched DSP56300 tools: make setup')):
    if not need.is_file():
        sys.exit(f'[FAIL] atomizer: missing {need} ({how})')
sys.path[:0] = [str(ROOT / 'tools/build'), str(ROOT / 'tools/harness'), str(ROOT / 'tools/verify'), str(ROOT / 'tools'),
                str(FOLDER)]
os.environ.update(XBUS='1', SPEC='1', DEV='0', NOROUNDTRIP='0', OCTABAM_NO_CACHE='1')
os.environ.setdefault('BUILD', '79')
import toolpath  # noqa: E402,F401
import dsp_modmap  # noqa: E402
from remix import registry, stock  # noqa: E402
from remix.schema import Remix  # noqa: E402
import atomizer_ref  # noqa: E402

dsp_modmap.IMG = STOCK
KNOWN = registry.modules()
MOD = KNOWN['ATOMIZER']
NAMES = [p.name.decode() if p.name else '' for p in MOD.params]
if os.environ.get('ATOMIZER_NOLABELS') == '1':
    # Development without the m68k-elf toolchain: the MODE / FBMD / SYNC labels and the per-MODE
    # knob names are ColdFire caves (GNU as); the DSP code, the knobs' values and every gate below
    # are the same without them. A shipping check never sets this.
    import dataclasses
    from remix.schema import Formatter
    MOD = dataclasses.replace(MOD, mode_views=(), mode_slot=None,
                              params=tuple(dataclasses.replace(p, labels=None, formatter=Formatter.PLAIN)
                                           if p.labels else p for p in MOD.params))
    KNOWN['ATOMIZER'] = MOD
    registry.modules = lambda *a, **k: KNOWN
DONORS = ('DELAY', 'SPRING REV', 'PLATE REV', 'DARK REV')
FR, SR = 16, 44100
FS = 8388607
CLEAR = 62                                  # calls: the slot clears 256 words a call
TEMPO = 130                                 # dsp_host -tempo: tempo24 = 130 x 24


def remix_for(donors):
    ids = {m.menu.fx2_id: m.key for m in KNOWN.values() if m.is_stock and m.menu is not None}
    fx1 = [ids[i] for i in stock.fx1_order() if i]
    fx2 = [ids[i] for i in stock._chooser_order(stock.FX2_CHOOSER) if i]
    return Remix(name='atomizer-verify', doc='Private gate image; never flashed.',
                 modules=tuple(k for k in fx2 if k not in donors) + ('ATOMIZER',),
                 fx1=tuple(fx1), fallback='NONE')


def build_image(work, donors=DONORS):
    """The native build in a scratch tree, the composition exporter's way. Returns (image, log)."""
    remix = remix_for(donors)
    registry.remix = lambda _: remix
    tree = work / 'tree'
    tree.mkdir()
    for name in ('modules', 'platform', 'dsp', 'vendor'):
        os.symlink(ROOT / name, tree / name, target_is_directory=True)
    (tree / 'out').mkdir()
    cwd = os.getcwd()
    os.chdir(tree)
    log = io.StringIO()
    try:
        sys.modules.pop('build_bus', None)
        build = importlib.import_module('build_bus')
        build.IMG = STOCK
        build.OUT = work / 'atomizer.bin'
        with contextlib.redirect_stdout(log):
            build.main()
    finally:
        if 'build' in locals() and getattr(build, '_SCRATCH', None) is not None:
            shutil.rmtree(build._SCRATCH, ignore_errors=True)
        os.chdir(cwd)
    return work / 'atomizer.bin', log.getvalue()


class Gates:
    def __init__(self):
        self.failed = []

    def check(self, name, ok, detail=''):
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}{': ' + detail if detail else ''}", flush=True)
        if not ok:
            self.failed.append(name)


def knobs(**kw):
    vals = [p.default or 0 for p in MOD.params] + [0] * (12 - len(MOD.params))
    for k, v in kw.items():
        vals[NAMES.index(k)] = v
    return vals


def write_raw(path, frames):
    """frames: list of (L, R) floats -> interleaved int32 (dsp_host -stereo)"""
    a = array.array('i', [0] * (2 * len(frames)))
    for i, (l, r) in enumerate(frames):
        a[2 * i] = max(-FS - 1, min(FS, int(round(l * FS))))
        a[2 * i + 1] = max(-FS - 1, min(FS, int(round(r * FS))))
    path.write_bytes(a.tobytes())
    return path


def read_raw(path):
    a = array.array('i')
    a.frombytes(path.read_bytes())
    return a


def words(path):
    """The input as the model sees it: (L, R) 24-bit words."""
    a = read_raw(path)
    return [(a[i] & 0xFFFFFF, a[i + 1] & 0xFFFFFF) for i in range(0, len(a), 2)]


class Host:
    """dsp_host on the image's two payloads; AtoMizer on FX2 at positions 0..3 of each core."""

    def __init__(self, mems, work):
        import send_probe
        self.mems, self.work, self.n = mems, work, 0
        fxid = registry.bound(remix_for(DONORS))['ATOMIZER'].menu.fx2_id   # the remix's id (trap-module-id)
        self.ep = {c: send_probe.entry_points(mems[c], fxid) for c in (0, 1)}

    def run(self, insts, blocks, inputs, extra=(), mems=None):
        """insts: dicts with core, pos, and knobs or paramfile; inputs: one raw per instance.
        Returns (stdout, [interleaved int32 output per instance])."""
        mems = mems or self.mems
        self.n += 1
        out = self.work / f'r{self.n}.raw'
        cmd = [str(HOST), '-mem', str(mems[0]), '-memB', str(mems[1]),
               '-init', ','.join('%x' % self.ep[i['core']][0] for i in insts),
               '-proc', ','.join('%x' % self.ep[i['core']][1] for i in insts),
               '-inst', str(len(insts)), '-core', ','.join(str(i['core']) for i in insts),
               '-alloc', ','.join(str(i.get('alloc', 1 + 2 * i['pos'])) for i in insts),
               '-r7', ','.join(str(2 + 3 * i['pos']) for i in insts),
               '-audioidx', ','.join(str(k) for k in range(len(insts))), '-audio', '9000',
               '-in', ','.join(str(p) for p in inputs), '-stereo',
               '-frames', str(FR), '-blocks', str(blocks), '-out', str(out), '-tempo', str(TEMPO)]
        for i in insts:
            cmd += ['-params', ','.join(map(str, i.get('knobs', knobs())))]
        for i in insts:
            if 'paramfile' in i:
                cmd += ['-paramfile', str(i['paramfile'])]
        cmd += list(extra)
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode or 'HANG' in r.stdout:
            raise RuntimeError(f'dsp_host failed ({r.returncode}):\n{r.stdout[-3000:]}{r.stderr[-1000:]}')
        outs = [read_raw(out if k == 0 else pathlib.Path(f'{out}.i{k}')) for k in range(len(insts))]
        for p in [out] + [pathlib.Path(f'{out}.i{k}') for k in range(1, len(insts))]:
            p.unlink(missing_ok=True)
        return r.stdout, outs


def dbfs(v):
    return 20 * math.log10(max(abs(v), 1) / (FS + 1))


def signal(seconds, seed=1, stop=None):
    """A bass-like line: decaying saws on a 130 BPM 16th grid, a little noise, then silence from `stop` s."""
    rnd = random.Random(seed)
    n = int(seconds * SR) // FR * FR
    step = int(SR * 60 / TEMPO / 4)
    notes = (55, 55, 110, 82.4, 55, 65.4, 110, 73.4)
    x, ph = [], 0.0
    for i in range(n):
        if stop is not None and i >= stop * SR:
            x.append((0.0, 0.0))
            continue
        k, t = divmod(i, step)
        f = notes[k % len(notes)] * (2 if k % 5 == 3 else 1)
        ph = (ph + f / SR) % 1.0
        v = (2 * ph - 1) * 0.5 * math.exp(-t / (0.08 * SR)) + 0.01 * (rnd.random() * 2 - 1)
        x.append((v, v * 0.9))
    return x


def noise(n, level, seed):
    rnd = random.Random(seed)
    return [((rnd.random() * 2 - 1) * level, (rnd.random() * 2 - 1) * level) for _ in range(n)]


def reference(frames, calls, split=0):
    """atomizer_ref through the same calls; a split s > 0 cuts every block at s."""
    fx, out = atomizer_ref.AtoMizer(), []
    for b, k in enumerate(calls):
        block = frames[FR * b:FR * b + FR]
        for part in ((block[:split], block[split:]) if split else (block,)):
            if part:
                out += fx.call(k, part, TEMPO * 24)
    return array.array('i', [atomizer_ref.sx(v) for frame in out for v in frame])


def differ(a, b):
    n = sum(1 for p, q in zip(a, b) if p != q) + abs(len(a) - len(b))
    first = next((i for i, (p, q) in enumerate(zip(a, b)) if p != q), None)
    return n, ('' if first is None else f', first at frame {first // 2}')


def gate_source(g):
    try:
        import verify_init_regs as verify_initregs
    except ImportError:                     # the older trees' name
        import verify_initregs
    src = (FOLDER / 'atomizer.asm').read_text()
    block = verify_initregs.init_block(src)
    g.check('source: init leaves r1/n1/m1 alone', bool(block) and not verify_initregs.WRITE.search(block))
    registry.remix = lambda _: Remix(name='atomizer-verify', doc='cycle count', modules=('ATOMIZER',), fallback='NONE')
    import cycle_count
    row = cycle_count.measure('atomizer')
    same = cycle_count.verify('atomizer', row)
    per = row['cycles']
    g.check('source: static cycles', same and 4 * per <= cycle_count.USABLE,
            f'{per} cycles/sample per instance (a grain start priced every sample, the worst feedback mode), '
            f'4 per core = {4 * per} of {cycle_count.USABLE}; marker no-op {same}')


def gate_placement(g, log):
    for tag in 'AB':
        sec = log.split(f'-- payload {tag} --')[1].split('-- payload')[0] if f'-- payload {tag} --' in log else ''
        m = re.search(r'ATOMIZER\s+P:0x([0-9a-f]+)\.\.0x([0-9a-f]+) \(\s*(\d+) words\)', sec)
        runs = [(int(a, 16), int(b, 16)) for a, b in re.findall(r'(?:run \d+ |region )P:0x([0-9a-f]+)\.\.0x([0-9a-f]+)', sec)]
        if not (m and runs):
            g.check(f'placement: payload {tag}', False, 'no ATOMIZER or run line in the build log')
            continue
        lo, hi = int(m[1], 16), int(m[2], 16)
        global CODE_WORDS
        CODE_WORDS = int(m[3])
        ok = any(a <= lo and hi <= b for a, b in runs)
        g.check(f'placement: payload {tag}', ok, f'ATOMIZER P:0x{lo:05x}..0x{hi:05x} ({m[3]} words) inside a harvested run')


def automation(blocks, seed, mix=None, every=29):
    rnd = random.Random(seed)
    calls, cur = [], knobs()
    for b in range(blocks):
        if b % every == 0:
            cur = [rnd.randrange(p.count or 128) for p in MOD.params] + [0] * (12 - len(MOD.params))
            if mix is not None:
                cur[NAMES.index('MIX')] = mix
        calls.append(list(cur))
    return calls


def paramfile(path, calls):
    rows, last = [], None
    for b, k in enumerate(calls):
        if k != last:
            rows.append(','.join(map(str, [b, *k])))
            last = k
    path.write_text('\n'.join(rows) + '\n')
    return path


def gate_dry(g, host, work):
    blocks = 900
    inp = write_raw(work / 'dry_in.raw', noise(blocks * FR, 0.9, 7))
    want = read_raw(inp)
    calls = automation(blocks, 3, mix=0, every=37)
    pf = paramfile(work / 'dry_auto.csv', calls)
    for label, extra, moving in (('static', (), False), ('moving knobs', (), True), ('moving knobs, split 5', ('-split', '5'), True)):
        inst = dict(core=0, pos=1, knobs=knobs(MIX=0, FDBK=127, FBMD=4, MODE=5))
        if moving:
            inst['paramfile'] = pf
        _, (out,) = host.run([inst], blocks, [inp], extra)
        n, at = differ(out, want)
        g.check(f'dry: MIX 0 is the input sample for sample ({label})', n == 0, f'{n} of {len(want)} words differ{at}')


CASES = ([(f'MODE {m} {atomizer_ref_name}', dict(MODE=m, CHOP=60, TIME=70, PARA=90, FDBK=40, MIX=100, TONE=100, FBMD=1, SPRD=60))
          for m, atomizer_ref_name in enumerate(('DDEN', 'DLFO', 'DREV', 'DPCH', 'DRND', 'PDTN', 'PLFO', 'PDEN'))]
         + [(f'FBMD {f} {n}', dict(FBMD=f, MODE=0 if f != 1 else 2, CHOP=60, TIME=40, PARA=64, FDBK=80, MIX=100, TONE=80, SPRD=40))
            for f, n in enumerate(('AUTO', 'RCYC', 'POST', 'PING', 'REP', 'R1/2', 'R1/4', 'RPCT'))]
         + [('PDTN, PARA 0', dict(MODE=5, CHOP=80, TIME=100, PARA=0, FDBK=30, MIX=127, FBMD=1)),
            ('DPCH, PARA 127', dict(MODE=3, CHOP=50, TIME=20, PARA=127, FDBK=30, MIX=127, FBMD=1)),
            ('DREV, SYNC', dict(MODE=2, CHOP=70, TIME=70, FDBK=40, MIX=127, FBMD=1, SPRD=30, SYNC=1)),
            ('R1/2, SYNC', dict(MODE=1, CHOP=50, TIME=40, FDBK=60, MIX=127, FBMD=5, SPRD=40, SYNC=1)),
            ('RPCT, PDTN', dict(MODE=5, CHOP=70, TIME=100, PARA=30, FDBK=90, MIX=127, FBMD=7, SPRD=40)),
            ('PING, DLFO', dict(MODE=1, CHOP=40, TIME=90, PARA=100, FDBK=100, MIX=90, TONE=50, FBMD=3, SPRD=80)),
            ('FREZ 127', dict(MODE=2, CHOP=60, TIME=50, FDBK=60, FREZ=127, MIX=127, FBMD=1, SPRD=40)),
            ('FREZ 60, SYNC', dict(MODE=0, CHOP=60, TIME=50, FDBK=60, FREZ=60, MIX=127, FBMD=1, SPRD=40, SYNC=1)),
            ('R1/4, PDEN', dict(MODE=7, CHOP=40, TIME=30, PARA=20, FDBK=127, MIX=127, FBMD=6)),
            ('MIX 32, TONE 0', dict(MODE=0, CHOP=90, TIME=100, FDBK=50, MIX=32, TONE=0, FBMD=1))])
CORE1 = ('MODE 5 PDTN', 'FBMD 3 PING', 'FBMD 4 REP', 'FREZ 60, SYNC')


def gate_reference(g, host, work):
    sig = signal(1.6)
    blocks = len(sig) // FR
    inp = write_raw(work / 'ref_in.raw', sig)
    frames = words(inp)
    for core in (0, 1):
        for label, kw in CASES:
            if core == 1 and label not in CORE1:
                continue
            k = knobs(**kw)
            _, (out,) = host.run([dict(core=core, pos=core, knobs=k)], blocks, [inp])
            ref = reference(frames, [k] * blocks)
            n, at = differ(out, ref)
            peak = max(abs(v) for v in out)
            g.check(f'reference: core {core}, {label}', n == 0, f'{n} of {len(ref)} words differ{at}; peak {dbfs(peak):.1f} dBFS')


def gate_automation(g, host, work):
    sig = signal(2.4)
    blocks = len(sig) // FR
    inp = write_raw(work / 'auto_in.raw', sig)
    frames = words(inp)
    calls = automation(blocks, 11, every=23)
    pf = paramfile(work / 'auto.csv', calls)
    for split in (0, 7):
        extra = ('-split', str(split)) if split else ()
        _, (out,) = host.run([dict(core=0, pos=0, knobs=calls[0], paramfile=pf)], blocks, [inp], extra)
        n, at = differ(out, reference(frames, calls, split))
        g.check(f'automation: every knob moving every 23 blocks{", split %d" % split if split else ""}', n == 0,
                f'{n} words differ{at}; {sum(1 for a, b in zip(calls, calls[1:]) if a[8] & 7 != b[8] & 7)} FBMD changes')


def gate_idle(g, host, work):
    sig = signal(1.6, stop=0.6)
    blocks = len(sig) // FR
    inp = write_raw(work / 'idle_in.raw', sig)
    quiet = int(0.6 * SR) + 15779 + 2 * 8128 + 4096        # the ring, two grains and the post line pass
    for f in range(8):
        k = knobs(FBMD=f, FDBK=0, MIX=127, CHOP=127, TIME=127, MODE=0)
        _, (out,) = host.run([dict(core=0, pos=0, knobs=k)], blocks, [inp])
        tail = out[2 * quiet:]
        g.check(f'idle: FBMD {f}, FDBK 0: digital silence after the input stops', len(tail) > 0 and not any(tail),
                f'{sum(1 for v in tail if v)} non-zero words in the last {len(tail) // 2} frames')


def instance_set():
    rnd = random.Random(5)
    return [dict(core=c, pos=p, knobs=knobs(MODE=rnd.randrange(8), FBMD=rnd.randrange(8), CHOP=rnd.randrange(128),
                                            TIME=rnd.randrange(128), PARA=rnd.randrange(128), FDBK=rnd.randrange(128),
                                            MIX=127, SPRD=rnd.randrange(128)))
            for c in (0, 1) for p in range(4)]


def gate_isolation(g, host, work):
    blocks = 700
    insts = instance_set()
    inputs = [write_raw(work / f'iso_{k}.raw', noise(blocks * FR, 0.4, 100 + k)) for k in range(len(insts))]
    extra = ('-guard', '0x4000', '-guard-shared', '-dirty', '0x5a')
    text, outs = host.run(insts, blocks, inputs, extra)
    rows = re.findall(r'instance (\d+): \d+ non-zero output samples, (\d+) stray write regions, (\d+) CLOBBERING', text)
    strays, clob = sum(int(s) for _, s, _ in rows), sum(int(c) for _, _, c in rows)
    g.check('isolation: eight instances under -guard 0x4000 -guard-shared -dirty 0x5a', len(rows) == 8 and strays == 0 and clob == 0,
            f'{len(rows)} instances guarded, {strays} stray regions, {clob} clobbers')
    same = 0
    for k, inst in enumerate(insts):
        _, (alone,) = host.run([inst], blocks, [inputs[k]], extra)
        same += alone == outs[k]
    g.check('isolation: each instance alone renders bit-identically', same == 8, f'{same} of 8 identical')


FILLS = (0x7fffff, 0x800000, 0x400000, 0x5a5a5a)    # verify_dirty_state.py's


def mem_with_fill(base, fill, out, r7=2):
    """verify_dirty_state.py's: a .mem dump whose instance block X:0x6000 + 0x100 r7 is all `fill`
    (r7 slot 2: position 0, where gate_garbage runs)."""
    import struct
    blob = base.read_bytes()
    body, term = blob[:-9], blob[-9:]
    assert term[0] == 0xff, 'not a .mem dump'
    run = struct.pack('<BII', 1, 0x6000 + 0x100 * r7, 0x100) + struct.pack('<I', fill) * 0x100
    out.write_bytes(body + run + term)
    return out


def gate_garbage(g, host, work):
    blocks = 400
    sig = write_raw(work / 'g_in.raw', signal(blocks * FR / SR))
    sets = [knobs(MIX=127, FDBK=90, FBMD=1), knobs(MIX=127, FDBK=90, FBMD=4, MODE=5, SYNC=1, FREZ=40)]
    clean = {k: host.run([dict(core=0, pos=0, knobs=kn)], blocks, [sig])[1][0] for k, kn in enumerate(sets)}
    same = 0
    for fill in FILLS:
        mems = {c: mem_with_fill(host.mems[c], fill, work / f'fill_{fill:06x}_{c}.mem') for c in (0, 1)}
        for k, kn in enumerate(sets):
            _, (o,) = host.run([dict(core=0, pos=0, knobs=kn)], blocks, [sig], ('-dirty', '0x5a'), mems=mems)
            same += o == clean[k]
    g.check('garbage: a garbage instance block (and dirty Y) renders exactly as a zeroed one', same == len(FILLS) * len(sets),
            f'{same} of {len(FILLS) * len(sets)} renders identical')


CODE_WORDS = 1516                           # the build's figure, set by gate_placement from the log
MAGIC = 0xB0A5ED                            # DLCOPY's BOUND word (modules/dlcopy/dlcopy.asm)
EXTENT = 0x3DA3                             # AtoMizer writes its slot's +$0000..$3DA2


def published(mem, name, lo, hi, k=0):
    """A copy of the dump with effect k's entry as DLCOPY publishes it: BOUND, the span [lo, hi)."""
    blob = pathlib.Path(mem).read_bytes()
    end = blob.rindex(b'\xff')
    e = 0x33DA3 + 8 * k
    rec = b''.join(struct.pack('<BII', 1, a, 1) + struct.pack('<I', w)
                   for a, w in ((e + 3, lo), (e + 4, hi), (e, MAGIC)))
    path = pathlib.Path(mem).with_name(f'{name}.mem')
    path.write_bytes(blob[:end] + rec + blob[end:])
    return path


def gate_demand(g, host, work):
    blocks = 600
    inp = write_raw(work / 'dm_in.raw', signal(blocks * FR / SR, seed=5))
    want = read_raw(inp)
    kn = knobs(MODE=0, CHOP=60, TIME=70, FDBK=100, MIX=127, FBMD=1, SPRD=60)
    bases = {0: (0x4000, 0x8000, 0x30000, 0x34000), 1: (0x4000, 0x8000, 0x38000, 0x3C000)}

    def render(core, pos, mems, tag, alloc=None):
        ydump = work / f'dm_{tag}.y'
        inst = dict(core=core, pos=pos, knobs=kn)
        if alloc is not None:
            inst['alloc'] = alloc
        _, (o,) = host.run([inst], blocks, [inp],
                           ('-dumpy', f'4000,40000,{ydump}', '-dumpcore', str(core)), mems=mems)
        y = array.array('I')
        y.frombytes(ydump.read_bytes())
        ydump.unlink()
        return o, y

    def wrote(y, base):
        return sum(1 for a in range(base, base + EXTENT) if y[a - 0x4000])

    for c in (0, 1):                        # an FX1 base: AtoMizer is FX2 only (atomizer.asm, the header)
        o, y = render(c, 0, None, f'fx1{c}', alloc=0)
        n, at = differ(o, want)
        g.check(f'demand: core {c}, an FX1 slot (Y:0x01000): the input passes through', n == 0,
                f'{n} of {len(want)} words differ{at}')
        g.check(f'demand: core {c}, an FX1 slot: nothing written to Y', not any(y[:0x3E00]),
                f'{sum(1 for v in y[:0x3E00] if v)} words written at Y:0x4000..')
    clean = {(c, p): render(c, p, None, f'c{c}{p}') for c in (0, 1) for p in range(4)}
    for c, p in clean:
        g.check(f'demand: core {c} slot Y:0x{bases[c][p]:05x}, nothing loaded: the instance wrote its slot',
                wrote(clean[c, p][1], bases[c][p]) > 0)
    # AtoMizer's own block in remixes/test/atomizer: P:0x35000, +$1000 of T8's FX2 slot (core A, 0x34000)
    code = (0x35000, 0x35000 + CODE_WORDS)
    for label, (lo, hi), hit, k in (('its own code at +$1000 of the T8 slot', code, (0, 3), 0),
                                    ('its own code, published as effect 3', code, (0, 3), 3),
                                    ('a span ending one word past the slot\'s base', (0x33F00, 0x34001), (0, 3), 0),
                                    ('a span on the slot\'s last word, +$3DA2', (0x34000 + EXTENT - 1, 0x34000 + EXTENT), (0, 3), 0),
                                    ('a span from +$3DA3 (the loader\'s gap)', (0x34000 + EXTENT, 0x34000 + EXTENT + 32), None, 0),
                                    ('a span ending at the slot\'s base', (0x33F00, 0x34000), None, 0),
                                    ('a span at +$1000 of core B\'s T4 slot', (0x3D000, 0x3D000 + CODE_WORDS), (1, 3), 0)):
        mems = {c: published(host.mems[c], f'dm{c}_{lo:x}_{k}', lo, hi, k) for c in (0, 1)}
        for (c, p), (o0, y0) in clean.items():
            o, y = render(c, p, mems, f'p{c}{p}')
            if (c, p) == hit:
                n, at = differ(o, want)
                g.check(f'demand: {label}: the covered slot passes the input through', n == 0,
                        f'{n} of {len(want)} words differ{at}')
                g.check(f'demand: {label}: the covered slot writes nothing to Y', wrote(y, bases[c][p]) == 0,
                        f'{wrote(y, bases[c][p])} words written')
            else:
                n, at = differ(o, o0)
                g.check(f'demand: {label}: core {c} slot Y:0x{bases[c][p]:05x} renders as without it',
                        n == 0 and y == y0, f'{n} words differ{at}, Y {"same" if y == y0 else "differs"}')


def main():
    import send_probe
    g = Gates()
    print('== atomizer: render gates (dsp_host, private image; not hardware)')
    gate_source(g)
    with tempfile.TemporaryDirectory(prefix='atomizer-verify.') as tmp:
        work = pathlib.Path(tmp)
        try:
            image, log = build_image(work)
        except (SystemExit, AssertionError) as error:
            g.check('placement: the image builds', False, str(error))
            return 1
        mems = {c: send_probe.dump_mem(image, work / f'mem_{t}.mem', t) for c, t in ((0, 'A'), (1, 'B'))}
        gate_placement(g, log)
        host = Host(mems, work)
        only = sys.argv[1:]
        for gate in (gate_dry, gate_reference, gate_automation, gate_idle, gate_isolation, gate_garbage,
                     gate_demand):
            if not only or gate.__name__[5:] in only:
                gate(g, host, work)
    print(f"== atomizer: {'all gates pass' if not g.failed else str(len(g.failed)) + ' failed: ' + ', '.join(g.failed)}")
    return 1 if g.failed else 0


if __name__ == '__main__':
    sys.exit(main())
