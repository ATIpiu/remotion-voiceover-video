"""音效体检：我听不到声音，用规则和频谱代替耳朵。混音前跑，没通过就不渲染。
用法：python audio/sfxcheck.py             （查 audio/plan.json 里用到的音效）
      python audio/sfxcheck.py a.wav b.wav   （只看指定文件的频谱）

两道关：
  1. 每期限量（不过 = 退出码 1）：同一个声音最多 4 次（1.5 秒内的连拍算 1 次）；全片音效事件 ≤ 每分钟 24 个。用得密 = 听腻。
  2. 频谱（警告）：低频（< 150 Hz）占比 > 40% 或重心 < 200 Hz = 闷的「咚 / 嘭」。对不上材质就删掉，不要用滤波硬救。
只依赖 numpy + ffmpeg。
"""
import json, os, subprocess, sys
import numpy as np

MAX_PER_SOUND, BURST_GAP, MAX_PER_MIN = 4, 1.5, 24

def load(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', '44100', '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32)

def stats(p):
    x = load(p)
    X = np.abs(np.fft.rfft(x)) ** 2
    fr = np.fft.rfftfreq(len(x), 1 / 44100)
    tot = X.sum() + 1e-12
    return X[fr < 150].sum() / tot, (fr * X).sum() / tot, len(x) / 44100

def fmt(t): return f'{int(t // 60)}:{t % 60:04.1f}'

if len(sys.argv) > 1:
    for f in sys.argv[1:]:
        lo, cen, dur = stats(f)
        print(f"{os.path.basename(f):<20} 低频 {lo:4.0%}  重心 {cen:5.0f} Hz  {dur:.2f}s{'  ⚠ 闷' if lo > 0.4 or cen < 200 else ''}")
    sys.exit(0)

plan = json.load(open('audio/plan.json', encoding='utf-8'))
uses = {}
for c in plan['cues']: uses.setdefault(c['name'], []).append(c['t'])
d = plan.get('sfx_dir', 'audio/sfx')
fail, warn = [], 0
events_total = 0
print(f"{'音效':<10}{'事件':>4}{'低频':>6}{'重心Hz':>8}  用在")
for n, ts in sorted(uses.items(), key=lambda kv: kv[1][0]):
    ts = sorted(ts)
    ev = 1 + sum(1 for a, b in zip(ts, ts[1:]) if b - a > BURST_GAP)
    events_total += ev
    f = os.path.join(d, f'{n}_1.wav')
    lo, cen, _ = stats(f) if os.path.exists(f) else (0, 0, 0)
    notes = []
    if ev > MAX_PER_SOUND: notes.append(f'✗ 用了 {ev} 次 > {MAX_PER_SOUND}'); fail.append(n)
    if lo > 0.4 or cen < 200: notes.append('⚠ 闷 / 咚：材质对不上就删'); warn += 1
    print(f"{n:<10}{ev:>4}{lo:>6.0%}{cen:>8.0f}  {', '.join(fmt(t) for t in ts)}")
    for x in notes: print(f"{'':<12}{x}")
mins = plan['total'] / 60
if events_total > MAX_PER_MIN * mins:
    print(f'✗ 全片 {events_total} 个音效事件，超过每分钟 {MAX_PER_MIN} 个（{mins:.1f} 分钟最多 {int(MAX_PER_MIN * mins)}）'); fail.append('density')
print(f"\n{events_total} 个事件，{len(set(fail))} 项不通过，{warn} 个警告")
sys.exit(1 if fail else 0)
