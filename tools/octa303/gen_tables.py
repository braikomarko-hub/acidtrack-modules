#!/usr/bin/env python3
"""Write OCTA303's constants and lookup tables into modules/octa303/octa303.s.

    python3 tools/octa303/gen_tables.py          # rewrite the two GENERATED blocks
    python3 tools/octa303/gen_tables.py --check  # exit 1 if the .s is stale (used by the tests)

Values come from o3tables.py (the design) via ref303.py (the ladder tables); the assembly and
the golden model therefore read the very same numbers.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import o3tables as T, ref303 as R
SRC = os.path.normpath(os.path.join(HERE, '..', '..', 'modules', 'octa303', 'octa303.s'))

CONSTS = ['CS', 'SHIFT_OUT', 'P_CENTER', 'P_LO', 'P_HI', 'TUNE_LO', 'TUNE_HI', 'GATE_K', 'GATE_HOLD_INF', 'GATE_IDLE', 'GATE_TPS0', 'ONE30', 'S_MAX', 'DIST_GAIN', 'DIST_BIAS',
          'TB_MEG_ATT', 'TB_ACC_VCA', 'TB_DIS', 'TB_SWEEP_ST', 'TB_ACCVCA_GAIN',
          'DF_FM_MUL', 'DF_GIN_Q15', 'DF_SLOW_G', 'DF_FAST_G', 'DF_DIS_SLOW', 'DF_ENVX_MUL',
          'DF_MUFF_LP', 'DF_MUFF_T', 'DF_HIRES', 'OSAT_IN', 'OSAT_OUT', 'OSAT_LIM', 'VCA_LIM', 'SMOOTH_K', 'FINE_Q8']

TABLES = [('O3_K', [T.TB_PREHP, T.TB_SQLP, T.TB_FBHP, T.TB_DCHP, T.TB_KSQ, T.DIST_TONE, 10923, T.TB_C1R]),
          ('O3_INC_TAB', T.INC_TAB), ('O3_TB_MEG', T.TB_MEG), ('O3_TB_ACH', T.TB_ACH),
          ('O3_TB_SWDIRECT', T.TB_SWDIRECT), ('O3_TB_SWCAP', T.TB_SWCAP), ('O3_TB_CUT', T.TB_CUT),
          ('O3_TB_OFF', T.TB_OFF), ('O3_TB_SLO', T.TB_SLO), ('O3_TB_SHI', T.TB_SHI),
          ('O3_TB_KMUL', T.TB_KMUL), ('O3_TB_GCOMP', T.TB_GCOMP), ('O3_SQ_TH', T.SQ_TH), ('O3_ACC_AMT', T.ACC_AMT),
          ('O3_DF_GIN', T.DF_GIN), ('O3_DF_OCOMP', T.DF_OCOMP), ('O3_DF_OGAIN', T.DF_OGAIN),
          ('O3_DF_TRK_HZ', T.DF_TRK_HZ), ('O3_DF_VEG', T.DF_VEG), ('O3_DF_VSUS', T.DF_VSUS),
          ('O3_DF_SLIDE', T.DF_SLIDE), ('O3_DF_ADEC', T.DF_ADEC), ('O3_DF_SATK', T.DF_SATK),
          ('O3_DF_CUTX', T.DF_CUTX), ('O3_DF_HZ', T.DF_HZ), ('O3_DF_ACH_SLOW', T.DF_ACH_SLOW),
          ('O3_DF_ACH_FAST', T.DF_ACH_FAST),
          ('O3_LADDER_B', R.LB), ('O3_LADDER_K', R.LK), ('O3_KF', T.KF), ('O3_LG', T.LG),
          ('O3_TB_UD', T.TB_UD), ('O3_KD', T.KD), ('O3_DRV_IN', T.DRV_IN), ('O3_DRV_LIM', T.DRV_LIM)]

def consts_block():
    L = ['        .set    %-16s %d' % (k + ',', getattr(T, k)) for k in CONSTS]
    assert len(R.LB) == T.S_MAX // 64 + 1 == len(T.DF_HZ) == len(T.KF) == len(T.LG) == len(T.KD)
    L.append('        .set    %-16s %d' % ('NHZ,', len(T.DF_HZ)))
    return '\n'.join(L)

def tables_block():
    L = ['        .align  4']
    for name, vals in TABLES:
        L.append('%s:' % name)
        for i in range(0, len(vals), 8):
            L.append('        .long   ' + ', '.join(str(v) for v in vals[i:i + 8]))
    return '\n'.join(L)

def render(src):
    def put(src, tag, body):
        a = '| >>> GENERATED %s' % tag; b = '| <<< GENERATED %s' % tag
        i = src.index(a); i = src.index('\n', i) + 1; j = src.index(b)
        return src[:i] + body + '\n' + src[j:]
    return put(put(src, 'CONSTANTS', consts_block()), 'TABLES', tables_block())

if __name__ == '__main__':
    src = open(SRC).read(); new = render(src)
    if '--check' in sys.argv:
        if new != src: print('octa303.s is stale: run tools/octa303/gen_tables.py'); sys.exit(1)
        print('octa303.s tables up to date'); sys.exit(0)
    open(SRC, 'w').write(new); print('wrote', SRC)
