"""OCTA303 v6.9 (dEVILish) -- every constant and lookup table of the engine, computed in one place.

gen_tables.py writes these into modules/octa303/octa303.s; ref303.py imports them.
A table is derived here from a stated physical/design quantity, never typed by hand.
"""
import math

FS = 44100
CS = 16                     # control step: envelopes/cutoff/pitch every 16 samples (0.36 ms)
SHIFT_OUT = 6               # S20 -> s16 : >>5 is full scale, >>6 leaves 6 dB headroom

# ---------------------------------------------------------------- pitch
# frame word 0 (PTCH) = raw<<8 + the LFO's fraction.  v6.4, Tim Hastie's tuning system: on a 303
# track the PTCH byte is SEMITONES (raw 64 = 0, one unit a semitone; stock: 5 units a semitone), the
# page clone limits TUNE to TUNE_LO..TUNE_HI = -24..+24 (raw 40..88: four octaves, 0 in the middle;
# v6.5c, the author's choice over v6.4's -12..+24).
# p_abs (Q8 semitones) = P_CENTER + (word0 - 0x4000), clamped to P_LO..P_HI (p_abs = 16384 -> BASE note)
P_CENTER = 64 * 256
TUNE_LO, TUNE_HI = -24, 24
P_LO, P_HI = P_CENTER - 36 * 256, P_CENTER + 36 * 256      # the knob's range plus an octave of LFO
BASE_HZ = 130.81278          # C3: PTCH 0 plays C3 (the author's choice: his sound centred, keys aligned)
F_LOW = BASE_HZ * 2 ** (-64 / 12)
INC_TAB = [round(F_LOW * 2 ** (i / 768) / FS * 2 ** 32) for i in range(768)]   # one octave, 1/64 semitone

def q15(x): return int(round(x * 32768))
def q30(x): return int(round(x * (1 << 30)))
def onepole(tau_s, n=CS): return 1.0 - math.exp(-n / (FS * tau_s))
def onepole_hz(hz, n=1): return 1.0 - math.exp(-2 * math.pi * hz * n / FS)

ONE30 = (1 << 30) - 1

# ---------------------------------------------------------------- v6.5: the 303's own gate
# With the track's AMP HOLD at INF (127, locks applied) OCTA303 gates itself as the 303 does: a note
# sounds for half a step, and stays on into the next step when that step holds a trigless trig or a
# trigless lock (a slide).  Any other HOLD: the AMP decides, v6.4 sample for sample.
GATE_HOLD_INF = 127
GATE_K = q15(onepole(0.003))            # the gate's edges, 3 ms (no click), at the control rate
GATE_IDLE = 2048                        # frames (0.74 s) without a step/tick change = the sequencer stopped
GATE_TPS0 = 6                           # ticks a step before one has been measured (1x)

# ---------------------------------------------------------------- TB-303 engine
# v6.4: every 303 constant below checked against the Roland service notes' main-board schematic
SLIDE_TAU = 103.3e3 * 0.22e-6           # the slide RC: 103.3k (DAC + protection, Whittle p. 16) * C35 0.22 uF = 22.7 ms
TB_SLIDE = q15(onepole(SLIDE_TAU))      # 303 slide: ~68 ms to 95 % (v6.3: 21 ms, an inconsistency with DF_SLIDE's own RC)
# >>> CAL v6.7
# v6.9 (19 Oct 2026): the RESONANCE by its decay.  Din Sync measured at every saw reset: at full RES the real
# ring decays ~2.2 dB/ms from 400 Hz to 11 kHz, v6.8's 6-8 dB/ms above 1 kHz (RES 95 agreed).  New law
# k = LK*KMUL*KF - UD*KD (km0-5 on seven RES knots, kr0-4 the shape, ud0-5 dB/ms); the square's soft edges (sqlp,
# a one-pole lowpass: Din Sync's square is 3-9 dB under the saw's harmonics above 1.4 kHz).  Fitted, with the
# accent, the cutoff/env/decay laws and the levels, on Din Sync (bands, peaks, the ring's decay in 12 RES x
# frequency cells, the BRIGHTNESS -- spectral centroid -- of all 400 notes at 2..1000 ms) and tinyloops (the
# ring's frequency, the three drops' decay, the spectrum), under two rules: the ring never grows (no
# self-oscillation, -1.2 dB/ms or faster) and never decays faster as RES goes up.  v6.8 -> v6.9: ring cells
# 1.09 -> 0.16 (log2), brightness 0.30 -> 0.18 octave (square 0.28 -> 0.21), tinyloops drops -3.95/-7.8/-6.6
# -> -3.4/-3.1/-3.1 dB/ms (303: -3.4/-3.0/-3.1), its spectrum 6.1 -> 1.0 dB, bands 4.73 -> 4.68, peaks 2.30
# -> 2.29 dB; tinyloops' knobs come out at CUT 52 RES 112 ENV 111 ACC 125 (the photo: RES 85-90 %).  Level:
# v6.8's -2 dB at mid knobs (the accents are louder against the notes, as on Din Sync; ceiling -0.9 dBFS).
CAL = {
    'cut0':      190.904,
    'cut1':      223.911,
    'cut2':      417.993,
    'cut3':      914.838,
    'cut4':      1446.95,
    'slo0':      0.642997,
    'slo1':      0.764815,
    'slo2':      1.20609,
    'slo3':      3.05027,
    'slo4':      4.07984,
    'shi0':      0.838333,
    'shi1':      0.675048,
    'shi2':      1.5677,
    'shi3':      3.46185,
    'shi4':      4.88259,
    'km0':       0.0722092,
    'km1':       0.39515,
    'km2':       0.412628,
    'km3':       0.596876,
    'km4':       0.817852,
    'km5':       0.864409,
    'ud0':       0.473728,
    'ud1':       0.45,
    'ud2':       0.26127,
    'ud3':       0,
    'ud4':       0.521166,
    'ud5':       0.754574,
    'gc0':       0.853566,
    'gc1':       1.38368,
    'gc2':       1.72866,
    'gc3':       2.2254,
    'dec0':      0.0843294,
    'dec1':      0.180131,
    'dec2':      0.618953,
    'dec3':      1.76538,
    'dec4':      2.34939,
    'acc0':      0.104631,
    'acc1':      0.309067,
    'acc2':      1.0104,
    'acc3':      1.46856,
    'kr0':       0.975876,
    'kr1':       0.8,
    'kr2':       1.02538,
    'kr3':       1.12766,
    'kr4':       1.1469,
    'lg0':       0.306474,
    'lg1':       0.327793,
    'lg2':       0.448971,
    'lg3':       0.708251,
    'lg4':       1.90264,
    'swk0':      0.797365,
    'swk1':      0.370416,
    'swk2':      0.845848,
    'swk3':      1.0,
    'chk0':      1.0,
    'chk1':      1.0,
    'chk2':      1.03938,
    'chk3':      1.06649,
    'chk4':      1.0,
    'off_a':     0.00461511,
    'off_b':     0.304783,
    'acc_dec':   0.130431,
    'meg_att':   0.0003,
    'ach0':      0.059672,
    'ach1':      0,
    'dis':       0.126172,
    'swd':       0.312903,
    'swc':       0.620224,
    'sweep_st':  76.085,
    'accvca_gain': 0.789405,
    'accvca_tau': 0.0012376,
    'prehp':     148.7,
    'fbhp':      45.2607,
    'dchp':      8.84257,
    'c1r':       2.3481,
    'ksq':       0.576456,
    'sq_c2':     0.533233,
    'veg_tau':   1.38888,
    'satk':      0.00032028,
    'smax':      12531.6,
    'osat_db':   -0.889752,
    'sqlp':      3115.48,
    'gall':      3.7383}
KNOT_RAW = (0, 32, 64, 95, 127)                 # 0/25/50/75/100 percent of the pots
def pchip(xs, ys, x):
    """Monotone piecewise-cubic Hermite (Fritsch-Carlson, scipy's PchipInterpolator rules)."""
    n = len(xs); h = [xs[i + 1] - xs[i] for i in range(n - 1)]; m = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    sg = lambda v: (v > 0) - (v < 0)
    dd = [0.0] * n
    for k in range(1, n - 1):
        if sg(m[k - 1]) * sg(m[k]) <= 0: dd[k] = 0.0
        else:
            w1 = 2 * h[k] + h[k - 1]; w2 = h[k] + 2 * h[k - 1]
            dd[k] = (w1 + w2) / (w1 / m[k - 1] + w2 / m[k])
    def edge(h0, h1, m0, m1):
        e = ((2 * h0 + h1) * m0 - h0 * m1) / (h0 + h1)
        if sg(e) != sg(m0): return 0.0
        if sg(m0) != sg(m1) and abs(e) > abs(3 * m0): return 3 * m0
        return e
    dd[0] = edge(h[0], h[1], m[0], m[1]); dd[-1] = edge(h[-1], h[-2], m[-1], m[-2])
    k = max(0, min(n - 2, max(i for i in range(n - 1) if xs[i] <= x) if x >= xs[0] else 0))
    t = (x - xs[k]) / h[k]; t2 = t * t; t3 = t2 * t
    return ((2 * t3 - 3 * t2 + 1) * ys[k] + (t3 - 2 * t2 + t) * h[k] * dd[k] + (-2 * t3 + 3 * t2) * ys[k + 1] + (t3 - t2) * h[k] * dd[k + 1])
def _curve(vals): return [pchip(KNOT_RAW, vals, r) for r in range(128)]
TB_PREHP = q15(onepole_hz(CAL['prehp']))   # VCO->VCF coupling highpass (v6.5f: 44.5 Hz)
TB_FBHP = q15(onepole_hz(CAL['fbhp']))     # highpass inside the resonance loop (v6.5f: 150 Hz, Open303)
TB_DCHP = q15(onepole_hz(CAL['dchp']))     # output coupling (v6.5f: 24 Hz)
TB_MEG_ATT = q15(onepole(CAL['meg_att']))  # MEG attack (v6.5f: 3 ms)
TB_ACC_VCA = q15(onepole(CAL['accvca_tau']))   # accent VCA path (v6.5f: 47k * 0.033uF = 1.55 ms)
TB_MEG_ACC = q30(math.exp(-CS / (FS * CAL['acc_dec'] / math.log(10))))  # accent MEG decay (v6.5f: 0.2 s, Whittle)
_DEC = [math.exp(v) for v in _curve([math.log(CAL['dec%d' % i]) for i in range(5)])]   # -20 dB time by DECAY raw
DEC_T_MIN, DEC_T_MAX = _DEC[0], _DEC[127]
TB_MEG = [q30(math.exp(-CS / (FS * t / math.log(10)))) for t in _DEC]
TB_DIS = q15(onepole(CAL['dis']))          # accent-sweep capacitor discharge (v6.5f: 0.2 s)
TB_ACH = [q15(onepole((CAL['ach0'] + CAL['ach1'] * r / 127) * math.exp(v))) for r, v in enumerate(_curve([math.log(CAL['chk%d' % i]) for i in range(5)]))]   # charge: 47k + pot (2nd res gang), shaped
TB_SWDIRECT = [q15(min(0.999, CAL['swd']) * (1 - r / 127)) for r in range(128)]   # direct path, pot ACW (v6.5f: 100/147)
TB_SWCAP = [q15(min(0.999, max(0.0, CAL['swc'] * v))) for v in _curve([0.0] + [CAL['swk%d' % i] for i in range(4)])]   # the 2nd RES gang's law
TB_SWEEP_ST = int(round(CAL['sweep_st'] * 256))                 # full accent sweep, Q8 semitones
TB_ACCVCA_GAIN = q15(min(0.999, CAL['accvca_gain']))   # accent VCA boost (v6.5f: 0.85)

# cutoff domain: s (Q8 semitones) above FC0 = 20 Hz; tables are 1/4 semitone
FC0 = 20.0
def s_of_hz(hz): return 12 * math.log2(hz / FC0) * 256
S_MAX = int(s_of_hz(CAL['smax'])) // 64 * 64       # v6.7: the ladder's top, from the fit (v6.6: 108 * 256, ~10.2 kHz)
TB_CUT = [int(round(s_of_hz(max(math.exp(v), 21.0)))) for v in _curve([math.log(CAL['cut%d' % i]) for i in range(5)])]
TB_OFF = [q15(CAL['off_a'] * r / 127 + CAL['off_b']) for r in range(128)]
TB_SLO = [int(round(max(v, 0.0) * 3072)) for v in _curve([CAL['slo%d' % i] for i in range(5)])]   # env sweep, octaves*12*256
TB_SHI = [int(round(max(v, 0.0) * 3072)) for v in _curve([CAL['shi%d' % i] for i in range(5)])]
# v6.9: the RES pot's law on seven knots (the 303's pot is steep at its top: 95 -> 127 takes the ring from
# ~13 to ~2 dB/ms on Din Sync), as a fraction of the ladder's true oscillation point (KF holds KO / LK)
RES_KNOTS = (0, 32, 64, 80, 95, 110, 127)
def _rcurve(vals): return [pchip(RES_KNOTS, vals, r) for r in range(128)]
TB_KMUL = [q15(min(0.999, max(0.0, v))) for v in _rcurve([0.0] + [CAL['km%d' % i] for i in range(6)])]
# v6.9: the ring's own decay by RES, dB/ms (Q10), whatever the cutoff: the real 303 at full RES rings
# ~2.2 dB/ms from 400 Hz to 11 kHz (Din Sync), which no fraction of the oscillation point can give
TB_UD = [int(round(min(60.0, max(0.0, v)) * 1024)) for v in _rcurve([0.0] + [CAL['ud%d' % i] for i in range(6)])]
TB_GCOMP = [int(round(4096 * 1.3 * CAL['gall'] * math.exp(v))) for v in _curve([0.0] + [math.log(CAL['gc%d' % i]) for i in range(4)])]
ACC_AMT = [int(round(max(0.0, v) * 127 * 8454660)) for v in _curve([0.0] + [CAL['acc%d' % i] for i in range(4)])]   # Q30
TB_C1R = int(round(CAL['c1r'] * 4096))     # ladder: first stage = b * C1R (Q12); the schematic's smaller bottom cap
TB_KSQ = int(round(CAL['ksq'] * 32768))    # square level (v6.6: 27853)
TB_SQLP = q15(onepole_hz(CAL['sqlp']))   # v6.9: the square's soft edges (Din Sync: ~3-9 dB under the saw's harmonics above 1.4 kHz)
TB_SATK = q30(1.0 - math.exp(-CS / (FS * CAL['satk'])))   # the 303's own attack on non-accented notes (DF_SATK[0])
VEG_TAU = CAL['veg_tau']                   # the VCA decay (DF_VEG at VDEC 64; v6.6: 1.23 s, Open303)
# v6.7: the resonance's strength (KF) and the level (LG) by cutoff frequency, Q12 by ladder index
FKN_HZ = (100.0, 300.0, 1000.0, 3000.0, 10000.0)
def _ixcurve(pre):
    xs = [math.log2(f) for f in FKN_HZ]; ys = [math.log(CAL[pre + '%d' % i]) for i in range(5)]
    out = []
    for i in range(S_MAX // 64 + 1):
        x = min(max(math.log2(FC0 * 2.0 ** (i * 64 / 3072.0)), xs[0]), xs[-1])
        out.append(int(round(4096 * math.exp(pchip(xs, ys, x)))))
    return out
LG = _ixcurve('lg')

# ---------------------------------------------------------------- v6.9: the resonance by its decay
# The ladder of ref303.sample, small signal (5 states: y1..y4 and the loop highpass), solved per ladder
# index: KO = the feedback at which its resonant mode neither grows nor decays, KD = the feedback taken
# off that point for each dB/ms of decay.  k = LK * KMUL * KF - UD * KD, KF = KO / LK * the shape kr(f).
def _lin_M(b, c1, k, fbhp):
    import numpy as np
    A = np.zeros((5, 5))
    for col in range(5):
        y1, y2, y3, y4, fb = [1.0 if j == col else 0.0 for j in range(5)]
        fb = fb + fbhp * (y4 - fb); y0 = -k * (y4 - fb)
        y1 = y1 + c1 * (y0 - y1 + y2); y2 = y2 + b * (y1 - 2 * y2 + y3)
        y3 = y3 + b * (y2 - 2 * y3 + y4); y4 = y4 + b * (y3 - 2 * y4)
        A[:, col] = [y1, y2, y3, y4, fb]
    return A
def _lin_decay(b, c1, k, fbhp):                     # dB/ms of the slowest resonant (complex) mode
    import numpy as np
    ev = np.linalg.eigvals(_lin_M(b, c1, k, fbhp)); ev = ev[np.abs(np.angle(ev)) > 2 * math.pi * 15 / FS]
    return 20 * math.log10(max(abs(ev))) * FS / 1000 if len(ev) else -999.0
def _lin_k(b, c1, fbhp, target):
    lo, hi = 0.0, 1.0
    while _lin_decay(b, c1, hi, fbhp) < target: hi *= 1.5
    for _ in range(50):
        m = (lo + hi) / 2
        if _lin_decay(b, c1, m, fbhp) < target: lo = m
        else: hi = m
    return (lo + hi) / 2
def resonance_tables(LB):
    fbhp = TB_FBHP / 32768.0; KO, KD = [], []
    for i in range(S_MAX // 64 + 1):
        b = LB[i] / 32768.0; c1 = b * TB_C1R / 4096.0
        ko = _lin_k(b, c1, fbhp, 0.0); KO.append(ko); KD.append(ko - _lin_k(b, c1, fbhp, -1.0))
    return KO, KD
def _ladder_cache():
    import json, os
    p = os.path.join(os.path.dirname(os.path.abspath(globals().get('__file__', 'o3tables.py'))), 'ladder_cache.json')
    if os.path.exists(p): d = json.load(open(p))
    else: d = {}; d['B'], d['K'] = ladder_tables()
    if d.get('res_key') != [TB_C1R, TB_FBHP, S_MAX]:
        d['KO'], d['KD'] = resonance_tables(d['B']); d['res_key'] = [TB_C1R, TB_FBHP, S_MAX]
    return d

# the square's duty (high part) moves with the pitch (Whittle: 45 % high .. 71 % low): sq_c2 at C2, -3.5 % an octave
SQ_TH = [int(round(min(0.71, max(0.45, CAL['sq_c2'] - 0.035 * (i - 52) / 12.0)) * 2 ** 32)) & 0xFFFFFFFF for i in range(128)]
# v6.8: the 303's output stage saturates softly: on Din Sync every accented note peaks at ~0.35-0.39 of full
# scale whatever the knobs (A5, D1, E1, E5), the normal notes below.  Out = OSAT_OUT * softclip(OSAT_IN * y):
# unity for small signals, a soft ceiling of osat_db dBFS (softclip's top, 988783 in S20, reached at sqrt2).
SOFTCLIP_TOP = 988783
OSAT_OUT = int(round(10 ** (CAL['osat_db'] / 20.0) * 32767 * 64 * 512 / (SOFTCLIP_TOP >> 6)))   # fm(.., 6, 9)
OSAT_IN = int(round(2 ** 25 / OSAT_OUT))                                                    # fm(.., 2, 8)
OSAT_LIM = 4 * ((2 ** 31 - 1) // OSAT_IN) - 4                                               # (y >> 2) * IN fits 32 bits
# v6.9: the VCA's multiply (o >> 6) * amp must fit 32 bits; the loudest amp is the full VCA envelope plus the
# accent path at ACC 127.  The ladder's output is held under VCA_LIM before it (reached only by dEVILish's
# self-oscillating modes or OVDR far up; the 303 alone peaks ~0.9 of it): a clip there, never a wrap.
AMP_MAX = (ONE30 >> 16) + (((ACC_AMT[127] >> 16) * TB_ACCVCA_GAIN) >> 15) + 64
VCA_LIM = (((2 ** 31 - 1) // AMP_MAX) << 6) - 64
# <<< CAL v6.7


# ---------------------------------------------------------------- v7.0: the TB-303 machine's SETUP page
# Six slots: WAVE (SAW SQR SAW+D SQR+D: the carrier names' four voices), GATE (OFF: the AMP decides, as v6.9;
# 303: the 303's own gate, 3.5 of the step's 6 clocks -- Whittle's slide page -- and held through a slide),
# FINE (+-50 cents, 64 = 0), SLID (the slide RC as dEVILish's SLID, 0 = the 303), DRIV (the output stage
# driven, 0 = the 303 .. +18 dB into its soft ceiling), ACCV (the accent's share on the VCA, 64 = the 303).
# A track without the machine (a TB303* sample) plays SETUP_NEUTRAL: v6.9 sample for sample.
SETUP_NAMES = ('WAVE', 'GATE', 'FINE', 'SLID', 'DRIV', 'ACCV')
SETUP_NEUTRAL = (0, 0, 64, 0, 0, 64)
SETUP_COUNT = (4, 2, 128, 128, 128, 128)
WAVE_LABELS = ('SAW', 'SQR', 'SAW+D', 'SQR+D')
GATE_LABELS = ('OFF', '303')
FINE_Q8 = 2                                   # Q8 semitones a FINE step: +-64 steps = +-0.5 semitone
DRV_DB = 18.0
DRV_IN = [int(round(OSAT_IN * 10 ** (DRV_DB * r / 127.0 / 20.0))) for r in range(128)]
DRV_LIM = [4 * ((2 ** 31 - 1) // v) - 4 for v in DRV_IN]           # (y >> 2) * DRV_IN fits 32 bits
assert DRV_IN[0] == OSAT_IN and DRV_LIM[0] == OSAT_LIM
# v7.0: CUT and ENV MOD glide to a new value (a p-lock, an LFO jump) in ~1 ms instead of stepping: the
# knobs' cutoff base and env depth, smoothed at the control rate (Q16 of the Q8-semitone domain)
SMOOTH_K = q15(onepole(0.001))

def _M(b, k):
    import numpy as np
    M = np.zeros((4, 4))
    for col in range(4):
        y = np.zeros(4); y[col] = 1
        y0 = -k * y[3]
        y1 = y[0] + 2 * b * (y0 - y[0] + y[1]); y2 = y[1] + b * (y1 - 2 * y[1] + y[2])
        y3 = y[2] + b * (y2 - 2 * y[2] + y[3]); y4 = y[3] + b * (y3 - 2 * y[3])
        M[:, col] = [y1, y2, y3, y4]
    return M
def _rho(b, k):
    import numpy as np
    return max(abs(np.linalg.eigvals(_M(b, k))))
def _kosc(b):
    lo, hi = 0.0, 400.0
    for _ in range(48):
        m = (lo + hi) / 2
        if _rho(b, m) >= 1: hi = m
        else: lo = m
    return lo
def _wres(b):
    import numpy as np
    ev = np.linalg.eigvals(_M(b, _kosc(b))); return abs(np.angle(ev[np.argmax(abs(ev))]))
def _solve_b(fc):
    lo, hi = 1e-6, 0.49
    for _ in range(40):
        m = (lo + hi) / 2
        if _wres(m) * FS / (2 * math.pi) < fc: lo = m
        else: hi = m
    return lo

def ladder_tables():
    n = S_MAX // 64 + 1
    B, K = [], []
    for i in range(n):
        fc = FC0 * 2 ** (i / 48)
        b = _solve_b(fc); k = _kosc(b)
        B.append(q15(b)); K.append(int(round(k * 256)))
    return B, K

_LC = _ladder_cache()
KD = [int(round(v * 256)) for v in _LC['KD']]                                  # Q8 feedback per dB/ms
_kr = _ixcurve('kr')
KF = [int(round(_LC['KO'][i] / (_LC['K'][i] / 256.0) * _kr[i])) for i in range(len(_kr))]   # Q12
_i0 = int(math.ceil(48 * math.log2(FKN_HZ[0] / FC0)))
KF = [KF[max(i, _i0)] for i in range(len(KF))]      # held below the first knot, as v6.7's KF

# gain compensation vs resonance (Q12): measured so a 110 Hz saw keeps its level within ~3 dB

# ---------------------------------------------------------------- dEVILish (v6.3): the Devil Fish, from an FX slot
# Robin Whittle, "User Manual for the Devil Fish mods to the TB-303" (2019), pp. 4-6, 8, 12-19, 24-25.
# A 303 track whose FX1 or FX2 is the dEVILish module (modules/devilish) reads these twelve knobs
# from that slot's two pages in the live lane (0x80000810 + 72*t: FX1 page 1 +18, FX2 +24, page 2
# +32 more; PARAM_PAGES.md 5a', 5b), locks applied; every other 303 track reads DF_NEUTRAL, which is
# v6.1.1 sample for sample ("Limiting the Devil Fish to TB-303 sounds", p. 8).
#  page 1, the knobs:   0 OVDR  1 FM   2 TRCK  3 VDEC  4 SLID  5 ADEC
#  page 2, the selects: 6 SATK  7 SWP  8 SPD   9 MUFF 10 CUTX 11 ENVX   (SATK a knob, the rest indices)
DF_NAMES = ('OVDR', 'FM', 'TRCK', 'VDEC', 'SLID', 'ADEC', 'SATK', 'SWP', 'SPD', 'MUFF', 'CUTX', 'ENVX')
DF_NEUTRAL = (25, 0, 0, 64, 0, 50, 0, 0, 1, 0, 0, 0)
DF_LABELS = {'SWP': ('ACID', 'WHST', 'SELF'), 'SPD': ('FAST', 'NORM', 'SLOW'),
             'MUFF': ('OFF', 'SOFT', 'HARD'), 'CUTX': ('OFF', 'ON'), 'ENVX': ('OFF', 'ON')}
# OVDR: the VCO into the ladder, none (0) .. normal (25) .. 66.6x normal (127)        [p. 4]
def _ovg(r): return r / 25.0 if r <= 25 else 66.6 ** ((r - 25) / 102.0)
# up to normal (raw <= 25) the v6.1 product exactly, Q15 (pre 7, post 8); above it Q10 (pre 6, post 4)
DF_GIN = [int(round(22938 * r / 25)) if r <= 25 else int(round(0.70 * _ovg(r) * 1024)) for r in range(128)]
DF_GIN_Q15 = 25                   # raw <= this: the Q15 path
# overdrive swamps the resonance, so TB_GCOMP's resonance part would lift the output and clip:
# gcomp = (base + resonance part * K1) * K2, K1 = G^-1.5, K2 = G^-0.3 (calibrated in v6.2), 1 for G <= 1
DF_OCOMP = [4096 if _ovg(r) <= 1 else int(round(4096 * _ovg(r) ** -1.5)) for r in range(128)]
DF_OGAIN = [4096 if _ovg(r) <= 1 else int(round(4096 * _ovg(r) ** -0.3)) for r in range(128)]
# FM: the VCA output (after the Muffler), AC coupled, moves the cutoff per sample           [p. 5, 18-19]
DF_FM_MUL = 96                    # fmq = raw*96: ((vca >> 8) * fmq) >> 12 Q8 st; 127 -> ~47 st at full level
# TRCK: LINEAR in Hz -- "the filter goes up ~2.7 kHz when the oscillator CV goes up an octave"
# at maximum; the zero point is the bottom C of the normal octave (here TUNE 0); a pot "made a
# little more linear" than log, so (raw/127)^1.5                                          [p. 5, 14]
DF_TRK_HZ = [int(round(2700.0 * (r / 127.0) ** 1.5)) for r in range(128)]            # Hz per octave
# VDEC: first half 16 ms .. the 303's long decay; second half that decay with a final level
# from silence (64) to full (127) -- "indefinitely long notes"                            [p. 4]
def _vtau(r): return 0.016 * (VEG_TAU / 0.016) ** (min(r, 64) / 64.0)   # v6.7: VEG_TAU at 64 (v6.6: 1.23 s)
DF_VEG = [q30(math.exp(-CS / (FS * _vtau(r)))) for r in range(128)]
DF_VSUS = [0 if r <= 64 else int(round((r - 64) / 63.0 * ONE30)) for r in range(128)]
# SLID: R = 103.3k (DAC + protection) + 0..500k pot on the 0.22 uF slide cap: 60 .. 360 ms  [p. 16]
DF_SLIDE = [q15(onepole(SLIDE_TAU * (103.3 + 500.0 * r / 127.0) / 103.3)) for r in range(128)]
# SWP: 2 ACID = sweep on, resonance normal; 1 WHST = sweep on, resonance doubled; 0 SELF =
# sweep circuit off (accents reach filter and VCA no more), resonance doubled             [p. 18]
DF_HIRES = 2                      # "double the usual feedback": self-oscillates at mid/high f (the 150 Hz loop HP)
# ADEC: the accented notes' MEG decay, 30 ms .. 3 s (-20 dB); 50 = the 303's fixed ~200 ms [p. 4]
DF_ADEC = [q30(math.exp(-CS / (FS * (0.03 * 100.0 ** (r / 127.0)) / math.log(10)))) for r in range(128)]
DF_ADEC[50] = TB_MEG_ACC              # neutral: the 303's own accent decay, exactly
# SATK: the VOLUME attack of non-accented notes (pp. 4, 24-25: Decay fully ACW with Soft Attack
# fully CW plays nothing). 0 = none, v6.1's instant attack; 1..127 = 90 % in 0.3 .. 30 ms
DF_SATK = [0] + [q30(1.0 - math.exp(-CS / (FS * 0.0003 * 100.0 ** ((r - 1) / 126.0) / math.log(10)))) for r in range(1, 128)]
DF_SATK[0] = TB_SATK                  # v6.7: SATK 0 = the 303's own attack (measured), not none
# SPD: sweep speed (v2.0+): FAST, NORM (the 303), SLOW ("much longer time constant ... can rise
# twice as high")                                                                         [p. 4-5]
# INTERPRETED: FAST = the capacitor read as a change (first accent strong, the next smaller),
# SLOW = charge and discharge 4x slower, the capacitor's sweep doubled
DF_SLOW_CH, DF_SLOW_DIS, DF_SLOW_G = 2, 4, 2      # SLOW: charge /CH, discharge /DIS, the capacitor's sweep x G
DF_FAST_G, DF_FAST_CH = 8, 64                       # FAST: max(0, vin - cap) * G / 16, the cap charging CH x faster
DF_ACH_SLOW = [a // DF_SLOW_CH for a in TB_ACH]
DF_DIS_SLOW = TB_DIS // DF_SLOW_DIS
DF_ACH_FAST = [min(a * DF_FAST_CH, 32767) for a in TB_ACH]
# MUFF: after the VCA; softens the loudest extremes, a square-wave clipping buzz, the bass passes;
# no effect at low level                                                                  [p. 6, 19]
# INTERPRETED: split at ~150 Hz; above it, mode 1 soft-clips and mode 2 hard-clips at DF_MUFF_T
DF_MUFF_LP = q15(onepole(1.0 / (2 * math.pi * 150.0), 1))
DF_MUFF_T = int(0.30 * (1 << 20))      # S20: the 303's normal peak at RES 0 is ~0.3 FS here
# CUTX: the cut-off pot's range, higher and lower, to ~5 kHz (an octave above the 303)      [p. 6]
DF_CUTX = [int(round(s_of_hz(157.0 * (4788.0 / 157.0) ** (r / 127)))) for r in range(128)]
# ENVX: the Env Mod pot's range tripled and including none                                [p. 6]
DF_ENVX_MUL = 3

DF_HZ = [int(round(FC0 * 2.0 ** (i * 64 / 3072.0))) for i in range(S_MAX // 64 + 1)]   # TRCK: Hz of a ladder index

# ---------------------------------------------------------------- distortion carriers (TB303D / TB303SQD)
# A fixed pedal after the VCA, as the London acid-techno records used: pre-gain, soft clip with a
# small asymmetry (even harmonics), 6 kHz tone lowpass.  The output highpass removes the bias DC.
DIST_GAIN = 5
DIST_BIAS = int(round(0.12 * (1 << 20)))
DIST_TONE = q15(onepole_hz(6000.0))

# the carrier's file name (after the last '/', case-insensitive) decides wave and pedal:
#   TB303*  saw     TB303SQ*  square     TB303D*  saw+pedal     TB303SQD*  square+pedal
# code = (dist << 1) | wave; not a TB303* name -> -1
def name_code(name):
    n = name.upper()
    if not n.startswith('TB303'): return -1
    n = n[5:]; wave = dist = 0
    if n.startswith('SQ'): wave = 1; n = n[2:]
    if n.startswith('D'): dist = 1
    return (dist << 1) | wave
