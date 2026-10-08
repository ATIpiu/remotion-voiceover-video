"""整段配音 → 每句起止 + 每个字的起点（秒），用 whisper 逐字时间对齐到口播稿。
用法（faster-whisper 环境）：python audio/align.py audio/vo_full.wav src/lines.json src/vo.json
输出 = {"file", "total", "cer", "abs": {id: [s, e]}, "chars": {id: [每个字起点]}}，Remotion 直接读。
"""
import sys, json, re, difflib
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from whisper_model import load_whisper  # GPU, CPU fallback

take, lines_p, out_p = sys.argv[1:4]
LINES = json.load(open(lines_p, encoding='utf-8'))
DIG = '零一二三四五六七八九'

def zh_int(n):
    if n < 10: return DIG[n]
    if n < 20: return '十' + (DIG[n % 10] if n % 10 else '')
    if n < 100: return DIG[n // 10] + '十' + (DIG[n % 10] if n % 10 else '')
    return ''.join(DIG[int(c)] for c in str(n))

ZH = any('一' <= c <= '鿿' for l in LINES for c in l['text'])  # 英文稿走英文识别

def clean(s):
    if ZH: s = re.sub(r'\d+', lambda m: zh_int(int(m.group())), s)
    return [c.lower() for c in s if c.isalnum()]

m = load_whisper('small')
PROMPT = '以下是普通话的句子，使用简体中文和标点。' if ZH else ''
segs, info = m.transcribe(take, language='zh' if ZH else 'en', word_timestamps=True, beam_size=5,
                          initial_prompt=PROMPT + ('、'.join(dict.fromkeys(re.findall(r'[A-Za-z][A-Za-z0-9+.-]*', ' '.join(l['text'] for l in LINES)))) if ZH else ''))
asr = []  # (char, t0, t1)
for s in segs:
    for w in s.words:
        cs = clean(w.word)
        for k, c in enumerate(cs):
            asr.append((c, w.start + (w.end - w.start) * k / len(cs), w.start + (w.end - w.start) * (k + 1) / len(cs)))

script, owner = [], []
for l in LINES:
    for c in clean(l['text']): script.append(c); owner.append(l['id'])
times = [None] * len(script)
sm = difflib.SequenceMatcher(None, script, [c for c, _, _ in asr], autojunk=False)
for b in sm.get_matching_blocks():
    for k in range(b.size): times[b.a + k] = asr[b.b + k][1:]
matched = sum(1 for t in times if t)
# interpolate unmatched chars between neighbours
known = [i for i, t in enumerate(times) if t]
for i in range(len(times)):
    if times[i]: continue
    lo = max([j for j in known if j < i], default=None); hi = min([j for j in known if j > i], default=None)
    a = times[lo][1] if lo is not None else 0.0; b = times[hi][0] if hi is not None else info.duration
    n0 = lo if lo is not None else -1; n1 = hi if hi is not None else len(times)
    times[i] = (a + (b - a) * (i - n0) / (n1 - n0 + 1e-9), a + (b - a) * (i - n0 + 1) / (n1 - n0 + 1e-9))
res = {}
for i, lid in enumerate(owner):
    s, e = times[i]
    if lid not in res: res[lid] = [s, e]
    else: res[lid][1] = e
res = {k: [round(v[0], 3), round(v[1], 3)] for k, v in res.items()}
cer = 1 - matched / len(script)
chars = {}
for i, lid in enumerate(owner): chars.setdefault(lid, []).append(round(times[i][0], 3))
json.dump({'file': take.replace(os.sep, '/'), 'total': round(info.duration, 3), 'cer': round(cer, 3), 'abs': res, 'chars': chars}, open(out_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{take}: dur {info.duration:.1f}s  matched {matched}/{len(script)}  cer~{cer:.3f}')
for l in LINES: print(f"  {l['id']:8} {res[l['id']][0]:6.2f}-{res[l['id']][1]:6.2f}  {l['text']}")
