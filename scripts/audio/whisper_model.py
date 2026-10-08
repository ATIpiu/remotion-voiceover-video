"""Shared faster-whisper loader: GPU (float16) when the pip cuBLAS/cuDNN DLLs are present, else CPU int8.
The whisper env has nvidia-cublas-cu12 + nvidia-cudnn-cu12==9.* installed; their DLLs live in
site-packages/nvidia/*/bin and must be put on the DLL search path before ctranslate2 loads them.
GPU keeps the CPU free, so a TTS job running at the same time is not slowed down."""
import glob, os, sys


def load_whisper(size="small"):
    for d in glob.glob(os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "*", "bin")):
        os.add_dll_directory(d)
        os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
    from faster_whisper import WhisperModel
    try:
        import numpy as np
        m = WhisperModel(size, device="cuda", compute_type="float16")
        list(m.transcribe(np.zeros(16000, np.float32), language="zh")[0])  # missing DLLs only fail on first use
        return m
    except Exception as e:  # no GPU / DLLs missing → CPU still works, just slower and CPU-heavy
        print(f"whisper: GPU unavailable ({type(e).__name__}: {e}); using CPU", file=sys.stderr, flush=True)
        return WhisperModel(size, device="cpu", compute_type="int8", cpu_threads=8)
