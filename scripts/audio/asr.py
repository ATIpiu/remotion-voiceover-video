"""faster-whisper (small) — GPU float16 via whisper_model.load_whisper, CPU int8 fallback.
Run with: <envs>/whisper/python asr.py OUT.json FILE_OR_GLOB [...]
Writes {basename: {text, dur, segments:[{start,end,text}]}}.  Use it to (1) transcribe a voice reference,
(2) back-check every TTS take (pick the take with lowest CER vs the script)."""
import sys, json, glob, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from whisper_model import load_whisper
out, pats = sys.argv[1], sys.argv[2:]
m = load_whisper("small")
res = {}
for pat in pats:
    for p in sorted(glob.glob(pat)):
        segs, info = m.transcribe(p, language="zh", beam_size=5, vad_filter=False,
                                  initial_prompt="以下是普通话的句子，使用简体中文和标点。")
        segs = [dict(start=round(s.start, 2), end=round(s.end, 2), text=s.text) for s in segs]
        res[os.path.basename(p)] = {"text": "".join(s["text"] for s in segs), "dur": info.duration, "segments": segs}
        print(os.path.basename(p), res[os.path.basename(p)]["text"], flush=True)
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
