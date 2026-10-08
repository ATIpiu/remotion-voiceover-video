"""Breeze-TTS-2 voice clone, one WAV per line, model loaded once.
Run with: <envs>/qwen3-tts/python tts_clone.py --lines lines.json --ref ref.wav --ref-text ref.txt --out DIR [--seeds 42] [--only L05 L06] [--eager]
Fast path (default): all five Breeze stages as CUDA Graphs / torch.compile — ~3x real time on the 5090 vs ~0.4x eager.
  Needs triton-windows<3.5 in the env and TORCHINDUCTOR_USE_STATIC_CUDA_LAUNCHER=0 (set below; on Windows the static
  launcher overflows a 32-bit C long). First run compiles ~75 s (cached, later ~20 s); warmup peaks ~26 GiB VRAM, then ~8 GiB.
  --eager = old slow path (~8 GiB, no warmup) if the fast path ever fails.
lines.json: [{"id": "L01", "text": "..."}]   (Chinese vocal events: [笑] [叹气] [咳嗽] [清嗓子])
"""
import argparse, json, os, sys
os.environ.setdefault("TORCHINDUCTOR_USE_STATIC_CUDA_LAUNCHER", "0")  # must be set before torch is imported
from pathlib import Path
REPO = Path(os.environ.get("BREEZE_REPO", Path.home() / "envs" / "qwen3-tts" / "breeze-tts"))
MODEL = Path(os.environ.get("BREEZE_MODEL", REPO.parent / "modelscope-cache" / "models" / "BreezeBlue--Breeze-TTS-2" / "snapshots" / "master"))
sys.path.insert(0, str(REPO))
import soundfile as sf
from breeze_infer.runtime import load_runtime, resolve_device, set_all_seeds, update_generation_config_for_breeze
from breeze_infer.templates import get_template, prepare_inputs, select_template_name
from models.fast_streaming import FastBreezeStreamingRuntime, FastStreamingConfig

ap = argparse.ArgumentParser()
ap.add_argument("--lines", required=True)
ap.add_argument("--ref", default=None, help="omit both --ref/--ref-text and give --instruction = Voice Design (built-in voice from a description)")
ap.add_argument("--ref-text", default=None, help="UTF-8 txt with the EXACT transcript of --ref")
ap.add_argument("--out", required=True); ap.add_argument("--seeds", default="42")
ap.add_argument("--instruction", default=None, help="optional: voice direction (tone/pace); switches to Voice Direction")
ap.add_argument("--cfg", type=float, default=1.0, help="use 4 with --instruction")
ap.add_argument("--only", nargs="*", default=[])
ap.add_argument("--eager", action="store_true", help="slow path: no CUDA Graphs / compile")
a = ap.parse_args()
if not a.ref and not a.instruction: sys.exit("need --ref + --ref-text (clone) or --instruction (voice design)")
ref_text = Path(a.ref_text).read_text(encoding="utf-8").strip() if a.ref else None
lines = json.loads(Path(a.lines).read_text(encoding="utf-8"))
seeds = [int(s) for s in a.seeds.split(",")]
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
tok, model, atok = load_runtime(MODEL, device=resolve_device(), attn_implementation="eager")
update_generation_config_for_breeze(model)
cfg = FastStreamingConfig(max_new_tokens=1500, max_seq_len=2048, fast_all=not a.eager, repetition_penalty=1.1)
rt = FastBreezeStreamingRuntime(model, atok, cfg, tokenizer=tok)
for ln in lines:
    if a.only and ln["id"] not in a.only: continue
    for s in seeds:
        req = {"id": ln["id"], "text": ln["text"], "speaker": "S0"}
        if a.ref: req.update(ref_audio_path=str(a.ref), ref_text=ref_text)
        if a.instruction: req["instruction"] = a.instruction
        set_all_seeds(s)
        inputs = prepare_inputs(tok, atok, model, [req], get_template(select_template_name(req)),
                                guidance_scale=a.cfg, guidance_scale_ref=None, guidance_scale_ins=None)
        p = out / f"{ln['id']}_s{s}.wav"
        with sf.SoundFile(p, mode="w", samplerate=rt.sample_rate, channels=1, subtype="PCM_16") as f:
            for ch in rt.iter_audio_chunks(inputs, request_id=ln["id"], seed=s):
                f.write(ch.audio)
        print("saved", p.name, flush=True)
print("TTS done")
