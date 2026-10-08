"""把一张网格拼图切成多个透明底物件 PNG。
用法：python split_sheet.py <sheet.png> <输出目录> <cols> <rows> <名字1> <名字2> ...（按从左到右、从上到下）
每格：裁到物体外框 → 四周留 8% 边 → 补成正方形 → 缩放到 1024×1024。
物体压到格线（格子边缘有不透明像素）会打印 WARN，说明 Codex 没把物体放在格子里，需要重画这张拼图。"""
import sys, os
import numpy as np
from PIL import Image

src, out, cols, rows, *names = sys.argv[1:]
cols, rows = int(cols), int(rows)
im = Image.open(src).convert("RGBA")
a = np.array(im)
H, W = a.shape[:2]
os.makedirs(out, exist_ok=True)
for i, name in enumerate(names):
    c, r = i % cols, i // cols
    x0, x1 = W * c // cols, W * (c + 1) // cols
    y0, y1 = H * r // rows, H * (r + 1) // rows
    cell = a[y0:y1, x0:x1]
    alpha = cell[:, :, 3] > 24
    if not alpha.any():
        print(f"MISS {name}: 第 {i + 1} 格是空的")
        continue
    edge = alpha[0].any() or alpha[-1].any() or alpha[:, 0].any() or alpha[:, -1].any()
    ys, xs = np.where(alpha)
    crop = Image.fromarray(cell[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
    side = int(max(crop.size) * 1.16)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(crop, ((side - crop.width) // 2, (side - crop.height) // 2))
    sq.resize((1024, 1024), Image.LANCZOS).save(os.path.join(out, f"{name}.png"))
    print(f"{'WARN' if edge else 'ok  '} {name:16s} {crop.width}x{crop.height}" + ("（压到格线，可能被切掉一块）" if edge else ""))
