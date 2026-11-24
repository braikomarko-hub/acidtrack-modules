#!/usr/bin/env python3
"""STROJ (modules/stroj) through the stock panel and the audio path under the ColdFire port.

Boots of the emulated unit on a fixture project (OT_PROJECT), with real key and encoder events:

1. list    T1 -> FUNC+SRC -> DOWNs to STROJ's row (5 alone, 6 beside OCTA303): the list (a screenshot).
2. select  ... -> YES, then SETUP's VOIC -1 and BRTH +10: T1 is FLEX signed 'S','J',1 in the Part
           and its shadow, with STROJ's defaults (PLAYBACK 64 40 64 40 50 90, SETUP 3 0 1 40 1 0)
           then the edits (VOIC 2, BRTH 50) in the Part, the shadow and the live lane; UI type 5's
           record is STROJ's (named STROJ, its PLAYBACK and SETUP names).  Screenshots of SETUP and,
           after SRC, of the PLAYBACK page.
3. unsign  the same selection, then another machine: the signature is cleared in both copies.
4. audio   T1 signed STROJ with a trig on step 1, the sequencer running: stroj_render's voice
           reaches the main out (not silent; its strongest partial near the note's), saved as a wav.
Beside OCTA303 (remix test/stroj-303, HOOKS machine_rows) the same, with OCTA-303 on row 5 and STROJ on
row 6 (the chain's last link).

Skips without OT_PROJECT (a stock project directory to copy; it is not modified).
Usage: OT_PROJECT=<dir> python3 tools/verify/verify_stroj_port.py [image]
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import wave

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/hw"), str(ROOT / "tools/harness"), str(ROOT / "tools/emu")]
import ot_project as otp  # noqa: E402
from ab_fixture import prepare  # noqa: E402

OUT = pathlib.Path(os.environ.get("SJ_OUT", ROOT / "out/stroj/port-gate")).resolve()
PART = 0x40170F60            # part 0's Part' (BANK + 0x8ed80); found again from the dumped BANK pointer
SHADOW = 0x100A4ECE
LANE = 0x80000810
PB_TABLE5 = 0x400D5F4C
DEFS_PB, DEFS_SU = [64, 40, 64, 40, 50, 90], [3, 0, 1, 40, 1, 0]


def key(code, gap=0.6, hold=0.4):
    return [(gap, f"key {code:#x} down"), (hold, f"key {code:#x} up")]


FUNC_SRC = [(0.6, "key 0x2d down"), (0.3, "key 0x22 down"), (0.3, "key 0x22 up"), (0.3, "key 0x2d up")]
TO_LIST = key(0x10) + FUNC_SRC
DOWN4 = [e for _ in range(4) for e in key(0x20, 0.35, 0.1)]   # held 0.1 s: a port key held 0.25 s can repeat (TRAPS.md)
SELECT = TO_LIST + DOWN4 + key(0x31)     # STROJ's row 5 (alone); main() makes it its row beside others


def symbols():
    nm = shutil.which("m68k-elf-nm") or "m68k-elf-nm"
    out = subprocess.check_output([nm, str(ROOT / "out/platform/runtime/runtime.elf")], text=True)
    return {l.split()[-1]: int(l.split()[0], 16) for l in out.splitlines() if len(l.split()) == 3}


def shot(d, name):
    png = OUT / f"{name}.png"
    subprocess.run([sys.executable, str(ROOT / "tools/emu/lcd_view.py"), str(d / "lcd.bin"), "--png", str(png)],
                   check=True, cwd=ROOT, capture_output=True)
    return png


def run(name, card, image, script, extra=()):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    spans = (f"{PART:#x},6322={d}/part.bin;{SHADOW:#x},6322={d}/shadow.bin;0x46c82456,4={d}/bank.bin;"
             f"{LANE:#x},600={d}/lane.bin;{PB_TABLE5:#x},4={d}/page.bin")
    cmd = [str(ROOT / "out/emu/ot_emu"), "--image", str(image), "--card", str(card),
           "--set", "OCTABAM", "--project", "RIG", "--load-ms", "20000", "--dsp", "--mem-dump", spans,
           "--lcd", str(d / "lcd.bin"), *extra]
    if script is not None:
        t, ev = 0, []
        for delay, e in script + [(1.0, "quit")]:
            t += round(delay * 1000)
            ev.append(f"{t} {e}\n")
        (d / "events.txt").write_text("".join(ev))
        cmd += ["--live-script", str(d / "events.txt")]
    with (d / "port.log").open("w") as log:
        log.write(" ".join(cmd) + "\n"); log.flush()
        subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=1800, check=True)
    log = (d / "port.log").read_text()
    assert "ILLEGAL" not in log, f"{name}: an illegal instruction ({d / 'port.log'})"
    rd = lambda f: (d / f).read_bytes() if (d / f).exists() else b""
    return rd, log, d


def stage(fixture, name):
    card = OUT / f"{name}.img"
    subprocess.run([sys.executable, str(ROOT / "tools/emu/ot_emu/stage_card.py"), str(fixture), "OCTABAM", "RIG",
                    "--tree", str(OUT / f"tree-{name}"), "--out", str(card)], check=True, cwd=ROOT,
                   capture_output=True)
    return card


def main():
    global PART
    src = os.environ.get("OT_PROJECT")
    if not src:
        print("[SKIP] STROJ port: set OT_PROJECT to a stock project fixture")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    fixture = prepare(src, OUT / "project")
    card = stage(fixture, "card")
    image = OUT / "image.bin"
    shutil.copy2(sys.argv[1] if len(sys.argv) > 1 else ROOT / "out/mainos_bus.bin", image)
    rows = image.read_bytes()[0x40079248 - 0x40000400 + 3]       # the machine list's row count
    beside = rows > 6
    # STROJ is the last link of HOOKS's machine chain: its row is the list's last (5 alone, 6 beside
    # OCTA303); the cursor starts on FLEX (row 1), so (row - 1) DOWNs reach it
    global SELECT, DOWN4, PB_TABLE5
    sj_row = rows - 1
    DOWN_SJ = [e for _ in range(sj_row - 1) for e in key(0x20, 0.35, 0.1)]
    SELECT = TO_LIST + DOWN_SJ + key(0x31)
    PB_TABLE5 = 0x400D5F38 + 4 * sj_row
    print(f"the list has {rows} rows: STROJ on row {sj_row}")
    sym = symbols()
    if "sj_desc" not in sym:                # the runtime in out/ is whatever built last (TRAPS.md)
        sys.exit("verify_stroj_port: out/platform/runtime is not a STROJ build: "
                 "make bus REMIX=test/stroj (or test/stroj-303) first, then pass its image")
    rec = sym["sj_desc"]
    shots = []

    # 1. the list
    _, log, d = run("list", card, image, TO_LIST + DOWN_SJ)
    assert "ended on quit" in log, "list: the script did not finish"
    shots.append(shot(d, "1_list_stroj"))
    if beside:
        _, log, d = run("list303", card, image, TO_LIST + DOWN4)          # OCTA-303 on row 5
        shots.append(shot(d, "1b_list_octa303"))

    # 2. select STROJ, edit SETUP (VOIC down, BRTH +10, WAVE up)
    script = SELECT + [(0.8, "enc 0 -6"), (0.5, "enc 3 10"), (0.6, "enc 5 8")]
    rd, log, d = run("select", card, image, script)
    assert "ended on quit" in log, "select: the script did not finish"
    bank = int.from_bytes(rd("bank.bin"), "big")
    if bank + 0x8ED80 != PART:
        PART = bank + 0x8ED80
        rd, log, d = run("select", card, image, script)
    shots.append(shot(d, "2_setup"))
    part, shadow, lane = rd("part.bin"), rd("shadow.bin"), rd("lane.bin")
    p = part
    print("SETUP after the edits:", list(p[0x1E0:0x1E6]))
    want_su = [p[0x1E0], 0, 1, 50, 1, p[0x1E5]]
    assert p[0x1E0] < 3 and p[0x1E5] > 0, ("VOIC / WAVE did not move", list(p[0x1E0:0x1E6]))
    for nm, p in (("part", part), ("shadow", shadow)):
        assert p[0x22] == 1, (nm, "machine byte", p[0x22])
        assert p[0x3C:0x3F] == b"SJ\x01", (nm, "signature", p[0x3C:0x3F])
        assert list(p[0x30:0x36]) == DEFS_PB, (nm, "PLAYBACK", list(p[0x30:0x36]))
        assert list(p[0x1E0:0x1E6]) == want_su, (nm, "SETUP", list(p[0x1E0:0x1E6]))
    assert list(lane[0:6]) == DEFS_PB and list(lane[0x20:0x26]) == want_su, \
        ("live lane", list(lane[0:6]), list(lane[0x20:0x26]))
    assert int.from_bytes(rd("page.bin"), "big") == rec, (f"UI type {sj_row}'s record", rd("page.bin").hex(), hex(rec))
    print(f"PASS select: FLEX signed S J 1, the defaults then VOIC {want_su[0]} / BRTH 50 / WAVE {want_su[5]} in the Part, its shadow and the "
          f"live lane; UI type {sj_row} = STROJ's record")
    rd, log, d = run("playback", card, image, SELECT + key(0x22))
    shots.append(shot(d, "3_playback"))

    # 3b. LFO SETUP on the STROJ track: PMTR reads "PB NOTE" (the machine's names, not FLEX's PTCH)
    tap = lambda c, gap=0.5: key(c, gap, 0.1)
    out_of_src = tap(0x32) + tap(0x32)                      # NO, NO: SRC SETUP closed, the main page
    rd, log, d = run("lfo", card, image, SELECT + out_of_src + tap(0x24) +
                     [(0.6, "key 0x2d down"), (0.2, "key 0x24 down"), (0.1, "key 0x24 up"), (0.3, "key 0x2d up")])
    shots.append(shot(d, "4_lfo_setup"))

    # 3c. CHROMATIC (FUNC + DOWN, DOWN) on the STROJ track: TRIG 16, TRIG 1, TRIG 13 (index 15, 0, 12) are
    #     NOTE raw 52 + index = D#2, C1, C2 (77.8, 32.7, 65.4 Hz); the stock 5 * index + 4 would make
    #     TRIG 16 D#3 (155.6 Hz).  The defaults: INTV 5TH, so each note's fifth sounds with it.
    chrom = (SELECT + out_of_src +
             [(0.6, "key 0x2d down"), (0.3, "key 0x20 down"), (0.1, "key 0x20 up"),
              (0.4, "key 0x20 down"), (0.1, "key 0x20 up"), (0.5, "key 0x2d up")] +
             [(1.0, "key 0xf down"), (2.5, "key 0xf up"), (1.5, "key 0x0 down"), (2.5, "key 0x0 up"),
              (1.0, "key 0xc down"), (2.5, "key 0xc up")])
    rd, log, d = run("chrom", card, image, chrom, ("--audio-out", str(OUT / "chrom")))
    shots.append(shot(d, "5_chromatic"))
    import numpy as np
    cw = sorted(OUT.glob("chrom*core*.wav"))
    assert cw, ("CHROMATIC: no audio written", log[-1500:])
    with wave.open(str(cw[0]), "rb") as f:
        ch, n = f.getnchannels(), f.getnframes()
        raw = np.frombuffer(f.readframes(n), dtype=np.uint8).reshape(n, ch, 3)
    x = raw[..., 0].astype(np.int32) | raw[..., 1].astype(np.int32) << 8 | raw[..., 2].astype(np.int32) << 16
    x = np.where(x & 0x800000, x - (1 << 24), x).astype(float)
    pk = np.abs(x).max(axis=0)
    y = x[:, int(np.argmax(pk))]
    assert pk.max() > 0, "CHROMATIC: the STROJ track is silent"
    tops = []                                   # each loud half second's three strongest low partials
    for i in range(0, len(y) - 22050, 22050):
        seg = y[i:i + 22050]
        if np.sqrt((seg ** 2).mean()) < pk.max() / 100:
            continue
        sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); fq = np.fft.rfftfreq(len(seg), 1 / 44100)
        m = (fq > 15) & (fq < 400)
        tops.append(fq[m][np.argsort(sp[m])[-3:]])
    found = lambda hz: any(any(abs(t - hz) < 2.5 for t in tt) for tt in tops)
    for name, hz in (("TRIG 16 = D#2", 77.78), ("TRIG 1 = C1", 32.70), ("TRIG 13 = C2", 65.41)):
        assert found(hz), (f"CHROMATIC: {name} ({hz} Hz) not heard", [list(np.round(t, 1)) for t in tops])
    assert not found(155.56) or found(77.78), "CHROMATIC: TRIG 16 played the stock mapping's D#3"
    print("PASS CHROMATIC: TRIG 16, 1, 13 play D#2, C1, C2 (NOTE in semitones)")

    # 3. select, then another machine
    rd, log, _ = run("unsign", card, image, SELECT + key(0x32, 0.6, 0.1) + FUNC_SRC +
                     [e for _ in range(4) for e in key(0x33, 0.35, 0.1)] + key(0x31))
    part, shadow = rd("part.bin"), rd("shadow.bin")
    assert part[0x3C:0x3F] == bytes(3) and shadow[0x3C:0x3F] == bytes(3), \
        ("signature not cleared", part[0x3C:0x3F], shadow[0x3C:0x3F])
    print("PASS unsign: choosing another machine clears the signature in both copies")

    # 4. audio: T1 signed STROJ (the MISTO preset), a trig on step 1 of every pattern, AMP held
    afix = prepare(src, OUT / "project-audio")
    pb, su = [64, 45, 104, 50, 85, 95], [3, 0, 1, 45, 2, 1]        # MISTO: C2, OCT, TRI ...
    for b in afix.glob("bank*.work"):
        def mutate(dat):
            for pi in range(8):
                base = otp.PART_BASE + pi * otp.PART_STRIDE + 9
                dat[base + 0x22] = 1
                dat[base + 60:base + 63] = b"SJ\x01"
                for k in range(6):
                    dat[base + 0x2A + 6 + k] = pb[k]
                    dat[base + 0x1DA + 6 + k] = su[k]
            for pattern in range(16):
                at = otp.trac_off(pattern, 0)
                dat[at:at + 8] = (1).to_bytes(8, "big")
        otp._bank_write(afix, int(b.stem[4:]), mutate, guard=False)
    acard = stage(afix, "audio")
    frames = int(os.environ.get("SJ_FRAMES", "8000"))
    base = OUT / "audio"
    rd, log, d = run("audio", acard, image, None,
                     ("--sequencer", "--internal-clock", "--bank", "0", "--frames", str(frames),
                      "--main-level", "64", "--audio-out", str(base)))
    wavs = sorted(OUT.glob("audio*core*.wav"))
    assert wavs, ("no audio written", log[-1500:])
    import numpy as np
    best = None
    for w in wavs:
        with wave.open(str(w), "rb") as f:
            ch, n = f.getnchannels(), f.getnframes()
            raw = np.frombuffer(f.readframes(n), dtype=np.uint8).reshape(n, ch, 3)
        x = raw[..., 0].astype(np.int32) | raw[..., 1].astype(np.int32) << 8 | raw[..., 2].astype(np.int32) << 16
        x = np.where(x & 0x800000, x - (1 << 24), x)          # 24-bit little-endian
        for c in range(ch):
            lvl = int(np.abs(x[:, c]).max())
            if best is None or lvl > best[0]:
                best = (lvl, w, c, x[:, c].astype(float))
    lvl, w, c, sig = best
    print(f"audio: loudest channel {c} of {w.name}, peak {lvl / 8388608:.3f} of full scale")
    assert lvl > 8388608 // 100, "the STROJ track is silent at the outputs"
    n = 1 << 15
    seg = sig[-n:] * np.hanning(n)
    spec = np.abs(np.fft.rfft(seg)); fq = np.fft.rfftfreq(n, 1 / 44100)
    # MISTO: NOTE C2 (65.4 Hz), INTV OCT (130.8), SUB1 /2 (32.7), SUB2 /3 (21.8).  The breath swells
    # the sub-octaves, so each partial is asked for within 40 dB of the strongest, not among the top few.
    top = spec.max()
    for want in (65.41, 130.81, 32.70, 21.80):
        band = spec[(fq > want - 2) & (fq < want + 2)]
        assert band.max() > top / 100, (f"no partial near {want} Hz", 20 * np.log10(band.max() / top))
    out = OUT / "stroj_T1_port.wav"
    y = (sig / lvl * 0.9 * 32767).astype("<i2")
    with wave.open(str(out), "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(44100); f.writeframes(y.tobytes())
    print(f"PASS audio: STROJ reaches the outputs, partials at C2, its octave and the /2 /3 sub-octaves ({out})")
    print("SHOTS", " ".join(str(s) for s in shots))


if __name__ == "__main__":
    main()
