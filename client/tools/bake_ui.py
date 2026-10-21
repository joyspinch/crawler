#!/usr/bin/env python3
"""bake_ui.py — 生成画布 UI 的美术底板（面板板 + 按钮三态）。

为什么要有底板：画布上的 HUD 面板与按钮原先是"圆角矩形 + 纯色 +
系统风文字"，没有美术。这里离线画出**九宫格可拉伸**的地牢风底板
（石板 + 锈金边 + 铆钉角），运行时用 CDraw 裁源矩形拼 9 块（引擎没有
border-image，九宫格得自己切）。

产出（都在 client/assets/ 下）：
  ui_board.png          —— HUD 面板底板（石板 + 铜边）
  ui_button.png         —— 次要按钮 常态
  ui_button_hi.png      —— 次要按钮 悬停
  ui_button_down.png    —— 次要按钮 按下
  ui_button_primary*.png —— 主按钮三态（火把橙实心）

板子 64×64、按钮 48×32；九宫格的切角边长取板子边长的 1/4
（见 client/src/CrawlerView.zan 的 NineSlice）。

用法：
    python client/tools/bake_ui.py [--assets <assets 目录>]
"""

import argparse
import os

from PIL import Image, ImageDraw, ImageFilter

BOARD_W, BOARD_H = 64, 64
BUTTON_W, BUTTON_H = 48, 32

# 地牢配色（与 client/src/CrawlerPalette.zan 一一对应）。
STONE = (52, 45, 38)
STONE_LIGHT = (68, 59, 48)
STONE_DARK = (22, 19, 17)
BRASS = (150, 110, 58)
BRASS_BRIGHT = (198, 154, 82)
EMBER = (186, 96, 40)
EMBER_BRIGHT = (226, 138, 62)
EMBER_DARK = (126, 60, 24)


def bevel_box(size, radius, body, top, bottom, edge, width=2):
    """一块带倒角的板：底色 + 上/左亮边 + 下/右暗边 + 描边。"""
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=body,
                         outline=edge, width=width)
    d.rounded_rectangle([width, width, w - 1 - width, h - 1 - width],
                        radius=max(1, radius - 2), outline=top, width=1)
    d.rounded_rectangle([width, h - 1 - width * 2, w - 1 - width, h - 1 - width],
                        radius=max(1, radius - 2), outline=bottom, width=1)
    return img


def make_board():
    """HUD 面板底板：深石板 + 铜色边框 + 四角铆钉。

    九宫格的**中间区会被拉伸**，所以中间必须保持纯色——任何画在中间
    的纹理都会被拉成条纹。四角铆钉落在角切片里，拉伸时不变形。
    """
    w, h = BOARD_W, BOARD_H
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=6, fill=STONE + (234,),
                         outline=BRASS + (255,), width=2)
    # 内嵌暗线（上下左右都在边条里，拉伸不变形）。
    d.rounded_rectangle([4, 4, w - 5, h - 5], radius=3,
                        outline=STONE_DARK + (220,), width=1)
    # 上沿高光 / 下沿压暗：面板有厚度。
    d.rectangle([5, 5, w - 6, 7], fill=(84, 72, 58, 190))
    d.rectangle([5, h - 9, w - 6, h - 6], fill=(12, 10, 9, 170))
    # 四角铆钉（落在角切片里）
    for (cx, cy) in ((6, 6), (w - 7, 6), (6, h - 7), (w - 7, h - 7)):
        d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=BRASS_BRIGHT + (255,))
        d.ellipse([cx - 1, cy - 1, cx + 1, cy + 1], fill=STONE_DARK + (255,))
    return img


def make_button(body, top, bottom, edge):
    """按钮底板：石台 + 铜边，角上有铆钉。"""
    w, h = BUTTON_W, BUTTON_H
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=5, fill=body + (255,),
                         outline=edge + (255,), width=2)
    # 上沿高光 / 下沿暗边
    d.rectangle([3, 3, w - 4, 4], fill=top + (255,))
    d.rectangle([3, h - 5, w - 4, h - 4], fill=bottom + (255,))
    # 角铆钉
    for (cx, cy) in ((5, 5), (w - 6, 5), (5, h - 6), (w - 6, h - 6)):
        d.ellipse([cx - 1, cy - 1, cx + 1, cy + 1], fill=edge + (255,))
    return img


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
        print("%-26s %-9s %d 字节" % (name, "%dx%d" % img.size,
                                      os.path.getsize(path)))

    save(make_board(), "ui_board.png")
    save(make_button((58, 50, 42), (80, 70, 57), (32, 27, 23), BRASS),
         "ui_button.png")
    save(make_button((80, 68, 54), (104, 90, 72), (40, 34, 28), BRASS_BRIGHT),
         "ui_button_hi.png")
    save(make_button((36, 31, 26), (28, 24, 20), (66, 56, 46), (108, 80, 42)),
         "ui_button_down.png")
    save(make_button(EMBER, EMBER_BRIGHT, EMBER_DARK, (232, 168, 92)),
         "ui_button_primary.png")
    save(make_button((214, 120, 54), EMBER_BRIGHT, (146, 74, 30),
                      (250, 196, 120)), "ui_button_primary_hi.png")
    save(make_button((132, 66, 28), (110, 52, 20), (186, 96, 40),
                      (196, 118, 56)), "ui_button_primary_down.png")


if __name__ == "__main__":
    main()
