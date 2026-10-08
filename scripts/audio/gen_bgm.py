"""MiniMax-Music3 BGM (local weights; set MINIMAX_MUSIC3_DIR). Loading takes ~10 min (slow disk); each 90 s take ~1-2 min on the 5090.
Generate several seeds in ONE run so the load is paid once.
Run with: <envs>/minimax-music3/python gen_bgm.py --out DIR --dur 90 --seeds 7 --prompt "..." [--lyrics "..."]
Output: 44.1 kHz stereo WAV bgm_<seed>.wav"""
import argparse, numpy as np, torch, soundfile as sf
from pathlib import Path
from diffusers import ModularPipeline
# Keep the weights on an SSD: from a hard disk the mmap'd safetensors load with random seeks (~10 min); from NVMe well under a minute.
import os
WEIGHTS = os.environ.get("MINIMAX_MUSIC3_DIR") or str(Path.home() / "models" / "MiniMax-Music3")
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True); ap.add_argument("--dur", type=float, default=90)
ap.add_argument("--seeds", default="7,23,51")
ap.add_argument("--prompt", default="Genre: playful funky electro-pop. BPM: 118. Key: F major. Bouncy, humorous, upbeat. "
                "Instrumental only, no vocals. Arrangement: plucky synth bass, snappy claps, marimba accents, clean mix leaving space for voiceover.")
ap.add_argument("--lyrics", default="[Intro]\n[Instrumental]\n[Verse]\n[Instrumental]\n[Chorus]\n[Instrumental]\n[Bridge]\n[Instrumental]\n[Outro]")
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
pipe = ModularPipeline.from_pretrained(WEIGHTS)
pipe.load_components(dtype=torch.bfloat16)
pipe.to("cuda")
for seed in [int(s) for s in a.seeds.split(",")]:
    audio = pipe(prompt=a.prompt, lyrics=a.lyrics, audio_duration=a.dur,
                 generator=torch.Generator("cuda").manual_seed(seed), output="audios")[0]
    x = audio.float().cpu().numpy() if hasattr(audio, "cpu") else np.asarray(audio, dtype=np.float32)  # returns numpy!
    if x.ndim == 3: x = x[0]
    if x.ndim == 2 and x.shape[0] <= 2: x = x.T
    sf.write(out / f"bgm_{seed}.wav", x, pipe.sampling_rate)
    print("saved bgm", seed, x.shape, flush=True)
print("BGM done")
