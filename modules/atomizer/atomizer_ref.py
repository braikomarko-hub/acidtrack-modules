"""AtoMizer -- the golden reference: the integer arithmetic of atomizer.asm, in Python.

Every helper is one DSP56300 idiom and every line of `AtoMizer.call` is a line (or a few) of
atomizer.asm, in the same order; tools/verify/verify_atomizer.py requires dsp_host's output to be
BIT-IDENTICAL to this model.

Behaviour (after the Red Panda Particle V1, read from the Particle 2 owner's manual 2.2 and its
public changelog; no Red Panda code): a ring of the track's mono sum, two grain voices reading it
through a linear-interpolated Q9 position and a trapezoid window, the voices panned by SPRD.
"""

M24 = 0xFFFFFF
FS = 0x7FFFFF
N0, N1 = 15779, 8192            # the ring: RCYC's 15,779 words (+$0000..$3da2), the others' 8,192
AUX = 7587                      # layout 1's aux, +$2000..$3da2
AUXB = 0x2000
PING = 3793                     # PING: two lines of 3,793
LSMAX = 7552                    # the REP slot's ceiling (the aux holds one slot)

CHOP_HT = (3, 4, 6, 8, 12, 16, 24, 48)        # SYNC: CHOP's divisions, half MIDI ticks: 1/64 .. 1/4
TIME_HT = (3, 6, 9, 12, 18, 24, 36, 48)       # SYNC: TIME's: 1/64 1/32 3/64 1/16 3/32 1/8 3/16 1/4
EXP = tuple(round(512 * 2 ** (i / 12)) for i in range(-12, 14))   # Q9 increments, -12 .. +13 semitones


# ---- the DSP56300's words and accumulators -------------------------------------------------
def sx(w):
    w &= M24
    return w - (1 << 24) if w & 0x800000 else w


def acc(v):
    v &= (1 << 56) - 1
    return v - (1 << 56) if v >> 55 else v


def ld(w):                       # move w,a: a1 = w, a0 = 0, a2 = the sign
    return sx(w) << 24


def lim(a):                      # move a,x0 / move a,x:(..): the limiter
    if a >= (1 << 47):
        return FS
    if a < -(1 << 47):
        return -(1 << 23)
    return sx(a >> 24)


def a1(a):                       # move a1,x0: no limiting
    return sx(a >> 24)


def a0(a):                       # move a0,x0
    return a & M24


def mpy(x, y):                   # mpy x,y,a: 2xy
    return acc(2 * sx(x) * sx(y))


def mac(a, x, y):                # mac x,y,a
    return acc(a + 2 * sx(x) * sx(y))


def lcg(seed):                   # BBD's: seed 1664525 + 1013904223 (mod 2^24)
    return (seed * 1664525 + 1013904223) & M24


def q4_of(t24):                  # samples per MIDI tick, Q4 (BusDelay's doubled dividend)
    return 14700 if t24 == 0 else 42336000 // t24


def du_of(L):                    # 2^23 / L
    return (1 << 23) // L


class AtoMizer:
    """One instance: `s` is its r7 block, `y` its Y slot (indices relative to the allocator's base)."""

    def __init__(self):
        self.s = [0] * 0x60
        self.y = [0] * 0x3E00
        self.s[0x01] = 0x3E
        self.s[0x03] = 0x5A5A5B

    # ---- the block --------------------------------------------------------------------------
    def call(self, knobs, frames, tempo24=0):
        """One proc call: knobs = twelve values 0..127 (selects as their index); frames = list of
        (L, R) 24-bit words. Returns the output frames."""
        s, y = self.s, self.y
        k = list(knobs) + [0] * (12 - len(knobs))
        mode = (k[6] & 7) << 16
        s[0x38] = mode
        auto = 0x010000 if mode == 0 else 0
        fbm = ((k[8] & 7) << 16) - 0x010000
        if fbm < 0:
            fbm = auto
        s[0x34] = fbm
        lay = 1 if fbm else 0
        if lay != s[0x02]:
            s[0x02] = lay
            s[0x01] = 0x3E
        if s[0x01]:
            s[0x01] -= 1
            c = s[0x01]
            n = 0xA3 if c == 0x3D else 0x100
            for i in range(n):
                y[(c << 8) + i] = 0
            if c == 0:
                for i in range(0x04, 0x60):
                    s[i] = 0
            return [tuple(f) for f in frames]
        if k[5] == 0:                          # MIX 0: at rest (the block passes as it came)
            self.rest(k, lay, fbm, frames)
            return [tuple(f) for f in frames]
        q4 = q4_of(tempo24 & 0xFFFF)
        s[0x3C] = q4
        sync = (k[10] & 1) << 16
        s[0x43] = sync
        N = N1 if lay else N0
        s[0x39], s[0x3A] = N, N << 9
        # ---- L
        chop = k[0]
        if not sync:
            L = (chop * chop) // 2 + 64
        else:
            L = (CHOP_HT[chop >> 4] * q4) >> 5
        x1 = self.lmax(mode, N)
        for _ in range(5):
            if L > x1:
                L >>= 1
        L = max(L, 64)
        s[0x3D] = L
        # ---- D
        x1 = self.drange(mode, N, L)
        t = k[1]
        if not sync:
            D = a1(mpy(x1, t << 16))
        else:
            D = (TIME_HT[t >> 4] * q4) >> 5
            for _ in range(5):
                if D > x1:
                    D >>= 1
        s[0x3E] = D
        # ---- three draws: r1 the choice, r2 the amount, r3 the pan
        r = []
        for _ in range(3):
            s[0x03] = lcg(s[0x03])
            r.append(sx(s[0x03]))
        s[0x44], s[0x47], s[0x4A] = r[0] & M24, r[1] & M24, r[2] & M24
        s[0x22] = du_of(L)
        q = lim(mpy(k[9] << 16, r[2]))
        s[0x23] = lim(ld(FS) - ld(q))
        s[0x24] = lim(ld(FS) + ld(q))
        # ---- the LFO (always runs): a triangle, 0.05 .. 5 Hz
        P = k[2]
        s[0x4B] = P
        inc = ((29 * P * P) >> 10) + 5
        ph = s[0x0E] + inc * len(frames)
        if ph - 0x400000 >= 0:
            ph -= 0x400000
        s[0x0E] = ph
        tri = FS - (abs(ph - 0x200000) << 2)
        s[0x4C] = max(tri, 0)
        # ---- semitones Q8 from TIME: -12 .. +12
        st = (((k[1] * 24) + 64) >> 7) - 12
        s[0x3F] = (st << 8) & M24
        sq = st << 8
        # ---- the grain record: A (and B: voice 1 in PDTN)
        s[0x20], s[0x21], s[0x48], s[0x49] = D, 0x200, D, 0x200
        s[0x25] = (7 * L) >> 3                # floor(7L/8): the asr remainder stays in a0
        s[0x26], s[0x27] = FS, 3
        mo = mode >> 16
        if mo == 0:
            self.dens(L, P)
        elif mo == 1:
            s[0x20] = a1(mpy(D, s[0x4C]))     # scan: 0 .. D
        elif mo == 2:
            s[0x49] = sx(0xFFFE00)            # reverse
            self.sel(P)
        elif mo == 3:
            s[0x49] = 1024 if r[1] >= 0 else 256   # an octave up or down
            self.sel(P)
        elif mo == 4:
            qq = a1(mpy(P << 16, r[1] & FS))
            s[0x20] = D - a1(mpy(D, qq))      # somewhere 0 .. D before the delay
        else:
            self.pitch(L)
            if mo == 5:
                s[0x21] = self.exp(sq + P)
                s[0x49] = self.exp(sq - P)
                s[0x48] = 0
            elif mo == 6:
                s[0x21] = self.exp(a1(mpy(sx(s[0x3F]), s[0x4C])))
            else:
                s[0x21] = self.exp(sq)
                self.dens(L, P)
        if mo != 5:
            s[0x48], s[0x49] = s[0x20], s[0x21]
        for b in (0x20, 0x48):
            s[b] = self.safe(s[b], s[b + 1], L)
        # ---- FDBK, TONE, MIX
        s[0x2C] = lim(mpy(0x79999A, k[3] << 16))
        T = k[7]
        b = (T * (T + 2) << 9) + 0x1FF
        s[0x2D] = max(b, 0x028F5C)
        m = k[5] << 16
        a = ld(FS) if m == 0x7F0000 else ld(m)
        a = a << 1
        g = lim(a)
        a = a - (0x400000 << 25)
        if a < 0:
            a = 0
        kk = lim(a)
        s[0x31], s[0x32] = g, kk
        # ---- FREZ, the feedback modes' block values
        F = k[4]
        s[0x5C] = a1(mpy(F << 16, F << 16)) >> 2
        s[0x33] = 2 if F == 127 else (1 if F else 0)
        s[0x4E] = 1 if s[0x33] == 2 else 0                 # 127 a block; 1..126: each sample rewrites it
        env = s[0x33] == 1 or sync != 0                     # the envelopes run
        fbm = fbm >> 16
        s[0x52] = PING if fbm == 2 else AUX
        if s[0x50] - s[0x52] >= 0:            # POST -> PING: the write index restarts
            s[0x50] = 0
        Tp = s[0x3E] if (mode >> 16) < 5 else 2 * L
        Tp = min(max(Tp, 64), s[0x52] - 2)
        s[0x51] = Tp
        Ls = min(L, LSMAX)
        s[0x56] = Ls
        s[0x57] = du_of(min(128, Ls >> 2))
        s[0x5D] = (k[3] * 9) >> 7
        s[0x5E] = k[3] << 16
        # ---- the samples
        out = []
        for (l, r) in frames:
            xm = lim((ld(l) + ld(r)) >> 1)
            s[0x45] = xm
            s[0x40] = s[0x41] = s[0x42] = 0
            if env:                           # envelopes: fast 1/32, slow 1/1024 a sample
                ax = lim(abs(ld(xm)))
                f = s[0x59]
                s[0x59] = lim(mac(ld(f), 0x040000, lim(ld(ax) - ld(f))))
                f = s[0x5A]
                s[0x5A] = lim(mac(ld(f), 0x002000, lim(ld(ax) - ld(f))))
                # SYNC: an attack (fast > 2 slow + 1/64) restarts the grain and the slot
                if s[0x5B] > 0:
                    s[0x5B] -= 1
                elif sync:
                    b = (ld(s[0x5A]) << 1) + ld(0x020000)
                    if ld(s[0x59]) - b > 0:
                        s[0x05] = 1
                        s[0x53] = 0
                        s[0x5B] = s[0x3D]
            if s[0x33] == 1:
                s[0x4E] = 1 if s[0x5A] - s[0x5C] < 0 else 0
            frz = s[0x4E]
            s[0x05] = s[0x05] - 1
            if s[0x05] <= 0:
                self.start()
            self.voice(0x10)
            self.voice(0x18)
            wm = s[0x42]
            if fbm == 0:                      # RCYC: the ring takes the input plus FDBK x tone(wet)
                t = self.tone(0x2E, wm)
                wv = lim(mac(ld(xm), s[0x2C], t))
            else:
                wv = xm
                if fbm == 1:
                    self.post(wm)
                elif fbm == 2:
                    self.ping(wm)
                else:
                    self.rep(fbm, wm)
            if not frz:
                y[s[0x04]] = wv
                w = s[0x04] + 1
                s[0x04] = 0 if w >= N else w
            o = []
            for ch, d in ((0x40, l), (0x41, r)):
                a = mac(ld(d), -sx(d), kk)
                a = mac(a, s[ch], g)
                o.append(lim(a) & M24)
            out.append(tuple(o))
        return out

    def rest(self, k, lay, fbm, frames):
        """MIX 0: the ring records (not under FREZ 127), layout 1's aux runs out; grains stop."""
        s, y = self.s, self.y
        s[0x12] = s[0x1A] = FS            # both voices silent
        s[0x05] = 1                       # a grain on the first wet sample
        s[0x53] = s[0x55] = 0             # the slot restarts live
        if k[4] == 127:
            return
        N = N1 if lay else N0
        s[0x39] = N
        s[0x52] = PING if (fbm >> 16) == 2 else AUX
        if s[0x50] - s[0x52] >= 0:
            s[0x50] = 0
        for (l, r) in frames:
            xm = lim((ld(l) + ld(r)) >> 1)
            if lay:
                y[AUXB + s[0x50]] = 0
                if (fbm >> 16) == 2:
                    y[AUXB + PING + s[0x50]] = 0
                self.adv()
            y[s[0x04]] = xm
            w = s[0x04] + 1
            s[0x04] = 0 if w >= N else w

    def start(self):
        s = self.s
        s[0x05] = s[0x25]
        vs = s[0x06]
        off = 8 if vs else 0
        s[0x06] = vs ^ 1
        v = 0x10 + off
        rec = 0x48 if vs else 0x20
        a = s[0x04] - s[rec]
        if a < 0:
            a += s[0x39]
        s[v + 0] = a << 9
        s[v + 1] = s[rec + 1]
        s[v + 2] = 0
        s[v + 3] = s[0x22]
        s[v + 4] = s[0x23]
        s[v + 5] = s[0x24]

    def voice(self, v):
        s, y = self.s, self.y
        u = s[v + 2]
        if u == FS:                        # the grain is over: a zero window, nothing to add
            return
        a = FS - u
        if a >= u:
            a = u
        m = lim(ld(a))
        a = mpy(m, s[0x26]) << s[0x27]
        w = lim(acc(a))
        pos = s[v + 0]
        idx = pos >> 9
        i1 = idx + 1
        if i1 >= s[0x39]:
            i1 = 0
        frac = (pos & 0x1FF) << 14
        s0, s1 = sx(y[idx]), sx(y[i1])
        x0 = lim(ld(s1) - ld(s0))
        vv = lim(acc(mpy(frac, x0) + ld(s0)))
        sm = lim(mpy(w, vv))
        s[0x42] = lim(ld(s[0x42]) + ld(sm))
        s[0x40] = lim(mac(ld(s[0x40]), s[v + 4], sm))
        s[0x41] = lim(mac(ld(s[0x41]), s[v + 5], sm))
        a = pos + sx(s[v + 1])
        pn = s[0x3A]
        if a - pn >= 0:
            a = a - pn
        if a < 0:
            a = a + pn
        s[v + 0] = a
        s[v + 2] = lim(ld(u) + ld(s[v + 3]))

    # ---- the feedback modes (per sample) ---------------------------------------------
    def tone(self, st, x):             # one pole: s += a (x - s)
        s = self.s
        b = ld(s[st])
        x0 = lim(acc(ld(x) - b))
        b = mac(b, s[0x2D], x0)
        s[st] = lim(b)
        return lim(b)

    def rd(self):
        s = self.s
        a = s[0x50] - s[0x51]
        return a + s[0x52] if a < 0 else a

    def adv(self):
        s = self.s
        w = s[0x50] + 1
        s[0x50] = 0 if w - s[0x52] >= 0 else w

    def addw(self, l, r):
        s = self.s
        s[0x40] = lim(ld(s[0x40]) + ld(l))
        s[0x41] = lim(ld(s[0x41]) + ld(r))

    def post(self, wm):                # POST: the grains into a delay line with FDBK
        s, y = self.s, self.y
        p = sx(y[AUXB + self.rd()])
        t = self.tone(0x2E, p)
        y[AUXB + s[0x50]] = lim(mac(ld(wm), s[0x2C], t))
        self.adv()
        self.addw(p, p)

    def ping(self, wm):                # PING: in on the left, every repeat changes side
        s, y = self.s, self.y
        i = self.rd()
        pl, pr = sx(y[AUXB + i]), sx(y[AUXB + PING + i])
        t = self.tone(0x2E, pr)
        y[AUXB + s[0x50]] = lim(mac(ld(wm), s[0x2C], t))
        y[AUXB + PING + s[0x50]] = lim(mpy(s[0x2C], pl))
        self.adv()
        self.addw(pl, pr)

    def rep(self, fbm, wm):            # REP..RPCT: slots of L, live or the captured one
        s, y = self.s, self.y
        t = s[0x53]
        if t - s[0x56] >= 0:
            t = 0
        if t == 0:
            self.slot(fbm)
        m = min(t, s[0x56] - 1 - t)
        w = min(m * s[0x57], FS)
        if s[0x54]:
            d = lim(ld(sx(y[AUXB + t])) - ld(wm))
            dl = lim(mpy(w, d))
            self.addw(dl, dl)
        if s[0x58]:
            y[AUXB + t] = wm
        s[0x53] = t + 1

    def slot(self, fbm):
        s = self.s
        if fbm == 3:                      # REP: live, then N repeats
            if s[0x55] > 0:
                s[0x54], s[0x58] = 1, 0
                s[0x55] -= 1
            else:
                s[0x54], s[0x58] = 0, 1
                s[0x55] = s[0x5D]
        elif fbm in (4, 5):               # R1/2, R1/4: a fresh capture every N + 1, else a coin
            if s[0x55] == 0:
                s[0x54], s[0x58] = 0, 1
                s[0x55] = s[0x5D]
            else:
                s[0x55] -= 1
                s[0x03] = lcg(s[0x03])
                p = 0x400000 if fbm == 4 else 0x200000
                s[0x54] = 1 if (s[0x03] & FS) - p < 0 else 0
                s[0x58] = 0
        else:                             # RPCT: repeat with probability FDBK
            s[0x03] = lcg(s[0x03])
            if (s[0x03] & FS) - s[0x5E] < 0:
                s[0x54], s[0x58] = 1, 0
            else:
                s[0x54], s[0x58] = 0, 1

    # ---- block-rate helpers ------------------------------------------------------------
    def dens(self, L, P):              # IOI = L/2 + 3.5 L (127 - P)/128: 4L .. L/2 (the floor at 0)
        t = a1(mpy(L, (127 - P) << 16))
        self.s[0x25] = 3 * t + (t >> 1) + (L >> 1)
        if self.s[0x25] - ((7 * L) >> 3) < 0:   # overlapped: triangles, so two windows never sum past 1
            self.s[0x26] = 0x200000

    def sel(self, P):                  # with probability PARA/128 the grain takes B's inc
        if (P << 16) - (self.s[0x44] & FS) > 0:
            self.s[0x21] = self.s[0x49]

    def pitch(self, L):                # the pitched modes: no delay, triangles at L/2
        s = self.s
        s[0x20] = 0
        s[0x26] = 0x200000
        s[0x25] = L >> 1

    @staticmethod
    def exp(sq):                       # 512 2^(s/12), s Q8 in -12 .. +12 semitones: the table, interpolated
        sq = min(max(sq, -3072), 3072) + 3072
        i, f = sq >> 8, sq & 0xFF
        t0, t1 = EXP[i], EXP[i + 1]
        return t0 + a1(mpy(t1 - t0, f << 15))

    @staticmethod
    def safe(D, inc, L):               # Dsafe = D + 2, + (inc - 512) L / 512 + 1 when the grain reads faster
        e = 0
        if inc - 0x200 > 0:
            x0 = min((inc - 0x200) << 14, FS)     # asl #14 then the limiter
            e = a1(mpy(L, x0)) + 1
        return D + 2 + e

    @staticmethod
    def lmax(mode, N):
        x1 = (N >> 1) - 64
        y0 = min(N - 128, 8128)
        mo = mode >> 16
        return x1 if mo in (2, 3) or mo >= 5 else y0

    @staticmethod
    def drange(mode, N, L):
        mo = mode >> 16
        a = N - L
        if mo in (2, 3) or mo >= 5:
            a -= L
        a -= 4
        return max(a, 0)
