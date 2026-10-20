"""OCTA303 v6.9 (dEVILish) golden reference: the integer arithmetic of modules/octa303/octa303.s, in Python.

One engine (TB-303).  Every helper is one assembly idiom.  sim/test_octa303.py runs the assembly
source in cfsim and requires its output to be BIT-IDENTICAL to this model.

v6 CPU work: per-sample multiplies are 'fast' -- ((d >> pre) * c) >> post, one muls.l and two
shifts -- instead of v5's exact split multiply (9 instructions).  CHECK=True asserts every product
stays inside 32 bits; the stress tests run with it on.
"""
import json, os
import o3tables as T

_lc = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ladder_cache.json')
if os.path.exists(_lc):
    _d = json.load(open(_lc)); LB, LK = _d['B'], _d['K']
else:
    LB, LK = T.ladder_tables()
M32 = 0xFFFFFFFF
CHECK = True
PEAK = {}

def s32(x): x &= M32; return x - (1 << 32) if x & 0x80000000 else x
def chk(x, tag=''):
    if CHECK:
        if not (-(1 << 31) <= x < (1 << 31)): raise OverflowError('%s %d' % (tag, x))
        if tag: PEAK[tag] = max(PEAK.get(tag, 0), abs(x))
    return x
def mulq(d, c, s):                                  # exact floor(d*c / 2^s) (control rate)
    hi = chk((d >> s) * c); lo = ((d & ((1 << s) - 1)) * c)
    if CHECK and lo >= (1 << 32): raise OverflowError('lo')
    return chk(hi + (lo >> s))
def mulq15(d, c): return mulq(d, c, 15)
def fm(d, c, pre, post, tag=''):                    # fast: asr pre ; muls.l ; asr post
    return chk((d >> pre) * c, tag) >> post
def mul30(a, b):                                    # a,b >= 0, ~(a*b)>>30
    ah, al, bh, bl = a >> 15, a & 0x7FFF, b >> 15, b & 0x7FFF
    mid = (ah * bl + al * bh) & M32
    return chk(ah * bh + (mid >> 15))
def clamp(x, lo, hi): return lo if x < lo else hi if x > hi else x
def raw(w): return min(w >> 8, 127)
def p_of_word(w0):                                  # v6.4: the word is semitones (Q8), no /5
    return clamp(T.P_CENTER + (w0 - 0x4000), T.P_LO, T.P_HI)
def inc_of_p(p):
    o, r = divmod(p, 3072)
    return (T.INC_TAB[r >> 2] << o) & M32
def blep(phase, inc):
    if phase < inc:
        t = min((phase << 3) // (inc >> 12), 32768); q = 32768 - t
        return -((q * q) >> 15)
    r = (-phase) & M32
    if r < inc and phase != 0:
        t = min((r << 3) // (inc >> 12), 32768); q = 32768 - t
        return (q * q) >> 15
    return 0
def softclip(y):                                    # clamp to +-sqrt2, y - y^3/6  (S20)
    y = clamp(y, -1482910, 1482910)
    xs = y >> 8; x2 = (xs * xs) >> 12; x3 = (x2 * xs) >> 12
    return y - ((x3 * 10923) >> 8)
FIELDS = ('latched', 'wave', 'dist', 'phase', 'inc', 'pcur', 'cs', 'meg', 'megs', 'veg',
          'accd', 'accamt', 'accvca', 'cap', 'amp', 'ampstep', 'hp', 'y1', 'y2', 'y3', 'y4', 'fb',
          'dc', 'tone', 'c1', 'b', 'k', 'gcomp', 'ptgt', 'cut', 'res', 'env', 'dec',
          'gin', 'vegd', 'vsus', 'trkhz', 'fmq', 'sctrl', 'kmul', 'ovca', 'ocomp', 'ogain',
          'slide', 'swp', 'adec', 'satk', 'vatt', 'spd', 'muff', 'mlo', 'cutx', 'envx', 'ginq15', 'nz',
          'gmode', 'gate', 'glvl', 'gstep', 'lstep', 'ltick', 'idle', 'kmax', 'tps', 'gnew', 'gel', 'gend', 'sqth', 'ud', 'sql', 'accvg', 'osin', 'oslim', 'fine', 'cutb', 'envs', 'smok', 'setsl', 'gsel', 'fcnt', 'fpt', 'fseen', 'gelf', 'mach')
class Track:
    def __init__(self):
        for k in FIELDS: setattr(self, k, 0)
        self.cs = 1
        self.accvg, self.osin, self.oslim = T.TB_ACCVCA_GAIN, T.OSAT_IN, T.OSAT_LIM

def note_on(st, code, w):
    st.wave, st.dist = code & 1, code >> 1
    acc = raw(w[5])
    st.pcur = clamp(p_of_word(w[0]) + st.fine, T.P_LO, T.P_HI) << 8   # v7.0: FINE
    st.cs = 1
    st.accd = 1 if acc else 0
    st.accamt = T.ACC_AMT[acc]                      # v6.7: the ACCENT pot's law, a table (v6.6: acc * 8454660)
    st.meg = T.ONE30
    st.veg = T.ONE30
    st.vatt = 0 if (st.satk and not acc) else T.ONE30   # SATK: non-accented notes fade in
    st.gnew = 1                                     # v6.5: the gate opens at the next gate_frame

def tdiv(a, b): return -((-a) // b) if a < 0 else a // b   # truncating, as divs.l

def trck(s, d, hz):
    """TRCK, linear in Hz: the cutoff at ladder index s>>6 plus hz*d/3072 Hz (d = Q8 semitones
    from TUNE 0), back to an index by binary search; the low notes can close the filter."""
    i = s >> 6
    f2 = T.DF_HZ[i] + tdiv(hz * d, 3072)
    if f2 <= T.DF_HZ[0]: return 0
    lo, hi = 0, len(T.DF_HZ) - 1                         # largest j with DF_HZ[j] <= f2
    while lo < hi:
        m = (lo + hi + 1) >> 1
        if T.DF_HZ[m] <= f2: lo = m
        else: hi = m - 1
    return (lo << 6) + (s & 63)

def kfb(i, kmul, ud):
    """v6.9: the feedback at ladder index i -- the RES pot's fraction of the oscillation point (KF = KO / LK
    times the shape by frequency) less the decay UD (dB/ms, Q10) times KD (the feedback a dB/ms), never < 0."""
    k = (((LK[i] * kmul) >> 15) * T.KF[i]) >> 12
    k -= chk(ud * T.KD[i], 'ud') >> 10
    return k if k > 0 else 0

def ctrl(st):
    st.pcur += mulq15((st.ptgt << 8) - st.pcur, st.slide)              # SLID
    st.inc = inc_of_p(st.pcur >> 8)
    st.sqth = T.SQ_TH[st.pcur >> 16]                                   # v6.6: the square's duty by pitch
    st.meg = mul30(st.meg, st.adec if st.accd else T.TB_MEG[st.dec])    # ADEC
    st.megs += mulq15(st.meg - st.megs, T.TB_MEG_ATT)
    d = st.veg - st.vsus                                               # VDEC (the final level may move
    st.veg = st.vsus + mul30(d, st.vegd) if d >= 0 else st.vsus - mul30(-d, st.vegd)   # above the envelope)
    if st.satk:
        st.vatt += mul30(T.ONE30 - st.vatt, st.satk)                     # SATK
        if st.vatt > T.ONE30 - 64: st.vatt = T.ONE30
    cut, res, env = st.cut, st.res, st.env
    vin = mul30(st.megs, st.accamt) if (st.accd and st.swp) else 0     # SWP 0: no sweep circuit
    if st.spd == 2:                                                    # SPD NORM: the 303
        if vin > st.cap:
            st.cap += mulq15(vin - st.cap, T.TB_ACH[res])
        st.cap -= mulq15(st.cap, T.TB_DIS)
        capterm = st.cap
    elif st.spd == 3:                                                  # SLOW
        if vin > st.cap:
            st.cap += mulq15(vin - st.cap, T.DF_ACH_SLOW[res])
        st.cap -= mulq15(st.cap, T.DF_DIS_SLOW)
        capterm = st.cap * T.DF_SLOW_G
    else:                                                              # FAST: the change, never below 0
        if vin > st.cap:
            st.cap += mulq15(vin - st.cap, T.DF_ACH_FAST[res])
        st.cap -= mulq15(st.cap, T.TB_DIS)
        capterm = ((vin - st.cap) >> 4) * T.DF_FAST_G if vin > st.cap else 0
    sweep = mulq15(vin, T.TB_SWDIRECT[res]) + mulq15(capterm, T.TB_SWCAP[res])
    if st.envx:                                                        # ENVX: x3, from none
        S = (((T.TB_SLO[127] + (((T.TB_SHI[127] - T.TB_SLO[127]) * res * 258) >> 15)) * T.DF_ENVX_MUL) * env) // 127
    else:
        S = T.TB_SLO[env] + (((T.TB_SHI[env] - T.TB_SLO[env]) * res * 258) >> 15)
    base = T.DF_CUTX[cut] if st.cutx else T.TB_CUT[cut]                 # CUTX
    if not st.smok:                                                    # v7.0: the first control step takes them
        st.cutb, st.envs, st.smok = base << 8, S << 8, 1
    st.cutb += mulq15((base << 8) - st.cutb, T.SMOOTH_K)               # v7.0: ~1 ms glides, no steps
    st.envs += mulq15((S << 8) - st.envs, T.SMOOTH_K)
    base, S = st.cutb >> 8, st.envs >> 8
    s = base + ((((st.megs >> 15) - T.TB_OFF[cut]) * S) >> 15) + (((sweep >> 15) * T.TB_SWEEP_ST) >> 15)
    s = clamp(s, 0, T.S_MAX - 1)
    if st.trkhz:
        s = trck(s, (st.pcur >> 8) - T.P_CENTER, st.trkhz)            # TRCK
    st.sctrl = s
    st.kmul = T.TB_KMUL[res] * (1 if st.swp == 2 else T.DF_HIRES)        # SWP 1/0: resonance doubled
    st.ud = T.TB_UD[res]                                               # v6.9: the ring's decay, dB/ms Q10
    i = s >> 6
    st.b = LB[i]; st.c1 = (LB[i] * T.TB_C1R) >> 12
    st.k = kfb(i, st.kmul, st.ud)
    g0 = T.TB_GCOMP[0]
    st.gcomp = ((g0 + (((T.TB_GCOMP[res] - g0) * st.ocomp) >> 12)) * st.ogain) >> 12   # OVDR comp
    st.gcomp = (st.gcomp * T.LG[i]) >> 12                             # v6.7: LG, the level by frequency
    st.accvca += mulq15(vin - st.accvca, T.TB_ACC_VCA)
    v = st.veg if st.vatt >= T.ONE30 else mul30(st.veg, st.vatt)        # SATK (none: v6.1 exactly)
    tgt = (v >> 16) + mulq15(st.accvca >> 16, st.accvg)                # Q14; v7.0: ACCV
    if st.gmode:                                                       # v6.5: the 303's gate
        st.glvl += mulq15((32767 if st.gate else 0) - st.glvl, T.GATE_K)
        tgt = (tgt * st.glvl) >> 15
    st.ampstep = (tgt - st.amp) >> 4

def sample(st):
    if st.fmq:                                       # FM: the last VCA sample moves the cutoff, per sample
        s = clamp(st.sctrl + ((((st.ovca >> 8) * st.fmq)) >> 12), 0, T.S_MAX - 1)
        i = s >> 6
        st.b = LB[i]; st.c1 = (LB[i] * T.TB_C1R) >> 12
        st.k = kfb(i, st.kmul, st.ud)
    inc = st.inc
    ph = st.phase = (st.phase + inc) & M32
    if st.wave == 0:
        x = (ph >> 11) - (1 << 20)
        x -= blep(ph, inc) << 5
    else:
        th = st.sqth                                 # v6.6: high while ph < th (duty by pitch)
        x = (1 << 20) if ph < th else -(1 << 20)
        x += blep(ph, inc) << 5
        x -= blep((ph - th) & M32, inc) << 5
        x = fm(x, T.TB_KSQ, 7, 8, 'sq')
        st.sql += fm(x - st.sql, T.TB_SQLP, 4, 11, 'sqlp')   # v6.9: the 303's square has soft edges
        x = st.sql
    st.hp += fm(x - st.hp, T.TB_PREHP, 4, 11, 'prehp')
    if st.ginq15:                                    # OVDR up to normal: v6.1's product, exactly
        x = fm(x - st.hp, st.gin, 7, 8, 'gin')
    else:                                            # overdrive, to 66.6x
        x = fm(x - st.hp, st.gin, 6, 4, 'gin')
    if st.swp < 2:                                   # SWP 1/0: the analogue noise floor, ~-84 dB, so
        if st.nz == 0: st.nz = 0x1D872B41              # (a Galois LFSR never leaves 0: seed it)
        st.nz = (st.nz >> 1) ^ (0xD0000001 if st.nz & 1 else 0)   # the filter can self-oscillate with no VCO
        x += 64 if st.nz & 1 else -64
    y4 = st.y4
    st.fb += fm(y4 - st.fb, T.TB_FBHP, 4, 11, 'fbhp')
    fb = clamp(y4 - st.fb, -(1 << 23), 1 << 23)
    y0 = softclip(x - chk((fb >> 8) * st.k, 'kfb'))
    st.y1 += fm(y0 - st.y1 + st.y2, st.c1, 7, 8, 'l1')
    st.y2 += fm(st.y1 - 2 * st.y2 + st.y3, st.b, 7, 8, 'l2')
    st.y3 += fm(st.y2 - 2 * st.y3 + y4, st.b, 7, 8, 'l3')
    st.y4 = y4 + fm(st.y3 - 2 * y4, st.b, 7, 8, 'l4')
    o = fm(st.y4, st.gcomp, 6, 6, 'gc')
    o = clamp(o, -T.VCA_LIM, T.VCA_LIM)              # v6.9: the VCA multiply never wraps
    st.amp += st.ampstep
    if st.amp < 0: st.amp = 0
    o = fm(o, st.amp, 6, 8, 'amp')
    if st.muff:                                      # MUFF: the bass passes, the rest is clipped
        st.mlo += fm(o - st.mlo, T.DF_MUFF_LP, 4, 11, 'mlo')
        h = o - st.mlo
        if st.muff == 1:
            h = clamp(h, -1048576, 1048576)                      # v6.7: no overflow (softclip saturates far below)
            h = fm(softclip(fm(h, 3413, 2, 8, 'mk')), 9830, 4, 11, 'mt')     # T*softclip(h/T), T = 0.3
        else:
            h = clamp(h, -T.DF_MUFF_T, T.DF_MUFF_T)
        o = st.mlo + h
    st.ovca = o                                      # FM reads the VCA after the Muffler
    if st.dist:
        o = softclip(o * T.DIST_GAIN + T.DIST_BIAS)
        st.tone += fm(o - st.tone, T.DIST_TONE, 7, 8, 'tone')
        o = st.tone
    st.dc += fm(o - st.dc, T.TB_DCHP, 4, 11, 'dc')
    y = clamp(o - st.dc, -st.oslim, st.oslim)                     # v6.8: the output stage's soft ceiling
    y = softclip(fm(y, st.osin, 2, 8, 'osi'))                     # v7.0: DRIV pushes into it
    return fm(y, T.OSAT_OUT, 6, 9, 'oso')

def set_df(st, df):
    """dEVILish's twelve knobs (locks applied), or None: DF_NEUTRAL, the 303 of v6.1.1."""
    k = [min(v, 127) for v in (df or T.DF_NEUTRAL)]
    st.gin, st.ocomp, st.ogain = T.DF_GIN[k[0]], T.DF_OCOMP[k[0]], T.DF_OGAIN[k[0]]
    st.ginq15 = int(k[0] <= T.DF_GIN_Q15)
    st.fmq, st.trkhz = k[1] * T.DF_FM_MUL, T.DF_TRK_HZ[k[2]]
    st.vegd, st.vsus = T.DF_VEG[k[3]], T.DF_VSUS[k[3]]
    st.slide, st.adec = T.DF_SLIDE[k[4]], T.DF_ADEC[k[5]]
    st.satk = T.DF_SATK[k[6]]
    st.swp = 2 - min(k[7], 2)                        # ACID 2 (the 303), WHST 1, SELF 0
    st.spd = min(k[8], 2) + 1                        # FAST 1, NORM 2 (the 303), SLOW 3
    st.muff = min(k[9], 2)                           # OFF, SOFT, HARD
    st.cutx, st.envx = int(k[10] >= 1), int(k[11] >= 1)

def set_setup(st, setup, df):
    """v7.0: the TB-303 machine's SETUP page (o3tables.SETUP_NAMES), or None: SETUP_NEUTRAL (a TB303* sample).
    SLID acts only without dEVILish on the track (dEVILish's own SLID wins)."""
    k = [min(v, 127) for v in (setup or T.SETUP_NEUTRAL)]
    st.accvg = (T.TB_ACCVCA_GAIN * k[5]) >> 6
    st.fine = (k[2] - 64) * T.FINE_Q8
    st.osin, st.oslim = T.DRV_IN[k[4]], T.DRV_LIM[k[4]]
    st.gsel = 1 if k[1] >= 1 else 0                  # GATE: OFF / 303
    if df is None:
        st.slide = T.DF_SLIDE[k[3]]

def gate_frame(st, seq):
    """v6.5, once a frame (the frame's last call) on a 303 track: seq = (hold, step, tick, slides,
    length) as the unit reads them -- the track's AMP HOLD from the live lane, the sequencer's step
    word and tick byte, the OR of the track record's trigless-trig and trigless-lock masks (bit s =
    step s), the track's length.
    v6.5d: the gate is timed from the note's START, in ticks (gel), not from the step word: on the
    unit a START reaches the renderer about a tick after the step word moves (measured, 12 Oct 2026:
    the step-word gate closed ~1/3 of a step after the note).  Half a step = tps ticks counted
    twice (gend = tps, +2 tps a tie)."""
    hold, s, k, mask, L = seq
    if not 1 <= L <= 64: L = 16
    s = s % L
    moved = s != st.lstep or k != st.ltick
    if s != st.lstep:                                  # a new step: the last one's ticks
        if st.kmax >= 1: st.tps = st.kmax + 1
        st.kmax = 0; st.idle = 0
    elif k != st.ltick: st.idle = 0
    elif st.idle < T.GATE_IDLE: st.idle += 1
    if k > st.kmax: st.kmax = k
    st.lstep, st.ltick = s, k
    if st.tps == 0: st.tps = T.GATE_TPS0
    if moved and st.gel < 4096: st.gel += 1            # ticks since the START
    f = min(st.fcnt + 1, 4095)                         # v7.0: the frames a tick, measured
    if moved:
        if st.fseen: st.fpt = f
        st.fseen = 1; f = 0
    st.fcnt = f
    if st.gelf < 65535: st.gelf += 1                   # v7.0: the frames since the START
    if st.gnew:                                        # a 303 START: the note's step, the clock from 0
        st.gnew = 0; st.gate = 1; st.gel = 0; st.gelf = 0
        st.gend = (7 * st.tps + 3) // 6                # v7.0: 3.5 of the step's 6 clocks, doubled (Whittle)
        st.gstep = (s + 1) % L if 2 * k >= st.tps else s
    if not st.gsel:                                    # v7.0: SETUP's GATE OFF: the AMP decides
        st.gmode = 0; st.glvl = 32767; return
    st.gmode = 1
    if st.idle >= T.GATE_IDLE:                         # the sequencer stopped: the AMP decides
        st.gate = 1; return
    due = (2 * st.gelf >= st.gend * st.fpt) if st.fpt else (2 * st.gel >= st.gend)
    if st.gate and due:                                # 3.5 clocks (+ a step a tie) since the START
        nxt = (st.gstep + 1) % L
        if (mask >> nxt) & 1:                          # the next step slides: still on
            st.gstep = nxt; st.gend += 2 * st.tps
        else:
            st.gate = 0

def render_call(st, w, start, code, n, alive=True, df=None, last=None, seq=None, setup=None):
    """One sy_render call: w = the record's six words as the call found them, start = this is the
    frame's last call (end == 16) and the packer's START bit is set, code = name_code() of the new
    voice's file (-1 = not ours), n = the samples this call ships, alive = the CF voice byte,
    df = dEVILish's twelve knobs on this track or None (no dEVILish there).
    Returns None (stock's samples stand) or n output longs (written to L and R)."""
    if start and code >= 0:
        set_df(st, df)                               # SATK decides how the note starts
        set_setup(st, setup, df)                     # v7.0: FINE decides where it starts
    if start:
        if code >= 0:
            note_on(st, code, w); st.latched = 1
        else:
            st.latched = 0
    if st.latched and last and seq is not None:    # v7.0: SETUP's GATE (v6.5's gate, Whittle's length),
        set_df(st, df); set_setup(st, setup, df)     # once a frame, after o3_params, whatever the voice
        gate_frame(st, seq)
    if not st.latched or not alive or n == 0:
        return None
    set_df(st, df)
    set_setup(st, setup, df)
    st.ptgt = clamp(p_of_word(w[0]) + st.fine, T.P_LO, T.P_HI)        # v7.0: FINE
    st.cut, st.res, st.env, st.dec = raw(w[1]), raw(w[2]), raw(w[3]), raw(w[4])
    out = []
    for _ in range(n):
        st.cs -= 1
        if st.cs == 0:
            st.cs = T.CS; ctrl(st)
        v = clamp(sample(st) >> T.SHIFT_OUT, -32767, 32767)
        out.append((v << 16) & M32)
    return out
