"""Voice + SFX + BGM mixer with voice ducking and loudness normalisation (numpy + ffmpeg; runs anywhere).
python mix.py --plan plan.json --out mix.wav
plan.json = {
  "total": 83.1,                                   # seconds
  "vo":   [{"file": "vo/L01.wav", "t": 0.6}, ...],  # trimmed voice clips and start times
  "sfx_dir": "sfx", "sfx_pick": {"pop": ["pop_1", 0.08, 0.22, 0.0], ...},   # name: [file_stem, src_start, length, align(s before cue)]
  "cues": [{"name": "pop", "t": 3.2, "gain": 0.8}, ...],
  "bgm": "bgm/bgm_23.wav",
  "bgm_segs": [[0, 14.6], [16.4, 86.3]],           # splice out unwanted breaks (optional)
  "bgm_pauses": [[19.25, 1.4]],                    # insert dramatic silence at output time (optional)
  "duck_db": -9, "lufs": -14, "tp": -1.5
}"""
import json, argparse, subprocess, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--plan", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args(); P = json.load(open(a.plan, encoding="utf-8")); SR = 48000
N = int(P["total"] * SR) + SR
def load(p, ch=2):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", str(ch), "-ar", str(SR), "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.float32).copy().reshape(-1, ch)
def fade(x, fi=0.004, fo=0.04):
    i, o = int(fi * SR), int(fo * SR); x[:i] *= np.linspace(0, 1, i)[:, None]; x[-o:] *= np.linspace(1, 0, o)[:, None]; return x
vo = np.zeros((N, 2), np.float32); fx = np.zeros((N, 2), np.float32); vad = np.zeros(N, bool)
for v in P["vo"]:
    x = load(v["file"], 1)[:, 0]
    x = x / (np.sqrt(np.mean(x[np.abs(x) > 0.01] ** 2)) + 1e-9) * 0.12      # level-match lines
    s = int(v["t"] * SR); vo[s:s + len(x)] += x[:, None]; vad[s:s + len(x)] = True
cache = {}
for c in P.get("cues", []):
    fn, st, ln, align = P["sfx_pick"][c["name"]]
    if fn not in cache:
        y = load(f'{P["sfx_dir"]}/{fn}.wav')[int(st * SR):int((st + ln) * SR)].copy()
        cache[fn] = fade(y / (np.abs(y).max() + 1e-9) * 0.5)
    y = cache[fn] * c.get("gain", 1.0); s = max(0, int((c["t"] - align) * SR)); e = min(N, s + len(y)); fx[s:e] += y[:e - s]
b0 = load(P["bgm"]); segs = P.get("bgm_segs") or [[0, len(b0) / SR]]
b = np.concatenate([fade(b0[int(x0 * SR):int(x1 * SR)].copy(), 0.03, 0.03) for x0, x1 in segs])
for pt, pl in sorted(P.get("bgm_pauses", []), reverse=True):
    i = int(pt * SR); b[i - 960:i] *= np.linspace(1, 0, 960)[:, None]
    b = np.concatenate([b[:i], np.zeros((int(pl * SR), 2), np.float32), b[i:]])
if len(b) < N: b = np.tile(b, (int(np.ceil(N / len(b))), 1))
b = b[:N] / (np.sqrt(np.mean(b[:N] ** 2)) + 1e-9) * 0.05
g = np.ones(N, np.float32); cur = 1.0; lo = 10 ** (P.get("duck_db", -9) / 20)
ka, kr = 1 - np.exp(-480 / (0.08 * SR)), 1 - np.exp(-480 / (0.4 * SR))
for n in range(0, N, 480):
    tgt = lo if vad[n:n + 480].any() else 1.0; cur += (tgt - cur) * (ka if tgt < cur else kr); g[n:n + 480] = cur
end = int(P["total"] * SR); fi, fo = int(0.4 * SR), int(2.5 * SR)
g[:fi] *= np.linspace(0, 1, fi); g[end - fo:end] *= np.linspace(1, 0, fo)
mix = (vo + fx + b * g[:, None])[:end]
raw = a.out + ".f32"; mix.astype(np.float32).tofile(raw)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", raw,
                "-af", f'loudnorm=I={P.get("lufs", -14)}:TP={P.get("tp", -1.5)}:LRA=11', "-ar", str(SR), "-c:a", "pcm_s16le", a.out], check=True)
print("wrote", a.out)
