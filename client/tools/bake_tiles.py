#!/usr/bin/env python3
"""bake_tiles.py — 程序化生成地牢的地砖 / 墙 / 点缀物 / 投影 / 光晕。

为什么不用 AI 出大面积底板：AI 生成的地砖容易变成**高频噪点**（看着脏、
没有结构）。这里改成**低频有结构**的做法：

  * 地砖：Voronoi 大石板（3~5 块），块与块之间是**缝隙**（暗线），
    每块底色只有一点点差异，再叠**大尺度明暗场**（低频噪声）与局部
    苔藓 / 湿渍 —— 结构是"大块石板 + 缝 + 苔"，不是噪点。
  * 墙：错缝**砌块分层**（一层层砖 + 灰缝），每块有上沿高光 /
    下沿暗边，整块再压一层顶部高光，做出"砌块分层 + 顶部高光"。

每张图 2×2 放 4 个变体（128×128），运行时按格子坐标取一块，避免
整片地砖重复感。

产出（都在 client/assets/ 下）：
  floor.png / wall.png     —— 地砖 / 墙，各 4 变体
  torch.png / moss.png / puddle.png —— 点缀物（位图，带 alpha）
  shadow.png               —— 椭圆落地投影
  glow.png                 —— 提灯暖光晕（径向）

用法：
    python client/tools/bake_tiles.py [--assets <assets 目录>]
"""

import argparse
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

TILE = 64          # 单个变体的边长（源图像素；运行时显示 32×32）
VARIANTS = 2       # 每张图 2×2 个变体


# ---------------------------------------------------------------- 噪声 ----

def lowfreq_field(w, h, cells, seed):
    """低频噪声场：随机 cells×cells 的网格，双三次放大到 w×h。

    值域 0..1。cells 越小越"大块"——地砖要的就是这个，别用逐像素噪声。
    """
    rng = np.random.default_rng(seed)
    grid = rng.random((cells + 1, cells + 1)).astype(np.float32)
    small = Image.fromarray((grid * 255).astype(np.uint8), "L")
    big = small.resize((w, h), Image.BICUBIC)
    return np.asarray(big, dtype=np.float32) / 255.0


def blob_mask(w, h, spots, seed, softness=0.55):
    """若干软斑块的掩码（0..1）：用于苔藓 / 湿渍这种"局部点缀"。

    spots —— [(cx, cy, r), ...]，坐标是像素。
    """
    rng = np.random.default_rng(seed)
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    for (cx, cy, r) in spots:
        jitter = rng.uniform(-0.18, 0.18)
        rr = r * (1.0 + jitter)
        d.ellipse([cx - rr, cy - rr * 0.8, cx + rr, cy + rr * 0.8],
                  fill=int(255 * softness))
    m = m.filter(ImageFilter.GaussianBlur(max(1.0, w * 0.035)))
    return np.asarray(m, dtype=np.float32) / 255.0


def clamp8(a):
    return np.clip(a, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- 地砖 ----

def make_floor_variant(seed):
    """一块 64×64 地砖：大石板 + 缝隙 + 低频明暗 + 苔藓 + 湿渍。"""
    rng = np.random.default_rng(seed)
    w = h = TILE

    # --- 大块不规则石板：每行错缝的宽板，板与板之间留缝 ---
    # 不用 Voronoi：放射状缝看着像"碎纸"。这里用错缝的宽石板，
    # 结构才是"大块石板 + 缝隙"，而不是放射裂缝。
    gap = 3.0
    img = Image.new("RGB", (w, h), (24, 22, 20))
    d = ImageDraw.Draw(img)
    rows = 2
    row_h = h / rows
    split = row_h * rng.uniform(0.82, 1.18)
    bounds = [0.0, split, float(h)]
    for r in range(rows):
        y0 = bounds[r] + gap * 0.5
        y1 = bounds[r + 1] - gap * 0.5
        x = -rng.uniform(0.0, 26.0)
        while x < w:
            bw = rng.uniform(19.0, 34.0)
            x0 = x + gap * 0.5
            x1 = x + bw - gap * 0.5
            if x1 > 0 and x0 < w:
                tone = rng.uniform(-9.0, 9.0)
                warm = rng.uniform(-4.0, 6.0)
                base = (int(60 + tone + warm), int(56 + tone), int(50 + tone - warm))
                d.rounded_rectangle([x0, y0, x1, y1], radius=3, fill=base)
                # 倒角：上沿亮、下沿暗，石板才有厚度。
                d.rounded_rectangle([x0 + 1, y0 + 1, x1 - 1, y0 + 3.5],
                                    radius=2, fill=(base[0] + 15, base[1] + 14, base[2] + 12))
                d.rounded_rectangle([x0 + 1, y1 - 3.5, x1 - 1, y1 - 1],
                                    radius=2, fill=(max(0, base[0] - 14), max(0, base[1] - 13),
                                                    max(0, base[2] - 12)))
                # 崩角：石板边角磕掉一小块。
                for _ in range(int(rng.integers(0, 3))):
                    cx = x0 if rng.random() < 0.5 else x1
                    cy = y0 if rng.random() < 0.5 else y1
                    cr = rng.uniform(2.0, 4.5)
                    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(24, 22, 20))
            x += bw
    img = img.filter(ImageFilter.GaussianBlur(0.5))
    arr = np.asarray(img, dtype=np.float32)

    # --- 低频明暗：大块的受光/背光 ---
    field = lowfreq_field(w, h, 3, seed + 11)
    arr += (field[:, :, None] - 0.5) * 26.0

    # --- 苔藓从缝里长出来：暗处（缝）作掩码，模糊后压上绿 ---
    lum = arr[:, :, 0] * 0.3 + arr[:, :, 1] * 0.5 + arr[:, :, 2] * 0.2
    seam = np.clip(1.0 - lum / 34.0, 0.0, 1.0)
    seam_img = Image.fromarray((seam * 255).astype(np.uint8), "L")
    seam_img = seam_img.filter(ImageFilter.GaussianBlur(2.6))
    moss = np.asarray(seam_img, dtype=np.float32) / 255.0
    moss_col = np.array([44.0, 78.0, 38.0], dtype=np.float32)
    arr = arr * (1.0 - moss[:, :, None] * 0.6) + moss_col * (moss[:, :, None] * 0.6)

    # --- 湿渍：偏冷的一片，边缘更暗（像积水）---
    wet_spots = [(rng.uniform(8, w - 8), rng.uniform(8, h - 8),
                  rng.uniform(4.0, 8.0)) for _ in range(int(rng.integers(1, 3)))]
    wet = blob_mask(w, h, wet_spots, seed + 37, softness=0.32)
    wet_col = np.array([34.0, 40.0, 48.0], dtype=np.float32)
    arr = arr * (1.0 - wet[:, :, None] * 0.42) + wet_col * (wet[:, :, None] * 0.42)

    # --- 稀疏砂粒：极少量高频点，只为别太"塑料" ---
    grit = rng.random((h, w)).astype(np.float32)
    grit = (grit - 0.5) * 10.0
    grit_mask = (grit > 3.0) | (grit < -3.0)
    arr += (grit * grit_mask)[:, :, None]

    # --- 四边压暗一点：块与块拼起来时缝隙更明显 ---
    edge = np.ones((h, w), dtype=np.float32)
    edge[:2, :] *= 0.93
    edge[-2:, :] *= 0.93
    edge[:, :2] *= 0.93
    edge[:, -2:] *= 0.93
    arr *= edge[:, :, None]

    return Image.fromarray(clamp8(arr), "RGB")


# ------------------------------------------------------------------ 墙 ----

def make_wall_variant(seed):
    """一块 64×64 墙：错缝砌块 + 灰缝 + 顶部高光。"""
    rng = np.random.default_rng(seed)
    w = h = TILE
    img = np.zeros((h, w, 3), dtype=np.float32)
    img[:, :, 0] = 34.0
    img[:, :, 1] = 32.0
    img[:, :, 2] = 33.0

    rows = 4
    row_h = h / rows
    mortar = 2.0
    for r in range(rows):
        y0 = r * row_h
        y1 = (r + 1) * row_h
        offset = (r % 2) * 11.0 + rng.uniform(-2.0, 2.0)
        x = -offset
        while x < w:
            bw = rng.uniform(13.0, 21.0)
            x0 = max(0.0, x)
            x1 = min(float(w), x + bw)
            if x1 - x0 > 4.0:
                tone = rng.uniform(-9.0, 9.0)
                block = np.array([50.0 + tone, 46.0 + tone, 42.0 + tone],
                                 dtype=np.float32)
                yi0 = int(y0 + mortar)
                yi1 = int(y1 - mortar)
                xi0 = int(x0 + mortar * 0.6)
                xi1 = int(x1 - mortar * 0.6)
                region = img[yi0:yi1, xi0:xi1, :]
                region[:] = region * 0.35 + block * 0.65
                # 上沿高光 / 下沿暗边：砌块的立体感。
                if yi1 - yi0 > 3:
                    img[yi0:yi0 + 2, xi0:xi1, :] += 20.0
                    img[yi1 - 2:yi1, xi0:xi1, :] -= 16.0
                if xi1 - xi0 > 3:
                    img[yi0:yi1, xi0:xi0 + 1, :] += 8.0
                    img[yi0:yi1, xi1 - 1:xi1, :] -= 10.0
            x += bw

    # 低频明暗：整块墙的大面积受光。
    field = lowfreq_field(w, h, 3, seed + 71)
    img += (field[:, :, None] - 0.5) * 22.0

    # 灰缝里的苔。
    spots = [(rng.uniform(4, w - 4), rng.uniform(4, h - 4),
              rng.uniform(3.0, 7.0)) for _ in range(int(rng.integers(2, 4)))]
    moss = blob_mask(w, h, spots, seed + 83, softness=0.5)
    moss_col = np.array([40.0, 72.0, 36.0], dtype=np.float32)
    img = img * (1.0 - moss[:, :, None] * 0.5) + moss_col * (moss[:, :, None] * 0.5)

    # 顶部高光：整块墙的上沿一条亮带（"墙有顶部高光"）。
    top = np.clip(1.0 - np.arange(h) / 10.0, 0.0, 1.0)
    img += (top[:, None, None] * np.array([26.0, 24.0, 20.0], dtype=np.float32))

    # 整体压暗：墙比地暗，主体才浮得出来。
    img *= 0.88
    return Image.fromarray(clamp8(img), "RGB")


def make_variant_sheet(fn, base_seed):
    """把 4 个变体拼成 2×2 的大图（128×128）。"""
    sheet = Image.new("RGB", (TILE * VARIANTS, TILE * VARIANTS), (0, 0, 0))
    for i in range(VARIANTS * VARIANTS):
        v = fn(base_seed + i * 977)
        sheet.paste(v, ((i % VARIANTS) * TILE, (i // VARIANTS) * TILE))
    return sheet


# -------------------------------------------------------------- 点缀物 ----

def make_torch():
    """墙上的火把：铁环 + 木柄 + 火苗（带 alpha）。"""
    w, h = 32, 48
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 木柄
    d.rectangle([13, 20, 19, 46], fill=(74, 52, 34, 255))
    d.rectangle([13, 20, 15, 46], fill=(96, 68, 44, 255))
    # 铁箍
    d.rectangle([11, 24, 21, 28], fill=(58, 54, 52, 255))
    d.rectangle([11, 38, 21, 41], fill=(52, 48, 46, 255))
    # 火苗外焰
    d.polygon([(16, 2), (25, 18), (16, 26), (7, 18)], fill=(214, 96, 30, 235))
    d.polygon([(16, 7), (22, 18), (16, 23), (10, 18)], fill=(238, 146, 44, 245))
    # 焰心
    d.polygon([(16, 12), (20, 19), (16, 22), (12, 19)], fill=(252, 214, 128, 255))
    # 辉光
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([2, 0, 30, 30], fill=(255, 168, 70, 110))
    glow = glow.filter(ImageFilter.GaussianBlur(5))
    return Image.alpha_composite(glow, img)


def make_moss():
    """地上的苔藓丛：几簇深浅不一的绿（带 alpha）。"""
    w = h = 32
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rng = np.random.default_rng(9021)
    for _ in range(9):
        cx = rng.uniform(6, w - 6)
        cy = rng.uniform(6, h - 6)
        r = rng.uniform(3.0, 6.5)
        tone = rng.uniform(-18, 14)
        col = (int(56 + tone), int(96 + tone), int(44 + tone), 235)
        d = ImageDraw.Draw(img)
        d.ellipse([cx - r, cy - r * 0.75, cx + r, cy + r * 0.75], fill=col)
    # 几根草叶
    d = ImageDraw.Draw(img)
    for _ in range(6):
        x = rng.uniform(8, w - 8)
        y = rng.uniform(10, h - 6)
        hgt = rng.uniform(4, 8)
        d.line([(x, y), (x + rng.uniform(-2, 2), y - hgt)],
               fill=(96, 132, 60, 210), width=1)
    return img.filter(ImageFilter.GaussianBlur(0.4))


def make_puddle():
    """地上的积水/湿渍：偏冷的一汪，边缘有反光（带 alpha）。"""
    w, h = 32, 24
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([3, 4, w - 3, h - 3], fill=(26, 36, 48, 200))
    d.ellipse([6, 6, w - 7, h - 6], fill=(34, 48, 62, 170))
    d.arc([3, 4, w - 3, h - 3], 190, 320, fill=(120, 152, 178, 150), width=1)
    return img.filter(ImageFilter.GaussianBlur(0.6))


# ---------------------------------------------------------------- 效果 ----

def make_shadow(w=48, h=24):
    """椭圆落地投影：中心黑、边缘平滑衰减到透明。"""
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    rx, ry = w / 2.0 - 1.0, h / 2.0 - 1.0
    dist = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    t = np.clip((1.0 - dist) / 0.5, 0.0, 1.0)
    a = (t * t * (3.0 - 2.0 * t) * 255.0).astype(np.uint8)
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 3] = a
    return Image.fromarray(rgba, "RGBA")


def make_glow(size=128, peak=110):
    """提灯暖光晕：中心亮、边缘平滑衰减到透明（暖橙）。"""
    yy, xx = np.mgrid[0:size, 0:size]
    cx, cy = (size - 1) / 2.0, (size - 1) / 2.0
    rx, ry = size / 2.0 - 1.0, size / 2.0 - 1.0
    dist = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    t = np.clip(1.0 - dist, 0.0, 1.0)
    t = t ** 1.7
    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    rgba[:, :, 0] = 255
    rgba[:, :, 1] = 196
    rgba[:, :, 2] = 120
    rgba[:, :, 3] = (t * float(peak)).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def make_lamp(size=64, peak=175):
    """提灯的小光池：比环境光更亮更小，落在角色朝向的一侧。

    颜色偏白暖（255/220/160）——地砖本身是暖褐的，暖橙叠上去看不出
    方向，偏白的光才压得住地砖。
    """
    yy, xx = np.mgrid[0:size, 0:size]
    cx, cy = (size - 1) / 2.0, (size - 1) / 2.0
    rx, ry = size / 2.0 - 1.0, size / 2.0 - 1.0
    dist = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    t = np.clip(1.0 - dist, 0.0, 1.0)
    t = t ** 1.5
    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    rgba[:, :, 0] = 255
    rgba[:, :, 1] = 220
    rgba[:, :, 2] = 160
    rgba[:, :, 3] = (t * float(peak)).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


# ----------------------------------------------------------------- main ----

def main():
    ap = argparse.ArgumentParser()
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    ap.add_argument("--assets", default=os.path.join(root, "client", "assets"))
    args = ap.parse_args()
    os.makedirs(args.assets, exist_ok=True)

    def save(img, name):
        path = os.path.join(args.assets, name)
        img.save(path, optimize=True)
        print("%-14s %-9s %d 字节" % (name, "%dx%d" % img.size,
                                      os.path.getsize(path)))

    save(make_variant_sheet(make_floor_variant, 4211), "floor.png")
    save(make_variant_sheet(make_wall_variant, 9137), "wall.png")
    save(make_torch(), "torch.png")
    save(make_moss(), "moss.png")
    save(make_puddle(), "puddle.png")
    save(make_shadow(), "shadow.png")
    save(make_glow(), "glow.png")
    save(make_lamp(), "lamp.png")


if __name__ == "__main__":
    main()
