#!/usr/bin/env python3
"""Write modules/distorx/distorx.asm from distorx.tmpl.asm.

dsp_asm has no `equ` and no expressions, so every constant is a literal in
the source. They are COMPUTED in manifest.py from the pedals' part values;
this script puts them into the template so the two can never disagree.
`--check` exits non-zero when distorx.asm is not what the template and the
manifest make (verify_distorx runs it).

    python3 modules/distorx/generate_asm.py [--check]
"""
import importlib.util
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import toolpath  # noqa: E402,F401  (remix.schema for the manifest)


def manifest():
    spec = importlib.util.spec_from_file_location("distorx_manifest", HERE / "manifest.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def render():
    m = manifest()
    vals = dict(m.CONSTQ)
    vals["NRAIL"] = (-((m.CONSTQ["RAIL"] ^ 0x800000) - 0x800000)) & 0xFFFFFF
    src = (HERE / "distorx.tmpl.asm").read_text()

    def sub(mt):
        k = mt.group(1)
        if k not in vals:
            sys.exit(f"distorx.tmpl.asm: no constant {k} in the manifest")
        return f"${vals[k]:06x}"
    out = re.sub(r"@([A-Z0-9_]+)@", sub, src)
    out = out.replace("; GENERATED from distorx.tmpl.asm",
                      "; GENERATED (do not edit) from distorx.tmpl.asm", 1)
    return out


def main():
    out = render()
    dst = HERE / "distorx.asm"
    if "--check" in sys.argv:
        if not dst.exists() or dst.read_text() != out:
            sys.exit("modules/distorx/distorx.asm is stale: run "
                     "python3 modules/distorx/generate_asm.py")
        print("distorx.asm matches the template and the manifest")
        return
    dst.write_text(out)
    print(f"wrote {dst.relative_to(ROOT)} ({out.count(chr(10))} lines)")


if __name__ == "__main__":
    main()
