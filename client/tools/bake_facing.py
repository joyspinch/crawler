#!/usr/bin/env python3
"""bake_facing.py — 把主体位图离线烘成"左右两帧"的朝向精灵表。

为什么必须离线烘：引擎运行时转不了图——`Canvas.BlitImage` 只有源矩形
(sx,sy,sw,sh)，没有旋转、没有水平翻转；`Gui.SpriteBatch` 的每精灵也只有
dx,dy,dw,dh,sx,sy,sw,sh,tint。所以"把角色转个方向"做不到，朝向只能在
素材阶段烘好，运行时按朝向取帧。

本项目是俯视格子地牢，只有左右两个朝向，因此每张精灵表两帧：

    帧 0 = 原图（朝右）
    帧 1 = 水平镜像（朝左）
    源矩形 = (索引 * 帧宽, 0, 帧宽, 帧高)   ← 源图像素，不是显示像素

镜像走"预乘 alpha → 镜像 → 反预乘"，半透明边缘的 RGB 不会被拖成黑边；
反预乘后重新抠 alpha（alpha=0 的像素 RGB 清零、低 alpha 归零），边缘不脏。

朝向可读性：原图是**正面视角**，单靠镜像看不出朝向，所以给需要的主体
烘一个**不对称标记**（史莱姆的大眼睛、蝙蝠的独眼），镜像后标记跑到另一
侧，"往左走 / 往右走"一眼可辨。玩家与骷髅的道具本身就不对称（提灯 /
长剑、剑 / 盾），镜像即明显。

产出（都在 client/assets/ 下）：
    player_sheet.png / slime_sheet.png / skeleton_sheet.png / bat_sheet.png

用法：
    python client/tools/bake_facing.py [--assets <assets 目录>]
"""

import argparse
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# 主体配置表。
#
# src   —— 源位图（client/assets/<src>.png，64×64 带 alpha）。
# mark  —— 要烘进去的"不对称标记"（见下方 MARKERS）；没有就留空。
ENTITY_MARKERS = {
    "player": "lamp",
    "slime": "slime_eye",
    "bat": "bat_eye",
}


def mirror_clean(img):
    """水平镜像，且不产生黑边。

    做法：RGB 预乘 alpha → 镜像 → 反预乘。直接镜像 RGBA 本身不会引入
    插值，但源图里透明像素残留的黑色 RGB 会在反预乘时把边缘拉灰，
    所以顺手做一次预乘/反预乘归一化。
    """
    img = img.convert("RGBA")
    alpha = np.asarray(img.split()[3], dtype=np.float32) / 255.0
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    pre = Image.fromarray(
        np.clip(rgb * alpha[:, :, None], 0, 255).astype(np.uint8), "RGB")
    mpre = np.asarray(pre.transpose(Image.FLIP_LEFT_RIGHT), dtype=np.float32)
    malpha = np.asarray(
        img.split()[3].transpose(Image.FLIP_LEFT_RIGHT), dtype=np.float32) / 255.0
    safe = np.maximum(malpha, 1e-3)[:, :, None]
    straight = np.clip(mpre / safe, 0, 255).astype(np.uint8)
    out = Image.fromarray(straight, "RGB").convert("RGBA")
    out.putalpha(Image.fromarray(
        (np.clip(malpha, 0.0, 1.0) * 255.0).astype(np.uint8), "L"))
    return out


def recut_alpha(img, floor_alpha=6):
    """重新抠 alpha：近透明的像素直接归零，透明像素的 RGB 清零。

    旋转/镜像过的素材常带着"半透明黑"——看着像脏边。这里把
    alpha < floor_alpha 的像素整个丢掉，其余保持不动。
    """
    img = img.convert("RGBA")
    arr = np.asarray(img).copy()
    a = arr[:, :, 3]
    dead = a < floor_alpha
    arr[dead, 3] = 0
    arr[dead, 0] = 0
    arr[dead, 1] = 0
    arr[dead, 2] = 0
    return Image.fromarray(arr, "RGBA")


def add_eye(img, cx, cy, radius, iris, glow, halo_scale, halo_alpha):
    """在主体上烘一只"会看方向"的眼睛（不对称标记）。

    cx/cy —— 眼睛中心（源图像素），**在朝右那一帧里偏右**。
    radius —— 眼球半径（源图像素）。
    iris   —— 虹膜色 (r,g,b)。
    glow   —— 眼周辉光色 (r,g,b)。
    halo_scale / halo_alpha —— 辉光的范围与强度（辉光过强会把主体洗白，
    标记就喧宾夺主了——宁小勿大）。
    """
    base = img.convert("RGBA")
    w, h = base.size

    # 眼周辉光：软圆，模拟怪物在暗处反光。
    halo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hr = max(1, int(radius * halo_scale))
    hd.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], fill=glow + (halo_alpha,))
    halo = halo.filter(ImageFilter.GaussianBlur(max(0.6, radius * 0.55)))
    out = Image.alpha_composite(base, halo)

    # 眼白 + 虹膜 + 高光。
    od = ImageDraw.Draw(out)
    od.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
               fill=(236, 232, 214, 255))
    ir = max(1, int(radius * 0.55))
    od.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=iris + (255,))
    gr = max(1, int(radius * 0.22))
    od.ellipse([cx - gr + radius // 3, cy - gr + radius // 3,
                cx + gr + radius // 3, cy + gr + radius // 3],
               fill=(255, 255, 255, 235))
    return out


def add_lamp(img, cx, cy, radius):
    """给提灯烘一团暖光（不对称标记）。

    玩家原图是正面视角，光靠镜像看不出朝向；提灯在身体的一侧，
    把灯焰烘亮之后，"亮的那一侧 = 朝向的那一侧"，镜像后立刻分得清。
    """
    base = img.convert("RGBA")
    w, h = base.size
    halo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
               fill=(255, 196, 108, 210))
    halo = halo.filter(ImageFilter.GaussianBlur(radius * 0.45))
    out = Image.alpha_composite(base, halo)
    od = ImageDraw.Draw(out)
    core = max(1, int(radius * 0.3))
    od.ellipse([cx - core, cy - core, cx + core, cy + core],
               fill=(255, 238, 186, 255))
    return out


# 标记参数：(cx, cy, radius, iris, glow, halo_scale, halo_alpha)
MARKERS = {
    # 史莱姆：胶体右侧的一只小眼睛（显示 32×32 时约 5px 直径，一眼可辨）。
    "slime_eye": dict(eye=(40, 30, 6, (22, 50, 20), (110, 190, 80), 1.5, 70)),
    # 蝙蝠：头上的一只发红光的独眼（小而亮，像暗处的反光点）。
    "bat_eye": dict(eye=(36, 21, 3, (255, 96, 44), (255, 140, 60), 2.0, 150)),
}


def bake_entity(name, assets_dir, marker=None):
    src_path = os.path.join(assets_dir, name + ".png")
    if not os.path.exists(src_path):
        raise SystemExit("缺少源位图：%s" % src_path)

    base = Image.open(src_path).convert("RGBA")
    if marker == "lamp":
        # 提灯在原图的右下角（朝右那一帧）。
        base = add_lamp(base, 45, 46, 13)
    elif marker:
        cfg = MARKERS[marker]
        base = add_eye(base, cfg["eye"][0], cfg["eye"][1], cfg["eye"][2],
                       cfg["eye"][3], cfg["eye"][4], cfg["eye"][5], cfg["eye"][6])

    frame_right = recut_alpha(base)                 # 帧 0：朝右
    frame_left = recut_alpha(mirror_clean(base))    # 帧 1：朝左

    w, h = frame_right.size
    sheet = Image.new("RGBA", (w * 2, h), (0, 0, 0, 0))
    sheet.paste(frame_right, (0, 0), frame_right)
    sheet.paste(frame_left, (w, 0), frame_left)

    out_path = os.path.join(assets_dir, name + "_sheet.png")
    sheet.save(out_path, optimize=True)
    print("%-10s 2 帧 %dx%d -> %s (%d 字节)"
          % (name, w * 2, h, os.path.basename(out_path),
             os.path.getsize(out_path)))
    return out_path


def main():
    ap = argparse.ArgumentParser()
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    ap.add_argument("--assets", default=os.path.join(root, "client", "assets"))
    args = ap.parse_args()
    os.makedirs(args.assets, exist_ok=True)

    for name in ("player", "slime", "skeleton", "bat"):
        bake_entity(name, args.assets, ENTITY_MARKERS.get(name))

    total = 0
    for f in sorted(os.listdir(args.assets)):
        if f.endswith("_sheet.png"):
            total += os.path.getsize(os.path.join(args.assets, f))
    print("精灵表合计: %.1f KB" % (total / 1024.0))


if __name__ == "__main__":
    main()
