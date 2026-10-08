"""MMAudio large_44k_v2 text-to-audio SFX, model loaded once (~6 s per clip on the 5090).
Run with: <envs>/mmaudio/python gen_sfx.py --spec sfx.json --out DIR [--variants 1,2,3]   (set MMAUDIO_DIR to your MMAudio checkout)
sfx.json: {"whoosh": ["fast airy swoosh whoosh transition sound effect, isolated", 1.5], ...}
Output: <name>_<variant>.wav at 44.1 kHz. Always make >=2 variants and pick by analysis (onset/peak/spectrogram)."""
import os, json, argparse
from pathlib import Path
import torch, torchaudio
MM = os.environ.get("MMAUDIO_DIR") or exit("set MMAUDIO_DIR to your MMAudio checkout (the folder with weights/ and ext_weights/)")
ap = argparse.ArgumentParser()
ap.add_argument("--spec", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--variants", default="1,2"); ap.add_argument("--neg", default="music, speech, human voice, singing, talking")
a = ap.parse_args()
spec = json.load(open(a.spec, encoding="utf-8")); out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
os.chdir(MM)  # weights/ and ext_weights/ are relative to the repo
from mmaudio.eval_utils import all_model_cfg, generate, setup_eval_logging
from mmaudio.model.flow_matching import FlowMatching
from mmaudio.model.networks import get_my_mmaudio
from mmaudio.model.utils.features_utils import FeaturesUtils
setup_eval_logging()
dev, dtype = "cuda", torch.bfloat16
model = all_model_cfg["large_44k_v2"]; seq = model.seq_cfg
with torch.inference_mode():
    net = get_my_mmaudio(model.model_name).to(dev, dtype).eval()
    net.load_weights(torch.load(model.model_path, map_location=dev, weights_only=True))
    fu = FeaturesUtils(tod_vae_ckpt=model.vae_path, synchformer_ckpt=model.synchformer_ckpt, enable_conditions=True,
                       mode=model.mode, bigvgan_vocoder_ckpt=model.bigvgan_16k_path, need_vae_encoder=False).to(dev, dtype).eval()
    fm = FlowMatching(min_sigma=0, inference_mode="euler", num_steps=25)
    for name, (prompt, dur) in spec.items():
        for v in [int(x) for x in a.variants.split(",")]:
            rng = torch.Generator(device=dev); rng.manual_seed(100 * v + len(name))
            seq.duration = dur
            net.update_seq_lengths(seq.latent_seq_len, seq.clip_seq_len, seq.sync_seq_len)
            x = generate(None, None, [prompt], negative_text=[a.neg], feature_utils=fu, net=net, fm=fm, rng=rng, cfg_strength=4.5)
            torchaudio.save(str(out / f"{name}_{v}.wav"), x.float().cpu()[0], seq.sampling_rate)
            print("saved", name, v, flush=True)
print("SFX done")
