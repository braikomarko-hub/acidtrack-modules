"""DISTORX references.

1. `SD1` -- SUPER OD's float circuit (modules/superod/superod_ref.py), and
   `RATCircuit` -- the RAT's, in floating point, at any sample rate: the
   float references the module is MEASURED against (run at 8x and
   band-limited back, the ground truth for aliasing). Diode laws exact
   (Wright omega), every RC network the bilinear transform of the circuit's
   own, the LM308 an integrator of 0.8 MHz with its slew and its rails.

2. `fixed()` -- distorx.asm, instruction for instruction, in integers: the
   DSP56300's 24-bit words and 56-bit accumulators (mpy = 2xy, a move from an
   accumulator truncates a0 and limits, clb/normf and div as measured on the
   emulator). The gate requires the assembled code to match it BIT FOR BIT;
   the arithmetic is then judged against (1). With MODE on SD-1 it is
   SUPER OD's model, the MODE fade the one addition.

All take/return the OT's digital level (1.0 = 0 dBFS = 1 V at the jack).
"""
import importlib.util
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import toolpath  # noqa: E402,F401

_spec = importlib.util.spec_from_file_location("distorx_manifest", HERE / "manifest.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
FS = M.FS


# =============================================================================
# 1. the circuit, float
# =============================================================================
def wright_omega(U):
    """omega(U): w + ln w = U (scalar, Newton on w + ln w; exact to 1e-15)."""
    if U > 1.0:
        w = U - math.log(U)
    else:
        w = math.exp(U)
    for _ in range(50):
        f = w + math.log(w) - U
        w2 = w - f * w / (w + 1.0)
        if w2 <= 0:
            w2 = w / 2
        if abs(w2 - w) < 1e-16 * max(1.0, w):
            w = w2
            break
        w = w2
    return w


def diode_fb(i, rf):
    """v_f for a current i (amps) through Rf || D4 || (D5 + D6), exact."""
    if i == 0.0:
        return 0.0
    N = M.N2 if i > 0 else M.N1
    u = abs(i) * rf
    isr = M.IS * rf
    U = (u + isr) / N + math.log(isr / N)
    v = u + isr - N * wright_omega(U)
    return v if i > 0 else -v


def _bil1(b, a, fs):
    K = 2.0 * fs
    B0, B1 = b[0] + b[1] * K, b[0] - b[1] * K
    A0, A1 = a[0] + a[1] * K, a[0] - a[1] * K
    return B0 / A0, B1 / A0, A1 / A0


def tone_coefs(t, fs):
    """TONE's biquad (b0, b1, b2, a1, a2) at wiper t, by nodal analysis."""
    R = M.VR3
    Ra, Rb = t * R, (1.0 - t) * R
    tau4, tau6 = M.R7 * M.C4, M.R9 * M.C6
    p0, p1 = R, M.C5 * (Ra * Rb + R * M.R8)
    num = (p0, p1 + p0 * tau6 + M.C5 * M.R9 * Ra, p1 * tau6)
    den = (p0, p1 + p0 * tau4 + M.R7 * M.C5 * Rb, p1 * tau4)
    K = 2.0 * fs

    def z(c):
        return (c[0] + c[1] * K + c[2] * K * K, 2 * c[0] - 2 * c[2] * K * K,
                c[0] - c[1] * K + c[2] * K * K)
    B, A = z(num), z(den)
    return B[0] / A[0], B[1] / A[0], B[2] / A[0], A[1] / A[0], A[2] / A[0]


def knob(v):
    """A page-1 knob (0..127, may be fractional) -> 0..1 as the module reads it."""
    return min(v / 127.0, 1.0)


class SD1:
    """The pedal. Knobs as the OT shows them (0..127); IN in dB around 64."""

    def __init__(self, fs=FS, LEVL=64, TONE=64, DRIV=64, IN=64, MIX=127, mono=True):
        self.fs = fs
        self.rf = M.R5 + knob(DRIV) * M.VR1
        self.lv = knob(LEVL) * M.VR2 / (M.R10 + M.VR2) * M.MAKEUP
        self.gin = 2.0 ** ((IN - 64) / 32.0)
        self.mix = min(MIX / 128.0, 1.0) if MIX < 127 else 1.0
        hp = lambda tau: _bil1((0.0, tau), (1.0, tau), fs)
        self.h1, self.h2, self.h3 = hp(M.R2 * M.C1), hp(M.R4 * M.C2), hp(M.R6 * M.C3)
        self.h4 = hp((M.R10 + M.VR2) * M.C7)
        self.l6 = _bil1((1.0, 0.0), (1.0, M.R9 * M.C6), fs)
        self.bq = tone_coefs(M.tone_taper(knob(TONE)), fs)

    def pedal(self, vin):
        """volts in -> volts out (before LEVEL), sample by sample."""
        (c1, d1, a1), (c2, d2, a2), (c3, d3, a3) = self.h1, self.h2, self.h3
        b0, b1, b2, ta1, ta2 = self.bq
        l0, l1, la = self.l6
        rail = M.RAIL
        s = [0.0] * 12
        out = np.empty(len(vin))
        for n, x in enumerate(vin):
            y1 = c1 * x + d1 * s[0] - a1 * s[1]; s[0], s[1] = x, y1
            vp = c2 * y1 + d2 * s[2] - a2 * s[3]; s[2], s[3] = y1, vp
            h = c3 * vp + d3 * s[4] - a3 * s[5]; s[4], s[5] = vp, h
            o1 = min(max(vp + diode_fb(h / M.R6, self.rf), -rail), rail)
            t = b0 * o1 + b1 * s[6] + b2 * s[7] - ta1 * s[8] - ta2 * s[9]
            s[7], s[6], s[9], s[8] = s[6], o1, s[8], t
            o2 = l0 * t + l1 * s[10] - la * s[11]; s[10], s[11] = t, o2
            out[n] = min(max(o2, -rail), rail)
        c4, d4, a4 = self.h4
        y = np.empty_like(out)
        x1 = y1 = 0.0
        for n, x in enumerate(out):
            y1 = c4 * x + d4 * x1 - a4 * y1
            x1 = x
            y[n] = y1
        return y

    def run(self, L, R):
        vin = (np.asarray(L) + np.asarray(R)) / 2 * self.gin
        wet = self.pedal(vin) * self.lv
        return (np.asarray(L) + self.mix * (wet - L),
                np.asarray(R) + self.mix * (wet - R))


def run_oversampled(L, R, os_factor=8, **knobs):
    """Ground truth: the same circuit at os_factor x FS, band-limited back.
    The 2x halfbands' 5-sample delay is NOT applied here. Needs scipy (an
    analysis tool, not a gate)."""
    from scipy.signal import resample_poly
    p = SD1(FS * os_factor, **knobs)
    vin = (np.asarray(L) + np.asarray(R)) / 2 * p.gin
    y = resample_poly(p.pedal(resample_poly(vin, os_factor, 1)), 1, os_factor)
    return y * p.lv


# =============================================================================
# 2. the module, bit for bit
# =============================================================================
W56 = 1 << 56
H47 = 1 << 47


def _w56(v):
    v %= W56
    return v - W56 if v >= (1 << 55) else v


def s24(v):
    v &= 0xFFFFFF
    return v - (1 << 24) if v & 0x800000 else v


def lim(A):
    """move a,reg / move a,x:: a1 with limiting (a0 dropped, i.e. floor)."""
    if A >= H47:
        return 0x7FFFFF
    if A < -H47:
        return -0x800000
    return A >> 24


def a1(A):
    """move a1,...: the middle word, no limiting."""
    return s24(A >> 24)


def a0(A):
    return A & 0xFFFFFF


def acc(r):
    """a register (24-bit signed) into an accumulator: a1 = r, a0 = 0."""
    return r << 24


def mpy(x, y):
    return 2 * x * y


def and_imm(A, imm):
    """and #imm,a: a1 &= imm; a2 and a0 untouched."""
    a2 = A >> 48
    return _w56((a2 << 48) | (((A >> 24) & 0xFFFFFF & imm) << 24) | (A & 0xFFFFFF))


def add_imm(A, imm):
    return _w56(A + (s24(imm) << 24))


def clb_normf(A):
    """clb a,b + normf b1,a on a positive value below 1.0 (measured)."""
    x = A
    e = 0
    # e = floor(log2(x / 2^47)) + 1, x shifted left by -e
    while x < (1 << 46):
        x <<= 1
        e -= 1
    return e, x


Q = M.CONSTQ
C = {k: s24(v) for k, v in Q.items() if not k.endswith("_AT") and k not in ("MK_AT6", "OMB")}
C["NRAIL"] = -C["RAIL"]
PT = [s24(v) for v in M.PTABLE]


def _interp(base, A_u, shift_idx, frac_mask, frac_shift):
    """transient's interpolation: idx = a1(u) >> shift, frac = (u & mask) << s."""
    u = a1(A_u)
    idx = u >> shift_idx
    frac = lim(acc(u & frac_mask) << frac_shift)
    t0, t1 = PT[base + idx], PT[base + idx + 1]
    d = lim(acc(t1) - acc(t0))
    return acc(t0) + mpy(frac, d)


def block_constants(kn):
    """The per-block decode, from the five page-1 knob WORDS (value << 16 | frac)."""
    st = {}
    w = lambda k: kn[k] & 0x7FFFFF
    # IN
    A = acc(w(3))
    idx = a1(A) >> 18
    frac = lim(acc(w(3) & 0x3FFFF) << 5)
    t0, t1 = PT[Q["EXP_AT"] + idx], PT[Q["EXP_AT"] + idx + 1]
    st["Gi"] = lim(acc(t0) + mpy(frac, lim(acc(t1) - acc(t0))))

    def stretch(word):
        return lim(acc(word) + mpy(word, C["STRETCH"]))
    # DRIV
    x = stretch(w(2))
    rfs = lim(acc(C["R5S"]) + mpy(x, C["V1S"]))
    A = mpy(rfs, C["KG2"])
    st["G2"] = lim(A)
    st["G1"] = lim(A << 1)
    k2 = lim(mpy(rfs, C["KK"]))
    e, mA = clb_normf(acc(rfs))
    A = mA - acc(0x400000)
    A = A << 1
    u = a1(A)
    idx = u >> 17
    frac = lim(acc(u & 0x1FFFF) << 6)
    t0, t1 = PT[Q["LN_AT"] + idx], PT[Q["LN_AT"] + idx + 1]
    lnm = lim(acc(t0) + mpy(frac, lim(acc(t1) - acc(t0))))
    B = acc(e) << 18
    B = mpy(lim(B), C["LN2"]) << 1
    B = B + acc(lnm)
    B = add_imm(B, Q["K0"])
    lk2 = lim(B)
    lk1 = lim(add_imm(acc(lk2), Q["LN2_16"]))
    for side, lk, ksh in (("2", lk2, 15), ("1", lk1, 14)):
        A = acc(lk) >> 11
        B = acc(k2) >> ksh
        A = add_imm(A + B, 0x000800)
        st["C" + side] = (a1(A), a0(A))
    st["A2"], st["A1"] = C["A2"], C["A1"]
    st["B2"] = lim(-mpy(lk2, C["A2"]))
    st["B1"] = lim(-mpy(lk1, C["A1"]))
    # TONE
    x = stretch(w(1))
    A = acc(x) - acc(0x400000)
    d = lim(A)
    y1 = lim(mpy(d, d))
    B = mpy(C["TAPB"], y1)
    B = add_imm(B, Q["TAPA"])
    y1 = lim(B)
    B = mpy(d, y1)
    B = add_imm(B, 0x200000)
    t = lim(B << 1)
    poly = {}
    for nm in ("B0", "B1", "B2", "A1", "A2", "A0"):
        A = mpy(C[f"T{nm}P2"], t)
        A = add_imm(A, Q[f"T{nm}P1"])
        A = mpy(lim(A), t)
        A = add_imm(A, Q[f"T{nm}P0"])
        poly[nm] = lim(A)
    q = (0x020000 << 23) // poly["A0"]          # div, measured
    st["b0"] = lim(mpy(poly["B0"], q) << 5)
    st["b1"] = lim(mpy(poly["B1"], q) << 5)
    st["b2"] = lim(mpy(poly["B2"], q) << 5)
    st["na1"] = lim(-mpy(poly["A1"], q) << 5)
    st["na2"] = lim(-mpy(poly["A2"], q) << 5)
    # LEVL
    st["GL"] = lim(mpy(stretch(w(0)), C["LVL8"]))
    # MIX
    m = kn[4] & 0x7F0000
    st["mix"] = 0x7FFFFF if m == 0x7F0000 else m
    return st


def nl(z, st):
    """sod_nl, bit for bit."""
    side = "2" if z >= 0 else "1"
    a = abs(acc(z))
    x0 = lim(a)
    G = st["G" + side]
    chi, clo = st["C" + side]
    A = (chi << 24) | clo
    A = A + mpy(x0, G)
    e, A = clb_normf(A)
    A = A - acc(0x400000)
    A = A << 1
    u = a1(A)
    seg = u >> 19
    point = e * 16 + 224 + seg
    frac = lim(acc(u & 0x7FFFF) << 4)
    t0, t1 = PT[point], PT[point + 1]
    A = acc(t0) + mpy(frac, lim(acc(t1) - acc(t0)))
    A = acc(st["B" + side]) + mpy(lim(A), st["A" + side])
    v = lim(A)
    nv = lim(-A)
    return acc(nv) if z < 0 else A




# =============================================================================
# 1b. the RAT, float
# =============================================================================
RAT = M.RAT


class RATCircuit:
    """The RAT (MODE 1) or the Turbo RAT (MODE 2), knobs as the OT shows them
    (0..127). The pots follow the A law exactly (the module interpolates it
    from 33 points); FILTER is turned round like the module's TONE."""

    def __init__(self, fs=FS, mode=1, LEVL=64, TONE=64, DRIV=64, IN=64, MIX=127, ft=None):
        self.fs = fs
        T = 1.0 / fs
        K = 2.0 * fs
        Rd = RAT.RDIST * M.taperA(knob(DRIV))
        Rt = RAT.RTONE * M.taperA(1.0 - knob(TONE))
        Is, n = M.DIODE[mode]
        self.N = n * M.VT
        self.Is = Is
        Rc5, Rc6 = T / (2 * RAT.C5), T / (2 * RAT.C6)
        g4, g5 = 1 / (RAT.R4 + Rc5), 1 / (RAT.R5 + Rc6)
        Gg = g4 + g5
        self.lam = g4 / Gg
        self.k5, self.k6 = 2 * Rc5 * g4, 2 * Rc6 * g5
        P = 1 + Rd * Gg                   # C4 left out (README): Zf = Rd
        self.q = 1 / P
        W = 2 * math.pi * (ft or RAT.FT) * T
        th = max(0.5, 1 / (1 + RAT.THETA_C) - P / W)
        r = P / (P + th * W)
        self.c_vo, self.c_d1, self.c_e = r, (1 - th) * r, th * W * r
        self.W, self.SRT, self.VS = W, RAT.SR * T, RAT.VSAT
        Rc7 = T / (2 * RAT.C7)
        R6p = RAT.R6 + Rc7
        self.k7 = 2 * Rc7 / R6p
        Rc8, Rc9 = T / (2 * RAT.C8), T / (2 * RAT.C9)
        R89 = RAT.R8 + Rc9
        Rtp = Rt + RAT.R7
        G8x = 1 / Rc8 + 1 / R89
        self.aD = 1 / (1 + Rtp * G8x)
        self.a8, self.a9 = Rtp / Rc8 * self.aD, Rtp / R89 * self.aD
        self.rho = 1 / (1 + R6p * G8x * self.aD)
        Rp = self.rho * R6p
        self.s8, self.s9 = Rp * self.aD / Rc8, Rp * self.aD / R89
        self.k = Is * Rp / self.N
        self.k9, self.gr8 = 2 * Rc9 / R89, RAT.R8 / R89
        tau = RAT.R2 * RAT.C1
        self.hp1 = (K * tau / (1 + K * tau), -(1 - K * tau) / (1 + K * tau))
        tau = RAT.C10 * RAT.RVOL
        self.hpo = (K * tau / (1 + K * tau), -(1 - K * tau) / (1 + K * tau))
        self.lv = knob(LEVL) * M.MAKEUP_RAT[mode]
        self.gin = 2.0 ** ((IN - 64) / 32.0)
        self.mix = min(MIX / 128.0, 1.0) if MIX < 127 else 1.0
        self.reset()

    def reset(self):
        self.vo = self.d1 = 0.0
        self.vh5 = self.vh6 = self.vh7 = self.vh8 = self.vh9 = 0.0

    def diode(self, u):
        a = abs(u)
        U = a / self.N + self.k + math.log(self.k)
        v = a + self.N * self.k - self.N * wright_omega(U)
        return v if u >= 0 else -v

    def core(self, vp):
        """one sample of the LM308 stage and the clipper node: vp -> the gate"""
        Hn = self.lam * self.vh5 + (1 - self.lam) * self.vh6
        c0 = (1 - self.q) * Hn
        vo = self.c_vo * self.vo + self.c_d1 * self.d1 + self.c_e * (vp - c0)
        vo = min(max(vo, self.vo - self.SRT), self.vo + self.SRT)
        vo = min(max(vo, -self.VS), self.VS)
        vm = self.q * vo + c0
        self.d1 = min(max(self.W * (vp - vm), -self.SRT), self.SRT)
        self.vh5 += self.k5 * (vm - self.vh5)
        self.vh6 += self.k6 * (vm - self.vh6)
        self.vo = vo
        vs = vo - self.vh7
        u = self.rho * vs + self.s8 * self.vh8 + self.s9 * self.vh9
        v = self.diode(u)
        self.vh7 += self.k7 * (vs - v)
        vX = self.aD * v + self.a8 * self.vh8 + self.a9 * self.vh9
        self.vh8 = 2 * vX - self.vh8
        g = self.gr8 * (vX - self.vh9)
        self.vh9 += self.k9 * (vX - self.vh9)
        return g

    def pedal(self, vin):
        """volts in -> volts out (before LEVEL), every stage at this object's fs"""
        c, p = self.hp1
        hc, hp = self.hpo
        out = np.empty(len(vin))
        x1 = y1 = g1 = o = 0.0
        for n, x in enumerate(vin):
            y1 = c * (x - x1) + p * y1
            x1 = x
            g = self.core(y1)
            o = hc * (g - g1) + hp * o
            g1 = g
            out[n] = o
        return out

    def run(self, L, R):
        vin = (np.asarray(L) + np.asarray(R)) / 2 * self.gin
        wet = self.pedal(vin) * self.lv
        return (np.asarray(L) + self.mix * (wet - L),
                np.asarray(R) + self.mix * (wet - R))


def rat_module_float(L, R, mode=1, **knobs):
    """The module's own structure in float: the input HP, the core and the
    output HP, all at 1x, which is the circuit above at FS. (Until
    15 Oct 2026 the core ran at 2x through the SD-1's halfbands.)"""
    return RATCircuit(FS, mode, **knobs).run(L, R)


def rat_oversampled(L, R, mode=1, os_factor=8, **knobs):
    """Ground truth: the whole RAT at os_factor x FS, band-limited back."""
    from scipy.signal import resample_poly
    m = RATCircuit(FS * os_factor, mode, **knobs)
    vin = (np.asarray(L, float) + np.asarray(R, float)) / 2 * m.gin
    return resample_poly(m.pedal(resample_poly(vin, os_factor, 1)), 1, os_factor) * m.lv


# =============================================================================
# 2b. the module, bit for bit
# =============================================================================
def asl(A, n):
    return _w56(A << n)


def lt(A, B):
    return A < B


def _tab(base, u, shift_idx, frac_mask, frac_shift):
    """the table interpolation every block uses: u a word, idx = u >> shift,
    frac = (u & mask) << shift2 (limited), t0 + frac (t1 - t0)."""
    idx = u >> shift_idx
    frac = lim(acc(u & frac_mask) << frac_shift)
    t0, t1 = PT[base + idx], PT[base + idx + 1]
    return acc(t0) + mpy(frac, lim(acc(t1) - acc(t0)))


def div24(num, den):
    """andi #$fe,ccr / rep #$18 / div x0,a / move a0,y1, 0 <= num < den"""
    return (num << 23) // den


def stretch(word):
    return lim(acc(word) + mpy(word, C["STRETCH"]))


def rat_block(X, kn, mode):
    """the RAT's per-block decode into the r7 slots X (a list of 64 words)"""
    base = Q["MK_AT"] if mode == 1 else Q["MK_AT6"]
    X[0x0a], X[0x0e], X[0x1b], X[0x1c], X[0x0d], X[0x10] = PT[base:base + 6]
    # DISTORTION
    T = lim(_tab(Q["TAP_AT"], stretch(kn[2] & 0x7FFFFF), 18, 0x3FFFF, 5))
    P = lim(add_imm(mpy(T, C["RPG"]), 0x000800))
    X[0x14] = P
    X[0x01] = div24(0x000400, P)
    q = lim(asl(acc(X[0x01]), 1))
    X[0x01] = q
    q1 = lim(acc(0x7FFFFF) - acc(q))
    X[0x02] = lim(mpy(q1, C["RLAM"]))
    X[0x03] = lim(mpy(q1, C["RLAM1"]))
    B = asl(mpy(P, C["RPW"]), 7)
    A = acc(C["RTH0"]) - B
    if A < acc(0x400000):
        A = acc(0x400000)
    th = lim(A)
    X[0x15] = th
    den = lim(mpy(th, C["RW4K"]) + acc(P))
    r = div24(P, den)
    X[0x04] = r
    X[0x05] = lim(acc(r) - mpy(th, r))
    X[0x06] = lim(mpy(lim(mpy(th, C["RW128"])), r))
    X[0x04] = lim(acc(r) - acc(0x400000) - acc(0x400000))
    # FILTER
    xt = stretch(kn[1] & 0x7FFFFF)
    T = lim(_tab(Q["TAP_AT"], lim(acc(0x7FFFFF) - acc(xt)), 18, 0x3FFFF, 5))
    X[0x14] = T
    den = lim(add_imm(mpy(T, C["RTGT"]), Q["RTG0"]))
    aD = div24(0x020000, den)
    X[0x0f] = aD
    X[0x13] = lim(mpy(lim(add_imm(mpy(T, C["RT9T"]), Q["RT97"])), aD))
    X[0x12] = lim(asl(mpy(lim(add_imm(mpy(T, C["RTCT"]), Q["RTC7"])), aD), 6))
    den = lim(add_imm(mpy(aD, C["RRG"]), 0x400000))
    rho = div24(0x400000, den)
    X[0x07] = rho
    ra = lim(mpy(aD, rho))
    X[0x08] = lim(mpy(ra, C["RSC8"]))
    X[0x09] = lim(mpy(ra, C["RSC9"]))
    X[0x0d] = lim(mpy(rho, X[0x0d]))
    u = a1(asl(acc(rho) - acc(0x400000), 1))
    lnr = lim(_tab(Q["LN_AT"], u, 17, 0x1FFFF, 6))
    A = (acc(lnr) >> 4) + acc(X[0x1b]) + mpy(rho, X[0x1c])
    X[0x0b], X[0x0c] = a1(A), a0(A)
    # LEVEL
    X[0x10] = lim(mpy(stretch(kn[0] & 0x7FFFFF), X[0x10]))


def rat_core(X, z):
    """dtx_core, bit for bit: z a word (volts/4); returns the accumulator g.
    X holds the module's r7 words by name-free index (see the template)."""
    A = mpy(X[0x28], X[0x02]) + mpy(X[0x2a], X[0x03])
    c0 = a1(A)                                   # move a1,b: |c0| < 1
    A = asl(mpy(lim((acc(z) - acc(c0)) >> 1), X[0x06]), 8)
    A = A + mpy(X[0x1e], X[0x04]) + mpy(X[0x1f], X[0x05])
    A >>= 1                                      # asr #1: the step at volts/8
    if A > acc(C["RSRT8"]):
        A = acc(C["RSRT8"])
    if A < acc(C["RNSRT8"]):
        A = acc(C["RNSRT8"])
    A = asl(A, 1)
    A = A + acc(X[0x1e])
    if A > acc(C["RVSAT"]):
        A = acc(C["RVSAT"])
    if A < acc(C["RNVSAT"]):
        A = acc(C["RNVSAT"])
    vo = lim(A)
    X[0x1e] = vo
    vm = lim(mpy(vo, X[0x01]) + acc(c0))
    X[0x1b] = vm
    X[0x1f] = lim(asl(mpy(lim((acc(z) - acc(vm)) >> 1), C["RW128"]), 8))
    for hi_, lo_, k in ((0x28, 0x29, "RK5"), (0x2a, 0x2b, "RK6")):
        d = lim(acc(vm) - acc(X[hi_]))
        A = ((X[hi_] << 24) | X[lo_]) + mpy(d, C[k])
        X[hi_], X[lo_] = a1(A), a0(A)
    # the clipper node
    vs = lim((acc(vo) >> 1) - acc(X[0x2c]))
    X[0x1d] = vs
    Au = mpy(vs, X[0x07]) + mpy(X[0x2e], X[0x08]) + mpy(X[0x32], X[0x09])
    uw = lim(Au)
    X[0x1c] = uw
    au = lim(abs(Au))
    A = ((X[0x0b] << 24) | X[0x0c]) + mpy(au, X[0x0a])
    if A < acc(0x008000):
        A = acc(0x008000)
    if A > acc(0x3FFFFF):
        A = acc(0x3FFFFF)
    e, A = clb_normf(A)
    A = asl(A - acc(0x400000), 1)
    u = a1(A)
    seg = u >> 19
    point = e * 16 + Q["OMB"] + seg
    frac = lim(acc(u & 0x7FFFF) << 4)
    t0, t1 = PT[point], PT[point + 1]
    om = lim(acc(t0) + mpy(frac, lim(acc(t1) - acc(t0))))
    B = asl(mpy(om, X[0x0e]), 1)
    A = acc(X[0x0d]) - B
    D, nD = lim(A), lim(-A)
    v = lim(acc(nD if uw < 0 else D) + acc(uw))
    X[0x1c] = v
    d = lim((acc(vs) - acc(v)) >> 1)
    A = ((X[0x2c] << 24) | X[0x2d]) + mpy(d, C["RK7X2"])
    X[0x2c], X[0x2d] = a1(A), a0(A)
    A = mpy(v, X[0x0f]) + mpy(X[0x2e], X[0x12]) + mpy(X[0x32], X[0x13])
    vX = lim(A)
    X[0x2e] = lim(asl(A, 1) - acc(X[0x2e]))
    dX = lim(acc(vX) - acc(X[0x32]))
    A = ((X[0x32] << 24) | X[0x33]) + mpy(dX, C["RK9"])
    X[0x32], X[0x33] = a1(A), a0(A)
    return mpy(dX, C["RGR8"])


def _sd1_state():
    S = {k: 0 for k in ("vin1", "y11", "o1a", "o1b", "ta", "tb", "o2", "o2c", "o3", "o3lo")}
    S["h"] = [0] * 5
    S["vp"] = [0] * 5
    S["w0"] = [0] * 5
    S["w1"] = [0] * 3
    return S


def _fade(F, mix):
    """MIX x (1 + d), then d one step on, clamped to [-1, 0]"""
    m = lim(acc(mix) + mpy(F["d"], mix))
    A = acc(F["d"]) + acc(F["step"])
    if A > 0:
        A = 0
    if A < acc(-0x800000):
        A = acc(-0x800000)
    F["d"] = lim(A)
    return m


def _mix_out(wet, d_, m):
    A = (acc(wet) - acc(d_)) >> 1
    A = (mpy(lim(A), m) << 1) + acc(d_)
    return lim(A)


def fixed(Lq, Rq, knob_words_per_block, frames=16, state=None, split=0):
    """Bit-exact render. Lq, Rq: 24-bit ints. knob_words_per_block: a list
    (one per block) of six knob words, or a single list for every block.
    split: the dispatcher's a=0 sub-block call of `split` frames, then the
    rest (two proc calls per block). Returns (Lout, Rout, state)."""
    Lq = [int(v) for v in Lq]
    Rq = [int(v) for v in Rq]
    n = len(Lq)
    if state is None:
        state = {"cur": 0, "d": -0x800000, "step": 0, "S": _sd1_state(), "X": [0] * 64}   # v8: OFF
    F = state
    S, X = F["S"], F["X"]
    outL, outR = [0] * n, [0] * n
    per_block = isinstance(knob_words_per_block[0], (list, tuple))
    calls = []
    for b0 in range(0, n, frames):
        kn = knob_words_per_block[b0 // frames] if per_block else knob_words_per_block
        e = min(n, b0 + frames)
        if 0 < split < frames and b0 + split < e:
            calls += [(b0, b0 + split, kn), (b0 + split, e, kn)]
        else:
            calls.append((b0, e, kn))
    for (i0, i1, kn) in calls:
        # ---- MODE: the knob's pedal, the switch at the bottom of the fade
        A = and_imm(acc(kn[5]), 0x7F0000)
        if A > acc(0x030000):                    # v8: 0 OFF 1 SD-1 2 RAT 3 TURBO
            A = acc(0x030000)
        mk = a1(A)
        if F["d"] == -0x800000 and F["cur"] != mk:
            S.clear()
            S.update(_sd1_state())
            for k in range(0x12, 0x3D):
                X[k] = 0
            F["cur"] = mk
        F["step"] = 0x010000 if F["cur"] == mk else -0x010000
        if F["cur"] == 0:                            # v8: OFF -- nothing runs, the frames pass
            for i in range(i0, i1):
                outL[i], outR[i] = Lq[i], Rq[i]
            continue
        # v8: a settled block (d = 0, the knob's pedal on, MIX 127): the wet alone
        F["fast"] = block_mix(kn) == 0x7FFFFF and F["d"] == 0 and F["step"] > 0
        if F["cur"] == 0x010000:
            st = block_constants(kn[:5])
            for i in range(i0, i1):
                _sd1_sample(S, st, F, Lq, Rq, outL, outR, i)
        else:
            mode = 2 if F["cur"] == 0x030000 else 1
            X[0x00] = block_constants_in(kn)
            X[0x11] = block_mix(kn)
            rat_block(X, kn, mode)
            for i in range(i0, i1):
                _rat_sample(X, F, Lq, Rq, outL, outR, i)
    return outL, outR, F


def block_constants_in(kn):
    w3 = kn[3] & 0x7FFFFF
    idx = a1(acc(w3)) >> 18
    frac = lim(acc(w3 & 0x3FFFF) << 5)
    t0, t1 = PT[Q["EXP_AT"] + idx], PT[Q["EXP_AT"] + idx + 1]
    return lim(acc(t0) + mpy(frac, lim(acc(t1) - acc(t0))))


def block_mix(kn):
    m = kn[4] & 0x7F0000
    return 0x7FFFFF if m == 0x7F0000 else m


def _rat_sample(X, F, Lq, Rq, outL, outR, i):
    A = (acc(Lq[i]) + acc(Rq[i])) >> 1
    vin = lim(mpy(lim(A), X[0x00]))
    A = (X[0x35] << 24) | X[0x36]
    A = A - mpy(X[0x35], C["RHPQ"]) - mpy(X[0x34], C["RHPC"]) + mpy(vin, C["RHPC"])
    X[0x34] = vin
    X[0x35], X[0x36] = a1(A), a0(A)
    vp = lim(A)
    g = lim(rat_core(X, vp))                     # at 1x (2x until 15 Oct 2026)
    A = (X[0x37] << 24) | X[0x38]
    A = A - mpy(X[0x37], C["RHOQ"]) - mpy(X[0x3a], C["RHOH"]) + mpy(g, C["RHOH"])
    X[0x3a] = g
    X[0x37], X[0x38] = a1(A), a0(A)
    wet = lim(mpy(lim(A), X[0x10]) << 4)
    if F.get("fast"):
        outL[i] = outR[i] = wet
        return
    m = _fade(F, X[0x11])
    outL[i] = _mix_out(wet, Lq[i], m)
    outR[i] = _mix_out(wet, Rq[i], m)


def _sd1_sample(S, st, F, Lq, Rq, outL, outR, i):
    """SUPER OD's per-sample code (superod_ref.fixed), the MIX through the fade"""
    A = acc(Lq[i]) + acc(Rq[i])
    A >>= 1
    vin = lim(mpy(lim(A), st["Gi"]))
    A = mpy(vin, C["HP1C"]) - mpy(S["vin1"], C["HP1C"]) + mpy(S["y11"], C["HP1P"])
    S["vin1"] = vin
    y1 = lim(A)
    y1old = S["y11"]
    S["y11"] = y1
    A = -mpy(y1old, C["HP2C"]) + mpy(y1, C["HP2C"]) + mpy(S["vp"][0], C["HP2P"])
    vp = lim(A)
    vp1 = S["vp"][0]
    A = -mpy(vp1, C["HP3C"]) + mpy(vp, C["HP3C"]) + mpy(S["h"][0], C["HP3P"])
    S["vp"] = [vp] + S["vp"][:4]
    h = lim(A)
    S["h"] = [h] + S["h"][:4]
    # v8: at 1x (2x through the halfbands, vp delayed 5 to match, until 18 Oct 2026)
    A = acc(lim(nl(h, st))) + acc(vp)
    if A > acc(C["RAIL"]):
        A = acc(C["RAIL"])
    if A < acc(C["NRAIL"]):
        A = acc(C["NRAIL"])
    o1 = lim(A)
    A = (mpy(o1, st["b0"]) + mpy(S["o1b"], st["b2"]) + mpy(S["o1a"], st["b1"])
         + mpy(S["tb"], st["na2"]) + mpy(S["ta"], st["na1"]))
    S["o1b"], S["o1a"] = S["o1a"], o1
    told = S["ta"]
    S["tb"] = told
    t = lim(A << 1)
    S["ta"] = t
    A = mpy(told, C["LP6L"]) + mpy(t, C["LP6L"]) + mpy(S["o2"], C["LP6P"])
    S["o2"] = lim(A)
    if A > acc(C["RAIL"]):
        A = acc(C["RAIL"])
    if A < acc(C["NRAIL"]):
        A = acc(C["NRAIL"])
    o2c = lim(A)
    A = (S["o3"] << 24) | S["o3lo"]
    A = A - mpy(S["o3"], C["HP4Q"]) - mpy(S["o2c"], C["HP4H"]) + mpy(o2c, C["HP4H"])
    S["o2c"] = o2c
    S["o3"], S["o3lo"] = a1(A), a0(A)
    wet = lim(mpy(lim(A), st["GL"]) << 4)
    if F.get("fast"):
        outL[i] = outR[i] = wet
        return
    m = _fade(F, st["mix"])
    outL[i] = _mix_out(wet, Lq[i], m)
    outR[i] = _mix_out(wet, Rq[i], m)


def knob_words(LEVL=64, TONE=64, DRIV=64, IN=64, MIX=127, MODE=1, frac=0):
    return [((v & 0x7F) << 16) | ((frac & 0xFF) << 8) for v in (LEVL, TONE, DRIV, IN, MIX, MODE)]
