"""查"很重地拍一下"：列出混音里最响的 100 ms 窗口，和全片第 95 百分位比。
用法：python audio/peaks.py audio/mix.wav [前 N 个，默认 8]
高出第 95 百分位 2 dB 以上的时刻多半是音效太重（低频重的音效 + 大 gain + 同帧震动），去 mkplan 里降 gain 或换轻的音效。"""
import sys, subprocess, numpy as np
p, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8
x = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True).stdout, np.float32)
w = 1600
db = np.array([10 * np.log10(np.mean(x[i:i + w] ** 2) + 1e-12) for i in range(0, len(x) - w, w)])
p95 = np.percentile(db, 95)
print(f'全片 100 ms 窗口第 95 百分位：{p95:.1f} dB')
for i in np.argsort(db)[::-1][:n]:
    t = i * 0.1
    print(f'  {int(t // 60)}:{t % 60:04.1f}  {db[i]:6.1f} dB  {"⚠ 太重" if db[i] > p95 + 2 else ""}')
