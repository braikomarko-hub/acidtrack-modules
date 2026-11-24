#!/usr/bin/env python3
"""STOP reaches AtoMizer (modules/atomizer/stop.s) under the port.

    python3 tools/verify/verify_atomizer_stop.py [REMIX] [--project DIR]     (default acidtrack)

Builds the remix, stages the project and, on its own boot each, puts AtoMizer on T2's FX2 (the live and
the Part id), opens T2's FX2 page and turns FREZ (E) and MIX (F) up with the encoders, then sets the
transport word (0x800065b8: 1 running, 2 stopped by STOP) and the stop kill's mask (0x8000184b, bit 1 =
T2) and reads both DSP records of T2 and T1 (0x80000110 + ping * 0x200 + 64 * track) at the end:

  running    FREZ (+32) and MIX (+34) are the knobs' values
  stopped    FREZ reads 0, MIX the knob's
  killed     stopped and T2 in the kill mask: FREZ and MIX read 0
  back       killed, then running again with the mask clear: both are the knobs' values again
  other      in every scenario T1's FX2 record (not AtoMizer) is the same as when running

Cannot see: the unit's own STOP keys (the words are poked), the DSP's response (verify_atomizer: FREZ 0
releases, MIX 0 rests).
"""
import argparse, json, os, pathlib, shutil, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1])); import toolpath  # noqa: E402,F401

ROOT = pathlib.Path(__file__).resolve().parents[2]
EMU = ROOT / "out/emu/ot_emu"
OUT = ROOT / "out/atomizer_stop"
FX2_LIVE, FX2_PART = 0x80000ECC, 0x402A75E8
REC = 0x80000110
FAILS = []


def check(what, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {what}" + (f"  {detail}" if detail else ""), flush=True)
    if not ok:
        FAILS.append(what)


def transport(v):
    return ";".join(f"{0x800065b8 + i:#x}={b:#x}" for i, b in enumerate(v.to_bytes(4, "big")))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("remix", nargs="?", default="atomizer")   # acidtrack carries no AtoMizer since ACIDV91
    ap.add_argument("--project", default=os.environ.get("OT_PROJECT", ""))
    a = ap.parse_args()
    project = a.project
    if not project and pathlib.Path("~/.octabam_project").expanduser().is_file():
        project = pathlib.Path("~/.octabam_project").expanduser().read_text().strip()
    if not project:
        print("  [SKIP] verify_atomizer_stop: no project (OT_PROJECT=<dir>, --project or ~/.octabam_project)"); return 0
    if not EMU.is_file():
        print("  [SKIP] verify_atomizer_stop: no port binary (make emu-cf)"); return 0
    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, REMIX=a.remix, XBUS="1", SPEC="1")
    env.setdefault("BUILD", "0")
    r = subprocess.run([sys.executable, str(ROOT / "tools/build/build_bus.py")], env=env, capture_output=True,
                       text=True, cwd=ROOT)
    if r.returncode:
        sys.exit(f"verify_atomizer_stop: building {a.remix} failed:\n{(r.stdout + r.stderr)[-1500:]}")
    image = OUT / "mainos.bin"
    shutil.copy2(ROOT / "out/mainos_bus.bin", image)
    from remix import registry
    atm = registry.bound(registry.remix(a.remix))["ATOMIZER"].menu.fx2_id

    copy = OUT / "project"
    shutil.rmtree(copy, ignore_errors=True)
    copy.mkdir(parents=True)
    for f in pathlib.Path(project).expanduser().iterdir():
        if f.is_file() and f.suffix.lower() == ".work":
            shutil.copy2(f, copy / f.name)

    first = f"{FX2_LIVE + 1:#x}={atm:#x};{FX2_PART + 1:#x}={atm:#x}"
    panel = ["300 key 0x11 down", "340 key 0x11 up", "700 key 0x26 down", "740 key 0x26 up",
             "1200 enc 4 40", "1500 enc 5 50", "1800 enc 4 40", "2100 enc 5 50"]
    kill_on, kill_off = "0x8000184b=0x2", "0x8000184b=0x0"
    scen = {
        "running": [f"2600 poke {transport(1)};{kill_off}"],
        "stopped": [f"2600 poke {transport(2)};{kill_off}"],
        "killed": [f"2600 poke {transport(0)};{kill_on}"],
        "back": [f"2600 poke {transport(0)};{kill_on}", f"3400 poke {transport(1)};{kill_off}"],
    }
    procs = {}
    for tag, later in scen.items():
        card = OUT / f"{tag}.img"
        r = subprocess.run([sys.executable, str(ROOT / "tools/emu/ot_emu/stage_card.py"), str(copy), "BRAINSET",
                            "BRAINPRJ", "--tree", str(OUT / f"tree_{tag}"), "--out", str(card)], cwd=ROOT,
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"verify_atomizer_stop: stage_card failed:\n{r.stdout[-800:]}{r.stderr[-800:]}")
        (OUT / f"{tag}.script").write_text("\n".join(panel + later + ["4200 quit"]) + "\n")
        cmd = [EMU, "--image", image, "--card", card, "--set", "BRAINSET", "--project", "BRAINPRJ",
               "--load-ms", "90000", "--dsp", "--frame", "--live-script", OUT / f"{tag}.script",
               "--step", "-:poke:" + first, "--mem-dump", f"{REC:#x},1024={OUT / (tag + '_rec.bin')}"]
        fh = open(OUT / f"{tag}.txt", "w")
        procs[tag] = (subprocess.Popen(list(map(str, cmd)), cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT), fh)
    recs = {}
    for tag, (p, fh) in procs.items():
        rc = p.wait()
        fh.close()
        txt = (OUT / f"{tag}.txt").read_text(errors="replace")
        if rc or "ended on quit" not in txt:
            sys.exit(f"verify_atomizer_stop: the {tag} run did not finish -- {OUT / (tag + '.txt')}")
        recs[tag] = (OUT / f"{tag}_rec.bin").read_bytes()

    def w(tag, ping, track, off):
        b = recs[tag]; i = ping * 0x200 + 64 * track + off
        return int.from_bytes(b[i:i + 2], "big")

    def fx2(tag, ping, track):
        return recs[tag][ping * 0x200 + 64 * track + 24:][:12].hex(" ")

    print(f"== atomizer stop: {a.remix}, AtoMizer id {atm:#x} on T2's FX2")
    for ping in (0, 1):
        frez, mix = w("running", ping, 1, 32), w("running", ping, 1, 34)
        check(f"running (record {ping}): T2 is AtoMizer and the knobs turned up", w("running", ping, 1, 56) == atm
              and frez >> 8 and mix >> 8, f"id {w('running', ping, 1, 56):#x}, FREZ {frez:#06x}, MIX {mix:#06x}")
        check(f"stopped (record {ping}): FREZ reads 0, MIX the knob's",
              w("stopped", ping, 1, 32) == 0 and w("stopped", ping, 1, 34) == mix,
              f"FREZ {w('stopped', ping, 1, 32):#06x}, MIX {w('stopped', ping, 1, 34):#06x}")
        check(f"killed (record {ping}): FREZ and MIX read 0",
              w("killed", ping, 1, 32) == 0 and w("killed", ping, 1, 34) == 0,
              f"FREZ {w('killed', ping, 1, 32):#06x}, MIX {w('killed', ping, 1, 34):#06x}")
        check(f"back (record {ping}): running again, the knobs' values return",
              w("back", ping, 1, 32) == frez and w("back", ping, 1, 34) == mix,
              f"FREZ {w('back', ping, 1, 32):#06x}, MIX {w('back', ping, 1, 34):#06x}")
        for tag in ("stopped", "killed", "back"):
            check(f"other ({tag}, record {ping}): T1's FX2 slots as when running",
                  fx2(tag, ping, 0) == fx2("running", ping, 0), fx2(tag, ping, 0))
    print(f"== atomizer stop: {'all pass' if not FAILS else str(len(FAILS)) + ' failed'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
