"""Offline re-implementation of Wwise interactive-music playback for the 007 First Light menu bank.

Why not wwiser + vgmstream alone: TXTP cannot express segment overlaps (the post-exit of one segment playing
under the pre-entry of the next), and vgmstream layers stems of different sample rates (24/32/36/48 kHz) without
resampling, so 24 kHz stems come out at double speed inside a 48 kHz mix.

This renderer walks the wwiser XML dump of a bank (Music Switch -> Random/Sequence playlist -> Segments ->
Tracks -> clips), schedules every segment on one timeline (entry cue of segment k+1 at the exit cue of segment k,
pre-entry and post-exit both played, as the bank's transition rules say), applies clip trims, clip fade
automation and the Volume/MakeUpGain properties along the node hierarchy, resamples every stem to 48 kHz and
writes 24-bit FLAC. Infinite loops are rendered twice and faded out at the last exit cue. Step/random
containers produce one file per choice ("variant").

Usage: python tools/render_music_timeline.py
Needs: external/wwiser/wwiser.pyz, external/vgmstream/vgmstream-cli.exe, numpy, scipy, soundfile,
       render/banks/*.bnk, render/wem/<id>.wem
"""
import os, sys, math, subprocess, itertools, xml.etree.ElementTree as ET
import numpy as np, soundfile as sf
from scipy.signal import resample_poly

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEM = os.path.join(ROOT, 'render', 'wem')
VG = os.path.join(ROOT, 'external', 'vgmstream', 'vgmstream-cli.exe')
WWISER = os.path.join(ROOT, 'external', 'wwiser', 'wwiser.pyz')
OUT = os.path.join(ROOT, 'audio', 'renders')
SR = 48000
ENTRY_ID, EXIT_ID = 43573010, 1539036744          # Wwise ids of the "Entry" / "Exit" cue markers
STATE_NAMES = {160038168: 'Splash', 2548270042: 'Landing (title fanfare)', 3573931707: 'Loading', 3604647259: 'MainMenu'}
BANKS = (('mx_mainmenu_launch.bnk', 'menu_music_LAUNCH_2026-05-27'), ('mx_mainmenu_current.bnk', 'menu_music_CURRENT_since_1.0.x'))
LOOP_ITER = 2        # iterations rendered for infinite loops
TAIL_FADE = 6.0      # seconds, fade-out ending at the last exit cue

# ----------------------------------------------------------------------------- bank model (wwiser XML)
def F(o):
    return {f.get('name'): f.get('value') for f in o.findall('field')}

class Bank:
    def __init__(self, xml):
        self.objs = {}
        for o in ET.parse(xml).getroot().iter('object'):
            if o.get('name', '').startswith('CAk'):
                f = F(o)
                if 'ulID' in f:
                    self.objs[int(f['ulID'])] = o

    @staticmethod
    def parent(o):
        for x in o.iter('field'):
            if x.get('name') == 'DirectParentID':
                return int(x.get('value'))
        return 0

    def node_db(self, o):
        """Volume (pID 0) + MakeUpGain (pID 5) of this node only."""
        nip = next((x for x in o.iter('object') if x.get('name') == 'NodeInitialParams'), None)
        db = 0.0
        if nip is not None:
            for pb in nip.iter('object'):
                if pb.get('name') == 'AkPropBundle':
                    f = F(pb)
                    if f.get('pID') in ('0', '5'):
                        db += float(f['pValue'])
        return db

    def chain_db(self, oid):
        db, seen = 0.0, set()
        while oid in self.objs and oid not in seen:
            seen.add(oid)
            db += self.node_db(self.objs[oid])
            oid = self.parent(self.objs[oid])
        return db

    @staticmethod
    def switch_target(sw, state):
        for n in sw.iter('object'):
            if n.get('name') == 'Node':
                f = F(n)
                if f.get('key') == str(state) and 'audioNodeId' in f:
                    return int(f['audioNodeId'])

    @staticmethod
    def playlist(rs):
        top = next(l for l in rs.iter('list') if l.get('name') == 'pPlayList')
        return list(top)

    def segment(self, sid):
        o = self.objs[sid]
        f = F(next(x for x in o.iter('object') if x.get('name') == 'MusicSegmentInitialValues'))
        dur = float(f['fDuration'])
        marks = {int(F(m)['id']): float(F(m)['fPosition']) for m in o.iter('object') if m.get('name') == 'AkMusicMarkerWwise'}
        pos = sorted(marks.values())
        entry = marks.get(ENTRY_ID, pos[0] if pos else 0.0)
        exit_ = marks.get(EXIT_ID, pos[-1] if pos else dur)
        tracks = [int(c.get('value')) for c in o.iter('field') if c.get('name') == 'ulChildID']
        return dict(id=sid, dur=dur / 1000, entry=entry / 1000, exit=exit_ / 1000, tracks=tracks)

    def clips(self, tid):
        o = self.objs[tid]
        autos = {}
        for a in o.iter('object'):
            if a.get('name') == 'AkClipAutomation':
                f = F(a)
                pts = [(float(F(p)['From']), float(F(p)['To']), int(F(p)['Interp']))
                       for p in a.iter('object') if p.get('name') == 'AkRTPCGraphPoint']
                autos.setdefault(int(f['uClipIndex']), []).append((int(f['eAutoType']), pts))
        out = []
        for i, c in enumerate(x for x in o.iter('object') if x.get('name') == 'AkTrackSrcInfo'):
            f = F(c)
            out.append(dict(src=int(f['sourceID']), fpa=float(f['fPlayAt']) / 1000, fbt=float(f['fBeginTrimOffset']) / 1000,
                            fet=float(f['fEndTrimOffset']) / 1000, fsd=float(f['fSrcDuration']) / 1000, auto=autos.get(i, [])))
        return out

# ----------------------------------------------------------------------------- playlist expansion
def kids_of(item):
    return [k for l in item.findall('list') for k in l if k.get('name') == 'AkMusicRanSeqPlaylistItem']

def expand(item, choices, path):
    """-> [(segment_id, fade_out_after)], one entry per segment play. choices: {path tuple: child index}."""
    f = F(item)
    seg, loop, rs = int(f['SegmentID']), int(f['Loop']), int(f['eRSType'])
    inf = loop == 0
    n = LOOP_ITER if inf else max(loop, 1)
    if seg:
        body = [(seg, False)]
    elif rs in (0, 2):                       # continuous sequence / continuous random (authored order kept)
        body = []
        for i, k in enumerate(kids_of(item)):
            body.extend(expand(k, choices, path + [i]))
    else:                                    # step sequence / step random: one child per play
        idx = choices.get(tuple(path), 0)
        body = expand(kids_of(item)[idx], choices, path + [idx])
    out = list(body) * n
    if inf and out:
        out[-1] = (out[-1][0], True)
    return out

def step_nodes(item, path, acc):
    f = F(item)
    kids = kids_of(item)
    if int(f['SegmentID']):
        return
    if int(f['eRSType']) in (1, 3) and len(kids) > 1:
        acc[tuple(path)] = len(kids)
    for i, k in enumerate(kids):
        step_nodes(k, path + [i], acc)

# ----------------------------------------------------------------------------- audio
_cache = {}

def stem(src):
    if src not in _cache:
        wem = os.path.join(WEM, f'{src}.wem')
        tmp = os.path.join(WEM, f'_{src}.wav')
        subprocess.run([VG, '-i', '-W', '4', '-o', tmp, wem], capture_output=True)
        a, sr = sf.read(tmp, dtype='float32')
        os.remove(tmp)
        if a.ndim == 1:
            a = np.stack([a, a], 1)
        if sr != SR:
            g = math.gcd(SR, sr)
            a = resample_poly(a, SR // g, sr // g, axis=0).astype(np.float32)
        _cache[src] = a
    return _cache[src]

def curve(x, interp):
    """AkCurveInterpolation -> 0..1 shape."""
    x = np.clip(x, 0, 1)
    if interp == 1: return np.sin(x * np.pi / 2)                       # Sine
    if interp == 3: return np.where(x < .5, np.sqrt(x / 2), 1 - np.sqrt((1 - x) / 2))  # InvSCurve
    if interp == 5: return x * x * (3 - 2 * x)                          # SCurve
    if interp in (0, 2): return x ** 0.5                                # Log
    if interp in (6, 8): return x ** 2                                  # Exp
    if interp == 7: return 1 - np.cos(x * np.pi / 2)                    # SineRecip
    if interp == 9: return np.zeros_like(x)                             # Constant (hold)
    return x                                                            # Linear

def envelope(n, auto):
    env = np.ones(n, np.float32)
    t = np.arange(n) / SR
    for typ, pts in auto:
        if typ not in (3, 4) or len(pts) < 2:       # 3 = FadeIn, 4 = FadeOut (values are linear gain 0..1)
            continue
        e = np.full(n, pts[0][1], np.float32)
        for (t0, v0, ip), (t1, v1, _) in zip(pts, pts[1:]):
            m = (t >= t0) & (t < t1)
            if t1 > t0:
                e[m] = v0 + (v1 - v0) * curve((t[m] - t0) / (t1 - t0), ip)
        e[t >= pts[-1][0]] = pts[-1][1]
        env *= e
    return env

def render_sequence(bank, seq):
    """seq: [(segment_id, fade_after)] -> float32 stereo at SR. t=0 is the first segment's entry cue."""
    segs = [bank.segment(s) for s, _ in seq]
    T = []
    for k, s in enumerate(segs):
        T.append(-s['entry'] if k == 0 else T[-1] + segs[k - 1]['exit'] - s['entry'])
    end = max(T[k] + s['dur'] for k, s in enumerate(segs))
    fade_at = None
    for k, (sid, fl) in enumerate(seq):
        if fl:
            fade_at = T[k] + segs[k]['exit']
            end = min(end, fade_at + 0.01)
    n = int(end * SR) + 1
    mix = np.zeros((n, 2), np.float32)
    for k, s in enumerate(segs):
        for tid in s['tracks']:
            gain = 10 ** (bank.chain_db(tid) / 20)      # track + segment + containers (+ switches), buses excluded
            for c in bank.clips(tid):
                if c['fbt'] < 0 or c['fet'] > 0:
                    print('  WARN: clip with repeats not supported, track', tid)
                start = T[k] + c['fpa'] + c['fbt']      # audible start on the timeline (wwiser: pad = fPlayAt + fBeginTrim)
                off, length = c['fbt'], c['fsd'] - c['fbt'] + c['fet']
                a = stem(c['src'])
                i0, i1 = int(round(off * SR)), min(len(a), int(round((off + length) * SR)))
                seg_a = a[i0:i1] * envelope(i1 - i0, c['auto'])[:, None] * gain
                p0 = int(round(start * SR))
                if p0 < 0:
                    seg_a, p0 = seg_a[-p0:], 0
                p1 = min(n, p0 + len(seg_a))
                if p1 > p0:
                    mix[p0:p1] += seg_a[:p1 - p0]
    if fade_at is not None:
        f0, f1 = max(0, int((fade_at - TAIL_FADE) * SR)), min(n, int(fade_at * SR))
        mix[f0:f1] *= np.linspace(1, 0, f1 - f0, dtype=np.float32)[:, None]
        mix = mix[:f1]
    return mix

# ----------------------------------------------------------------------------- main
def main():
    renders = []
    for bnk, label in BANKS:
        xml = os.path.join(ROOT, 'research', 'banks', bnk[:-4] + '.wwiser.xml')
        if not os.path.exists(xml):
            subprocess.run([sys.executable, WWISER, '-d', 'xml', bnk], cwd=os.path.join(ROOT, 'render', 'banks'), capture_output=True)
            os.replace(os.path.join(ROOT, 'render', 'banks', bnk + '.xml'), xml)
        bank = Bank(xml)
        sw = next(o for o in bank.objs.values() if o.get('name') == 'CAkMusicSwitchCntr' and '3931772277' in ET.tostring(o, encoding='unicode'))
        for state, sname in STATE_NAMES.items():
            node = bank.switch_target(sw, state)
            o = bank.objs[node]
            if o.get('name') == 'CAkMusicSegment':
                variants = {(): [(node, False)]}
            else:
                top = bank.playlist(o)
                acc = {}
                for i, it in enumerate(top):
                    step_nodes(it, [i], acc)
                keys = sorted(acc)
                variants = {}
                for combo in (itertools.product(*[range(acc[k]) for k in keys]) if keys else [()]):
                    ch = dict(zip(keys, combo))
                    seq = []
                    for i, it in enumerate(top):
                        seq.extend(expand(it, ch, [i]))
                    variants[combo] = seq
            for combo, seq in variants.items():
                name = f'State_MX_MainMenu - {sname}'
                if len(variants) > 1:
                    name += ' [variant ' + '-'.join(str(c + 1) for c in combo) + f' of {len(variants)}]'
                mix = render_sequence(bank, seq)
                renders.append((label, name, mix))
                print(f'{label}/{name}: {len(mix) / SR:.1f}s  segments {[s for s, _ in seq]}  peak {np.abs(mix).max():.3f}')
    peak = max(np.abs(m).max() for _, _, m in renders)
    g = 10 ** (-1 / 20) / peak
    print(f'global gain {20 * math.log10(g):+.1f} dB (shared by all files, relative levels preserved)')
    for label, name, mix in renders:
        d = os.path.join(OUT, label)
        os.makedirs(d, exist_ok=True)
        sf.write(os.path.join(d, name + '.flac'), np.clip(mix * g, -1, 1), SR, subtype='PCM_24')

if __name__ == '__main__':
    main()
