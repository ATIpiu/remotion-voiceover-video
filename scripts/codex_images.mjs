// 用 Codex exec（ChatGPT 账号的生图功能）并发出素材图。不占本机 GPU，可以和配音 / 音效 / BGM 同时跑。
// 用法：node codex_images.mjs <images.json> <输出目录> [--jobs 6] [--only a b]
// images.json：
// {
//   "_style": "3D clay render, soft matte ...",            // 拼到每条提示词后面
//   "lobster": {"prompt": "a cute red lobster ...", "alpha": true},   // 透明底单物件 → 1024x1024 PNG
//   "bg_city": {"prompt": "...", "size": [1920, 1080]},     // 整张背景 → 缩放裁切到 size
//   "sheet_a": {"sheet": {"machine": "a converter machine ...", "pen": "a fountain pen ..."}, "grid": [3, 2], "alpha": true}
//                                                           // ★拼图：一次调用画一张网格图，按格切成多个物件 PNG（machine.png、pen.png…）
//   "cover_3x4": {"cover": true, "size": [1080, 1440], "ref": ["frames/hook.png"],   // 封面：ref 路径相对 images.json
//                 "prompt": "版式描述", "safe": "安全区说明", "text": {"主标题": "...", "小字": "..."}}
//                                                           // 封面允许文字（只写 text 里的字），不拼 _style
// }
// 默认用拼图：一张图能产出多个素材。4–6 个小物件一张（2×2 / 3×2），画风天然统一，调用次数降到 1/4–1/6。
// 只有主角级大物件（要放到半屏以上）和整张背景才单独出图。拼图每个物件约 500 px，切出后放大到 1024²，画面里 ≤ 400 px 显示没问题。
// 透明底：先让 Codex 直接出透明 PNG；没有 alpha 的话退回纯绿底 #00FF00，再用 ffmpeg 抠掉。
import {spawn, execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const [specP, outDir, ...rest] = process.argv.slice(2);
const opt = (k, d) => { const i = rest.indexOf(k); return i >= 0 ? rest[i + 1] : d; };
const JOBS = +opt("--jobs", 6);
const PY = process.env.PY || 'python'; // 切拼图用（PIL + numpy）；可用环境变量 PY 指定解释器
const only = rest.includes('--only') ? rest.slice(rest.indexOf('--only') + 1).filter((x) => !x.startsWith('--')) : [];
const spec = JSON.parse(fs.readFileSync(specP, 'utf8'));
const style = spec._style || ''; delete spec._style;
fs.mkdirSync(outDir, {recursive: true});
const OUT = path.resolve(outDir).replace(/\\/g, '/');

// Codex 在 Codex 桌面版里，路径随版本变化
const loc = execFileSync('powershell', ['-NoProfile', '-Command', '(Get-AppxPackage OpenAI.Codex).InstallLocation']).toString().trim();
const CODEX = path.join(loc, 'app', 'resources', 'codex.exe');

const hasAlpha = (f) => {
  try {
    const fmt = execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=pix_fmt', '-of', 'csv=p=0', f]).toString().trim();
    if (!/a/.test(fmt.replace('gray', 'g'))) return false;
    // alpha 通道真的有透明像素（四角的 alpha 均值 < 50）
    const v = execFileSync('ffmpeg', ['-v', 'error', '-i', f, '-vf', 'alphaextract,scale=8:8,format=gray', '-f', 'rawvideo', '-']);
    return (v[0] + v[7] + v[56] + v[63]) / 4 < 50;
  } catch { return false; }
};

const sheetTask = (name, s, greenKey) => {
  const file = `${OUT}/${name}.png`;
  const [cols, rows] = s.grid || [3, 2];
  const items = Object.entries(s.sheet);
  const bg = s.alpha === false ? '' : greenKey
    ? '背景必须是纯色 #00FF00 亮绿色（整块均匀、无渐变无阴影），物体本身不要用绿色。'
    : '背景必须完全透明（PNG 带 alpha 通道），不要地面阴影。';
  return `用你的图片生成功能画一张「素材拼图」，保存为 PNG：${file}
画布按 ${cols} 列 × ${rows} 行均分成 ${cols * rows} 个等大的格子（宽高比 ${cols}:${rows}，用生图工具的原始分辨率，不要缩小）。
每个格子里只画一个物体，放在格子正中，四周留出至少 12% 的空白，绝对不能碰到或越过格子边界；不要画格线、编号、边框。
所有物体同一种画风、同一个光源方向、同样的比例感。画面里不要出现任何文字、字母、数字、logo 或水印。${bg}
按从左到右、从上到下的顺序：
${items.map(([, p], i) => `${i + 1}. ${p}`).join('\n')}
${items.length < cols * rows ? '其余格子留空。\n' : ''}整体风格：${style}
只做这一件事，完成后只回复保存路径和实际像素尺寸。`;
};

// 封面：允许文字（只写 text 里给的字），可带参考图（片子截图、上一版封面），不拼 _style
const coverTask = (name, s) => {
  const file = `${OUT}/${name}.png`;
  const size = s.size || [1080, 1440];
  const refs = (s.ref || []).map((r, i) => `第 ${i + 1} 张附图：${path.basename(r)}`).join('；');
  const txt = Object.entries(s.text || {}).map(([k, v]) => `- ${k}：「${v}」`).join('\n');
  return `用你的图片生成功能做一张视频封面，保存为 PNG：${file}
最终尺寸必须是 ${size[0]}x${size[1]} 像素（宽高比不对就重新生成，不要硬裁掉文字或主体；只差几个像素可以缩放）。
${refs ? `附图（${refs}）是画面依据：保持里面的画风、角色和物件，按下面的版式重新构图。\n` : ''}版式：${s.prompt}
${s.safe ? `安全区：${s.safe}\n` : ''}画面上只出现下面这些文字，一字不差，中文无错别字、无乱码，不要加任何别的文字、logo 或水印：
${txt || '（不要任何文字）'}
文字要粗、大、在手机信息流缩略图里也读得清。
只做这一件事，完成后只回复保存路径和实际像素尺寸。`;
};

const task = (name, s, greenKey) => {
  if (s.cover) return coverTask(name, s);
  if (s.sheet) return sheetTask(name, s, greenKey);
  const file = `${OUT}/${name}.png`;
  const size = s.size || [1024, 1024];
  const bg = s.alpha
    ? greenKey
      ? '背景必须是纯色 #00FF00 亮绿色（整块均匀、无渐变无阴影），物体本身不要用绿色，物体四周留白。'
      : '背景必须完全透明（PNG 带 alpha 通道），只画这一个物体，物体四周留白，不要地面阴影。'
    : '';
  return `用你的图片生成功能画一张图，保存为 PNG：${file}
最终尺寸必须是 ${size[0]}x${size[1]} 像素（不对就用 ffmpeg 或 Python 缩放并居中裁切${s.alpha ? '，保持透明通道' : ''}）。
画面里不要出现任何文字、字母、数字、logo 或水印。${bg}
提示词：${s.prompt}${style ? '. ' + style : ''}
只做这一件事，完成后只回复保存路径和实际像素尺寸。`;
};

const run = (name, s, greenKey = false) => new Promise((resolve) => {
  const md = `${OUT}/task_${name}.md`;
  fs.writeFileSync(md, task(name, s, greenKey));
  const t0 = Date.now();
  const log = fs.openSync(`${OUT}/${name}.log`, 'w');
  const imgs = (s.ref || []).flatMap((r) => ['-i', path.resolve(path.dirname(path.resolve(specP)), r)]);
  const p = spawn(CODEX, ['exec', '--skip-git-repo-check', '-s', 'workspace-write', '-C', OUT, '-o', `${OUT}/${name}.out.md`, ...imgs, '-'], {stdio: ['pipe', log, log]});
  p.stdin.end(fs.readFileSync(md));
  p.on('close', () => resolve((Date.now() - t0) / 1000));
});

const names = Object.keys(spec).filter((n) => !only.length || only.includes(n));
const queue = [...names];
const report = [];
const worker = async () => {
  while (queue.length) {
    const n = queue.shift(), s = spec[n], f = `${OUT}/${n}.png`;
    let sec = await run(n, s);
    let note = '';
    if (s.alpha && fs.existsSync(f) && !hasAlpha(f)) {
      // 没出透明底：重画成绿底再抠
      sec += await run(n, s, true);
      execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', f, '-vf', 'colorkey=0x00FF00:0.30:0.08,despill=type=green', '-pix_fmt', 'rgba', `${OUT}/${n}_k.png`]);
      fs.renameSync(`${OUT}/${n}_k.png`, f);
      note = '（绿底抠图）';
    }
    const ok = fs.existsSync(f);
    if (ok && s.sheet) {
      // 拼图：按格切成单个物件
      const [cols, rows] = s.grid || [3, 2];
      const res = execFileSync(PY, [path.join(path.dirname(fileURLToPath(import.meta.url)), 'split_sheet.py'), f, OUT, String(cols), String(rows), ...Object.keys(s.sheet)]).toString().trim();
      note += `\n  拼图 ${cols}×${rows} → ${Object.keys(s.sheet).length} 个物件\n  ${res.split('\n').join('\n  ')}`;
    }
    report.push(`${ok ? 'ok ' : 'MISS'} ${n.padEnd(16)} ${sec.toFixed(0)} s ${note}`);
    console.log(report.at(-1));
  }
};
const t0 = Date.now();
await Promise.all(Array.from({length: Math.min(JOBS, names.length)}, worker));
console.log(`done ${names.length} 张，用时 ${((Date.now() - t0) / 1000).toFixed(0)} s`);
