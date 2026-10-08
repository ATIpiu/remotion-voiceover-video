# 本机模型环境（作者环境：RTX 5090，离线）
如果第一次安装的时候，需要跟用户确认各种模型是在本地运行还是调用云端服务 并且进行本地化适配
脚本都在本 skill 的 `scripts/audio/`（下面写作 `<audio>`）。`envs` = 放各个 Python 环境的目录（自己约定，比如 `~/envs`），下面的路径都按这个约定写，装到别处就照着改。

## 必守规则

1. **离线**：先设 `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`、`PYTHONIOENCODING=utf-8`，清空代理变量。
2. **GPU 一次只跑一个模型**（BGM 占 24 GB），Remotion 渲染时不跑模型。
3. **音频听不到**：用 `asr.py` 回听 + `analyze_audio.py` 验收，交付时说明。
4. **许可**：Breeze 配音仅限非商用；只克隆本人或已授权的声音。商用前提醒用户。

## 用哪个

| 任务 | Python | 命令 |
|---|---|---|
| 配音 | `envs\qwen3-tts\python.exe`（cwd：`envs\qwen3-tts\breeze-tts`） | `<audio>\tts_clone.py --lines lines.json --ref ref.wav --ref-text ref.txt --out audio\vo --seeds 42`（默认快速路径，约 3 倍实时；出错加 `--eager`） |
| 配音（自带女声，无参考音） | 同上 | `<audio>\tts_clone.py --lines lines.json --out audio\vo --seeds 42 --cfg 4 --instruction "一位二十多岁的年轻女性，声音清亮……"`（不传 `--ref` = Voice Design） |
| 校验 / 对齐 | `envs\whisper\python.exe`（GPU，失败自动退回 CPU） | `<audio>\asr.py check.json "audio\vo\*.wav"`；对齐用 `<audio>\align.py` |
| BGM | `envs\minimax-music3\python.exe` | `<audio>\gen_bgm.py --out audio\bgm --dur 90 --seeds 7 --prompt "... Instrumental only, no vocals"` |
| 音效 | `envs\mmaudio\python.exe` | `<audio>\gen_sfx.py --spec sfx.json --out audio\sfx --variants 1` |
| 混音 | 任意（numpy + ffmpeg） | `<audio>\mix.py --plan plan.json --out mix.wav` → -14 LUFS |
| 音频体检 | 任意 | `<audio>\analyze_audio.py`（波形、响度） |

## 用户本人的声音

要求用本人声音配音时，向用户要一段本人录音（20–30 s 清晰口播），路径记在环境变量 `VOICE_REF` 或项目说明里。先转 24 kHz 单声道，截一段 10–20 s 的完整句子，再用 ASR 写出逐字稿 `ref.txt`。

