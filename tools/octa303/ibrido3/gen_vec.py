"""Frames for the seam bench: the ColdFire half (hyb.py) writes each frame's record; ref303 (whole, a twin voice) gives
the expected samples; hyb.dsp_model checks the record in Python first.
usage: gen_vec.py out.vec judge_notes samples_per_note random_runs frames_per_run [ovdr_runs]
out.vec per frame: int32 track (0..3), int32 words[84], int32 expected[16] (X words, v << 8)"""
import json, os, random, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hyb
R, T, S = hyb.R, hyb.T, hyb.S
out, NN, NS, RUNS, FR = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
OV = int(sys.argv[6]) if len(sys.argv) > 6 else 0
GJ = os.environ.get('O3_GIUDICE', '/home/claude/stradaA/giudice/giudice_meta/dati')
fo = open(out, 'wb'); nfr = [0]; stats = {'pieces': {}, 'start': 0, 'silent': 0}
class Voice:
    def __init__(self, track, df=None, setup=None):
        self.cf, self.ref, self.dsp, self.track, self.df, self.fresh = R.Track(), R.Track(), R.Track(), track, df, 1
        self.setup = setup
    def frame(self, calls):
        """calls: [(w, start, code, n)] summing to 16"""
        fr = hyb.Frame(); exp = []
        for (w, st_, code, n) in calls:
            hyb.render_call(self.cf, w, st_, code, n, fr, df=self.df, setup=self.setup)
            r = R.render_call(self.ref, w, st_, code, n, df=self.df, setup=self.setup)
            exp += [((x >> 8) & 0xFFFFFF) for x in r] if r is not None else [0] * n
        assert len(exp) == 16
        words = fr.words()
        if words is None:
            stats['silent'] += 1; return
        if self.fresh: words[1] |= 1; self.fresh = 0
        got = hyb.dsp_model(self.dsp, words)
        s = words[3] & 0xFF
        assert got[s:] == exp[s:], ('python model differs', nfr[0], got, exp)
        if s: stats['start'] += 1
        np_ = words[3] >> 8; stats['pieces'][np_] = stats['pieces'].get(np_, 0) + 1
        fo.write(struct.pack('<101i', self.track, *words, *got)); nfr[0] += 1
if NN:
    note = json.load(open(GJ + '/note400.json'))
    A = json.load(open(GJ + '/divisione.json'))['A']
    import importlib; sys.path.insert(0, os.environ.get('O3_MOTORI', '/home/claude/stradaA/motori')); MR = importlib.import_module('motore_ref')
    for q, idx in enumerate(A[:NN]):
        n = note[idx]; v = Voice(q & 3); acc = n['acc'] if n['accento'] else 0
        w = [MR._word0(n['freq_hz']), n['cut'] << 8, n['res'] << 8, n['env'] << 8, n['dec'] << 8, acc << 8]
        code = 0 if n['onda'] == 'dente' else 1
        # the judge's note: the note on in the frame's last call, then the phase as the judge sets it
        R.render_call(v.ref, w, True, code, 0); v.ref.phase = int(0.25 * 4294967296) & R.M32
        fr = hyb.Frame(); hyb.render_call(v.cf, w, True, code, 0, fr); v.cf.phase = v.ref.phase
        for f in range(NS // 16): v.frame([(w, False, code, 16)])
for run in range(RUNS):
    rnd = random.Random(1000 + run)
    df = setup = None
    if run < OV:      # dEVILish on the track, its knobs at random (OVDR up to 127) but FM 0 and MUFF OFF; SETUP at
        df = [rnd.choice([0, 1, 2, 64, 127, rnd.randint(0, 127)]) for _ in range(12)]      # random but DRIV 0
        df[1] = df[9] = 0
        setup = [0, rnd.choice([0, 1]), rnd.randint(0, 127), rnd.randint(0, 127), 0, rnd.randint(0, 127)]
    v = Voice(run & 3, df, setup)
    kv = lambda: rnd.choice([0, 1, 64, 126, 127, rnd.randint(0, 127)])
    w = None; code = 0
    for f in range(FR):
        if f == 0 or rnd.random() < 0.05:
            code = rnd.choice([0, 1, 4, 5])   # WAVE: saw/square, R (bit 2); not DIST (bit 1)
            w = [0x4000 + rnd.randint(-24, 30) * 256, kv() << 8, kv() << 8, kv() << 8, kv() << 8, rnd.choice([0, 0, 127, kv()]) << 8]
            s = rnd.randint(0, 15) if f else 0
            v.frame([(w, False, code, s), (w, True, code, 16 - s)])
        else:
            if rnd.random() < 0.08:
                w = list(w); w[rnd.randint(1, 5)] = kv() << 8
            s = rnd.randint(1, 15) if rnd.random() < 0.3 else 0
            v.frame([(w, False, code, s), (w, False, code, 16 - s)] if s else [(w, False, code, 16)])
print('frames', nfr[0], stats)
