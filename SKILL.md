---
name: remotion-voiceover-video
description: 用 Remotion 把口播稿做成动画视频（横屏 1920×1080 或 TikTok / 抖音竖屏 1080×1920；配音 + 字幕 + 音效 + BGM），附封面和发布文案。工程每期从零写，不套模板；配音用本机 Breeze 克隆本人声音整段生成（中英文都行），素材图用 Codex exec 并发生成，画面由模型按内容自由发挥，音效和转场音每期现做。用于"用 Remotion 做一期视频 / 把口播稿做成动画 / 做个 TikTok 视频 / 出封面和标题"。
---

# Remotion 口播动画

每期新建一个 Remotion 工程。本机模型环境（配音、BGM、音效、混音）都在本 skill 里，见 `reference/models.md`。

| 位置 | 内容 |
|---|---|
| `scripts/codex_images.mjs`、`split_sheet.py` | Codex 出图：素材拼图切成透明物件；`cover` 条目出带字的封面 |
| `scripts/codex_cover.mjs` | 封面：用 Codex 的 native-cover-design 技能整张生成（优先） |
| `scripts/audio/tts_clone.py`、`gen_bgm.py`、`gen_sfx.py`、`mix.py` | 配音、BGM、音效、混音 |
| `scripts/audio/asr.py`、`analyze_audio.py`、`whisper_model.py` | ASR 回听、音频体检 |
| `scripts/audio/align.py` | 整段配音 → 每句、每个字的时间（whisper） |
| `scripts/audio/sfxcheck.py` | 混音前检查音效（次数、闷不闷） |
| `scripts/audio/peaks.py` | 混音后找最响的时刻 |
| `scripts/runner/` | 远程会话用的任务队列 |
| `reference/models.md` | 本机模型环境、命令、踩坑 |
| `reference/audio.md` | 配音、对齐、音效、BGM、混音的做法 |
| `reference/publish.md` | 封面和各平台发布文案 |

## 流程

```
- [ ] 1 稿子拆句 + 分镜
- [ ] 2 配音 + 对齐（GPU）   ┐
- [ ] 3 素材图（Codex）      ├ 分镜定了就同时开始
- [ ] 4 建工程、写画面       ┘
- [ ] 5 音效 + BGM + 混音
- [ ] 6 渲染（1.25 倍；需要时再出 1 倍）
- [ ] 7 检查
- [ ] 8 封面 + 文案
```

**1 分镜**：口播稿拆成句子（每句一个 id），每幕写清楚画面里发生了什么、在哪个词上动、要用哪些物件、什么声音。画面怎么设计，按内容自己发挥。

**2 配音 + 对齐**：整段一次生成，然后对齐：`python <skill>/scripts/audio/align.py vo_full.wav lines.json vo.json`。见 `reference/audio.md`。

**3 素材图**：按这期需要现画，4–6 个一组写进 `images.json` 的拼图条目，然后跑 `node <skill>/scripts/codex_images.mjs images.json <输出目录> --jobs 6`。

**4 画面**：用 Remotion 写（竖屏 1080×1920 或横屏 1920×1080，30 fps）。所有动作按 `vo.json` 里的逐字时间定时，在说到这个词前约 6 帧开始，这样说到时画面已经到位。字幕按词或按字高亮。竖屏时字幕从 y≈1330 开始，底部约 420 px、右侧约 140 px 是平台界面，主体不要放在那里。

**5 声音**：音效按画面事件现做，BGM 这期现生成，用 `scripts/audio/mix.py` 混到 -14 LUFS。见 `reference/audio.md`。

**6 渲染**：`npx remotion render`，再用 ffmpeg 合上混好的音轨。渲染时不要跑 GPU 模型。

**7 检查**：
- 每句抽一帧拼成联系表，看有没有叠字、出框。
- 从成片里在说到关键词的那一刻抽帧，确认画面已经到位。
- 用 `peaks.py` 看最响的时刻；如果是音效太响就降它的 gain。
- 对成片音轨跑 ASR，确认开头和结尾的句子都在。

**8 封面 + 文案**：封面用 Codex 生图，每个版式一张，先想清楚这期要观众认出什么、为什么点、焦点是什么，再写提示词。见 `reference/publish.md`。

## 交付

成片、封面、文案复制进一个只放这些的交付文件夹，把路径给用户；另附一张音效表（第几秒、什么声音），请用户试听。
