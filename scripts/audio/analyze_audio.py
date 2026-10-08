"""Audit generated audio you cannot listen to: stats + spectrogram contact sheet.
python analyze_audio.py OUT.png FILE_OR_GLOB [...]
Prints dur / peak / loudest-100ms dB / onset ms / peak time ms / spectral centroid / active ratio.
Read the sheet: good SFX = clear transient near the start; reject near-silent takes, pure hiss (centroid > 15 kHz),
or takes whose only event sits at the very end of the window. For TTS: look for truncation and long gaps."""
import sys, glob, subprocess, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
out, fs = sys.argv[1], sorted(f for p in sys.argv[2:] for f in glob.glob(p))
cols = 4; rows = (len(fs) + cols - 1) // cols
fig, ax = plt.subplots(rows, cols, figsize=(20, 2.6 * rows), squeeze=False)
for a_, p in zip(ax.flat, fs):
    x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", "32000", "-f", "f32le", "-"],
                                     capture_output=True).stdout, np.float32)
    env = np.array([np.sqrt(np.mean(x[i:i + 320] ** 2)) for i in range(0, max(1, len(x) - 320), 320)]); pk = env.max() + 1e-9
    X = np.abs(np.fft.rfft(x)); f = np.fft.rfftfreq(len(x), 1 / 32000)
    print(f"{p}: dur={len(x)/32000:.2f}s peak={np.abs(x).max():.2f} loud={20*np.log10(pk):.1f}dB "
          f"onset={np.argmax(env > pk*0.3)*10}ms peakT={np.argmax(env)*10}ms centroid={(X*f).sum()/X.sum():.0f}Hz active={(env > pk*0.1).mean():.2f}")
    a_.specgram(x + 1e-7, NFFT=512, Fs=32000, noverlap=384, cmap="magma", vmin=-120); a_.set_ylim(0, 12000)
    t2 = a_.twinx(); t2.plot(np.arange(len(x)) / 32000, np.abs(x), color="cyan", lw=0.3); t2.set_ylim(0, 1)
    a_.set_title(p.split("/")[-1].split("\\")[-1], fontsize=10)
plt.tight_layout(); plt.savefig(out, dpi=45)
