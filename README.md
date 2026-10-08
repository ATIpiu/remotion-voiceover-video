# remotion-voiceover-video

一个 Claude Code skill：把口播稿做成带配音、动画、音效、BGM 的视频（横屏 1920×1080 或竖屏 1080×1920），最后附上封面和各平台发布文案。

写好稿子，剩下的交给它。就像在电脑里开了一间小片厂：

| 工位 | 做什么 |
|---|---|
| 录音棚 | 用一小段本人录音克隆声音，整篇稿子一次生成，语气连贯；再用 whisper 对齐出每句、每个字的时间 |
| 画室 | 用 Codex 生图按稿子现画道具和角色（拼图一次出多个物件，自动切成透明 PNG） |
| 动画台 | 每期从零写一个 Remotion 工程，动作按逐字时间触发，说到哪个词动作刚好到位 |
| 拟音 / 作曲 | 按画面事件现做音效（MMAudio），每期单独生成 BGM（MiniMax-Music3） |
| 混音台 | 配音 + 音效 + BGM，人声出现时自动压低 BGM，归一到 -14 LUFS |
| 质检 | 抽帧拼联系表查叠字出框，ASR 回听确认头尾句子都在，找最响的时刻 |
| 海报间 | 按平台出封面（整张由 ImageGen 生成，主标题写清主题和结果，陌生人 3 秒能看懂），写 B站 / 小红书 / 抖音 / TikTok 标题和文案 |

## 安装

```bash
git clone https://github.com/ATIpiu/remotion-voiceover-video ~/.claude/skills/remotion-voiceover-video
```

然后在 Claude Code 里说「用 Remotion 把这篇口播稿做成视频」即可触发。

## 依赖

- Node.js + Remotion（每期工程里 `npm i remotion @remotion/cli`）、ffmpeg
- [Codex CLI](https://github.com/openai/codex)（生图，`scripts/codex_images.mjs` 会从 Codex 桌面版里找 `codex.exe`）
- 封面（可选，优先）：Codex 里装一个 `native-cover-design` 技能，`scripts/codex_cover.mjs` 会让它整张生成封面；没装就用 `codex_images.mjs` 的 cover 条目
- 本地音频模型（作者用 RTX 5090 离线跑，也可以换成云端服务，见 `reference/models.md`）：
  - 配音：Breeze-TTS-2（`BREEZE_REPO`、`BREEZE_MODEL`）
  - 对齐 / 回听：faster-whisper
  - BGM：MiniMax-Music3（`MINIMAX_MUSIC3_DIR`）
  - 音效：MMAudio（`MMAUDIO_DIR`）

| 环境变量 | 用途 |
|---|---|
| `BREEZE_REPO` / `BREEZE_MODEL` | Breeze-TTS 代码和权重目录 |
| `MINIMAX_MUSIC3_DIR` | MiniMax-Music3 权重目录（放 SSD） |
| `MMAUDIO_DIR` | MMAudio 代码目录（含 weights/、ext_weights/） |
| `PY` | 切拼图用的 Python（需 PIL、numpy） |
| `VOICE_REF` | 本人参考录音（可选） |

## 目录

```
SKILL.md              流程
reference/models.md   模型环境、命令
reference/audio.md    配音、对齐、音效、BGM、混音
reference/publish.md  封面和发布文案
scripts/              生图、切图、配音、对齐、音效、BGM、混音、质检脚本
```

## 许可

代码以 MIT 协议开源。用到的模型各有许可：Breeze-TTS 等配音、BGM 模型通常仅限非商用；只克隆本人或已授权的声音；发布时请勾选「AI 生成内容」。
