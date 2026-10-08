// 封面：用 Codex 的 native-cover-design 技能整张生成（画面 + 版式 + 字都由 ImageGen 出，不在本地叠字、拼图、缩放）。
// 用法：node codex_cover.mjs <covers.json> <输出目录> [--only cover_4x3 ...]
// covers.json：
// {
//   "_about": "这期视频讲什么、产出是什么（一两句，所有封面共用）",
//   "cover_4x3": {
//     "platform": "B站投稿封面（横版 4:3）", "ratio": "4:3", "size": "1440×1080",
//     "ref": ["refs/hero.png"],                 // 片子里的干净素材（透明底物件、无字幕画面），路径相对 covers.json
//     "layout": "版式与层级：焦点是什么、放哪、占多大；主标题在哪、突出哪个词",
//     "text": ["主标题", "小字"],               // 画面上只出现这些字，一字不差
//     "safe": "左下角约 18%×11% 是时长角标"
//   }
// }
// 一张一张跑：并发时 Codex 可能把别的任务生成的图存成这张。每张约 3–14 分钟。
// 没装 native-cover-design 技能时，退回 codex_images.mjs 的 cover 条目。
import {spawn, execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const [specP, outDir, ...rest] = process.argv.slice(2);
const only = rest.includes('--only') ? rest.slice(rest.indexOf('--only') + 1) : [];
const spec = JSON.parse(fs.readFileSync(specP, 'utf8'));
const about = spec._about || ''; delete spec._about;
fs.mkdirSync(outDir, {recursive: true});
const OUT = path.resolve(outDir).split(path.sep).join('/');
const base = path.dirname(path.resolve(specP));
const loc = execFileSync('powershell', ['-NoProfile', '-Command', '(Get-AppxPackage OpenAI.Codex).InstallLocation']).toString().trim();
const CODEX = path.join(loc, 'app', 'resources', 'codex.exe');

for (const [name, s] of Object.entries(spec)) {
  if (only.length && !only.includes(name)) continue;
  const file = `${OUT}/${name}.png`;
  if (fs.existsSync(file)) fs.renameSync(file, `${OUT}/${name}.prev.png`);  // keep the old one, so ok/MISS below is honest
  const refs = (s.ref || []).map((r) => path.resolve(base, r));
  const prompt = `使用 native-cover-design 技能（$native-cover-design），严格按它的规则做这张封面：整张封面（画面、版式、所有文字）都用原生 ImageGen 生成，不用任何本地脚本画字、合成或修图。
平台：${s.platform}。宽高比 ${s.ratio}（尽量接近 ${s.size}）。
这期视频：${about}
${refs.length ? `附图（${refs.map((r) => path.basename(r)).join('、')}）是片子里的角色和物件：保持这套画风和角色样子，构图按下面的版式重新排。\n` : ''}版式与层级：${s.layout}
没看过这期视频的人只看封面 3 秒，也要能说出"这是个做什么的东西、做出了什么"。主标题必须写明主题对象和它的结果，不能只放情绪、反差或比喻。
画面里只出现这些文字，一字不差，不要别的字、logo、水印：
${s.text.map((t) => `- 「${t}」`).join('\n')}
安全区：${s.safe || '无'}
曝光正常（高光不发白、暗部有细节），颜色和附图一致。
生成后按技能自检（主标题一眼可读、文字准确、角色正确、安全区、3 秒能看懂这期做了什么），不合格就重新生成或编辑，直到合格。
最终文件保存为 PNG：${file}（只复制生成文件，不要本地缩放裁切）。完成后只回复保存路径、像素尺寸和最终提示词。`;
  fs.writeFileSync(`${OUT}/${name}.task.md`, prompt);
  const t0 = Date.now();
  await new Promise((res) => {
    const log = fs.openSync(`${OUT}/${name}.log`, 'w');
    const p = spawn(CODEX, ['exec', '--skip-git-repo-check', '-s', 'workspace-write', '-C', OUT, '-o', `${OUT}/${name}.out.md`,
      ...refs.flatMap((r) => ['-i', r]), '-'], {stdio: ['pipe', log, log]});
    p.stdin.end(prompt);
    p.on('close', res);
  });
  console.log(`${fs.existsSync(file) ? 'ok  ' : 'MISS'} ${name} ${((Date.now() - t0) / 1000).toFixed(0)} s`);
}
