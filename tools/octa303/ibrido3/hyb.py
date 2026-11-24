"""OCTA303 hybrid at the source seam: the ColdFire half and the record (coordination, 19 Nov 2026; code written by Claude).

The ColdFire keeps ref303 up to u (split303.cf_front) and the control step; per frame it ships one record in the
track's source slot, in place of the finished samples.  The DSP (o3h.asm) renders the rest (split303.dsp_chain).

THE RECORD (84 DSP words per track; each word carries one 16-bit half of a ColdFire long, high half first, in its
low 16 bits; the bits above are not trusted and are masked):
  w0   $a303            signature (stock: the high half of the sample count, always 0; ANALOG BD: $ab09)
  w1   flags            bit 0: a new voice (the DSP zeroes its 16 state words first)
  w2   $0303            signature
  w3   start | np << 8  the first sample this frame renders (0..15; samples before it are silent) and the number of
                        pieces (1..3).  The pieces cover [start, 16) exactly
  w4.. pieces, 13 halves each: n, c1, b, k, clg, cli, cll hi, cll lo, w2, gcomp, amp hi, amp lo, ampstep (signed)
  w44+2i  u of sample i, high half, low half (a signed 32-bit long)
A piece is a run of samples with the same control words: one starts at each render call and after each control step.
amp is the VCA level at the piece's first sample, before its step: the DSP does amp = max(0, amp + step) per sample;
the ColdFire keeps the same level as max(0, amp + n * step) at the piece's end (exact: the step is constant)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import split303 as S
R, T = S.R, S.T
SIG0, SIG1, W_U, W_PC, PIECE = 0xA303, 0x0303, 44, 4, 13
MAXP = 3

def hybrid_ok(st):
    """the cases the seam carries: no FM, no MUFF, no DIST, DRIV 0 (OSIN = DRV_G0)"""
    return not st.fmq and not st.muff and not st.dist and st.osin == T.DRV_G[0]

class Frame:
    def __init__(self):
        self.u = [0] * 16; self.pieces = []; self.start = None; self.cur = None; self.pos = 0; self.new = 0
    def open(self, st):
        self.cur = [0, st.c1, st.b, st.k, st.clg, st.cli, st.cll, st.w2, st.gcomp, st.amp, st.ampstep]
    def close(self, st):
        c = self.cur; self.cur = None
        if not c or c[0] == 0: return
        st.amp = max(0, c[9] + c[0] * c[10])
        self.pieces.append(c)
    def words(self):
        """the record's 84 halves (None when this frame rendered nothing: no signature, the stock samples stand)"""
        if not self.pieces: return None
        assert len(self.pieces) <= MAXP, len(self.pieces)
        assert self.start + sum(p[0] for p in self.pieces) == 16, (self.start, [p[0] for p in self.pieces])
        w = [0] * 84
        w[0], w[1], w[2], w[3] = SIG0, self.new, SIG1, self.start | len(self.pieces) << 8
        for j, (n, c1, b, k, clg, cli, cll, w2, gc, amp, step) in enumerate(self.pieces):
            assert 1 <= n <= 16 and 0 <= cll < 1 << 23 and 0 <= amp < 1 << 23 and -32768 <= step < 32768
            for v in (c1, b, k, clg, cli, w2, gc): assert 0 <= v < 65536, v
            w[W_PC + PIECE * j: W_PC + PIECE * (j + 1)] = [n, c1, b, k, clg, cli, cll >> 16, cll & 0xFFFF, w2, gc,
                                                           amp >> 16, amp & 0xFFFF, step & 0xFFFF]
        for i, u in enumerate(self.u):
            u &= 0xFFFFFFFF; w[W_U + 2 * i], w[W_U + 2 * i + 1] = u >> 16, u & 0xFFFF
        return w

def render_call(st, w, start, code, n, fr, alive=True, df=None, last=None, seq=None, setup=None):
    """ref303.render_call with the sample loop cut at u: the ColdFire half.  Returns the number of samples it covered
    (0 = stock's samples stand for this call)."""
    if start and code >= 0:
        R.set_df(st, df); R.set_setup(st, setup, df)
    if start:
        if code >= 0: R.note_on(st, code, w); st.latched = 1
        else: st.latched = 0
    if st.latched and last and seq is not None:
        R.set_df(st, df); R.set_setup(st, setup, df); R.gate_frame(st, seq)
    if not st.latched or not alive or n == 0:
        fr.pos += n; return 0
    R.set_df(st, df); R.set_setup(st, setup, df)
    st.ptgt = R.clamp(R.p_of_word(w[0]) + st.fine, T.P_LO, T.P_HI)
    st.cut, st.res, st.env, st.dec = R.raw(w[1]), R.raw(w[2]), R.raw(w[3]), R.raw(w[4])
    assert hybrid_ok(st)
    if fr.start is None: fr.start = fr.pos
    fr.open(st)
    for _ in range(n):
        st.cs -= 1
        if st.cs == 0:
            fr.close(st); st.cs = T.CS; R.ctrl(st); fr.open(st)
        fr.u[fr.pos] = S.cf_front(st); fr.pos += 1; fr.cur[0] += 1
    fr.close(st)
    return n

def dsp_model(dst, words):
    """the DSP half in Python (split303.dsp_chain over the record): the 16 output words X:0.. (v << 8, L = R)"""
    out = [0] * 16
    if words is None: return None
    if words[1] & 1:
        for a in ('fb', 'y1', 'y2', 'y3', 'y4', 'vp1', 'vp2', 'dc', 'amp', 'ovca'): setattr(dst, a, 0)
    start, np_ = words[3] & 0xFF, words[3] >> 8
    i = start
    for j in range(np_):
        p = words[W_PC + PIECE * j: W_PC + PIECE * (j + 1)]
        n = p[0]
        dst.c1, dst.b, dst.k, dst.clg, dst.cli = p[1:6]
        dst.cll = p[6] << 16 | p[7]; dst.w2, dst.gcomp = p[8], p[9]
        dst.amp = p[10] << 16 | p[11]; dst.ampstep = p[12] - 65536 if p[12] & 0x8000 else p[12]
        for _ in range(n):
            u = words[W_U + 2 * i] << 16 | words[W_U + 2 * i + 1]
            if u & 0x80000000: u -= 1 << 32
            v = R.clamp(S.dsp_chain(dst, u) >> T.SHIFT_OUT, -32767, 32767)
            out[i] = (v << 8) & 0xFFFFFF; i += 1
    return out

# ---------------------------------------------------------------- the whole ColdFire call on an O3_SEAM build
CHAIN = ('y1', 'y2', 'y3', 'y4', 'fb', 'dc', 'tone', 'ovca', 'mlo', 'vp1', 'vp2')

class Voice:
    """octa303.s with O3_SEAM = 1, one track: st = its ColdFire state, hmode = H_MODE (1: the DSP has the chain)."""
    def __init__(self):
        self.st = R.Track(); self.hmode = 0; self.fr = None
    def call(self, w, start, code, n, df=None, setup=None, last=None, seq=None, frame_start=False):
        """one sy_render call; returns the longs it leaves in the header's L/R pairs (None: stock's stand)."""
        st = self.st
        if frame_start or self.fr is None: self.fr = Frame()
        fr = self.fr
        if start and code >= 0:
            R.set_df(st, df); R.set_setup(st, setup, df)
        if start:
            if code >= 0: R.note_on(st, code, w); st.latched = 1
            else: st.latched = 0
        if st.latched and last and seq is not None:
            R.set_df(st, df); R.set_setup(st, setup, df); R.gate_frame(st, seq)
        if not st.latched or n == 0:
            fr.pos += n; return None
        R.set_df(st, df); R.set_setup(st, setup, df)
        st.ptgt = R.clamp(R.p_of_word(w[0]) + st.fine, T.P_LO, T.P_HI)
        st.cut, st.res, st.env, st.dec = R.raw(w[1]), R.raw(w[2]), R.raw(w[3]), R.raw(w[4])
        fr.last_hyb = hybrid_ok(st)
        if hybrid_ok(st):
            if fr.start is None: fr.start = fr.pos
            fr.open(st)
            for _ in range(n):
                st.cs -= 1
                if st.cs == 0:
                    fr.close(st); st.cs = T.CS; R.ctrl(st); fr.open(st)
                fr.u[fr.pos] = S.cf_front(st); fr.pos += 1; fr.cur[0] += 1
            fr.close(st)
            return [0] * n
        if self.hmode:                       # back from the DSP: the ColdFire's chain from rest
            for a in CHAIN: setattr(st, a, 0)
            self.hmode = 0
        out = []
        for _ in range(n):
            st.cs -= 1
            if st.cs == 0:
                st.cs = T.CS; R.ctrl(st)
            v = R.clamp(R.sample(st) >> T.SHIFT_OUT, -32767, 32767)
            out.append((v << 16) & R.M32)
        fr.pos += n
        return out
    def frame_end(self):
        """after the frame's last call: the record (None: not written)"""
        words = self.fr.words() if self.fr and getattr(self.fr, 'last_hyb', False) else None
        if words is not None:
            if not self.hmode: words[1] |= 1
            self.hmode = 1
        return words
