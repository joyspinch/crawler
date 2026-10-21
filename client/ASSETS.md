# crawler · 地底爬行 · 素材清单

回合制 Roguelike 地牢探索。角色/怪物/物品的位图用 gpt-image-2.5 生成原图后
由脚本抠 alpha / 裁边 / 缩放入库；**地砖 / 墙 / UI 底板 / 点缀物 / 阴影 / 光晕
全部程序化生成**（大面积底板交给 AI 只会得到高频噪点，程序化可控）；
音效用 Python 合成。

## 一、朝向精灵表（左右两帧）

引擎运行时转不了图——`Canvas.BlitImage` 只有源矩形 `(sx,sy,sw,sh)`，没有旋转、
没有水平翻转；`Gui.SpriteBatch` 的每精灵也只有 `dx,dy,dw,dh,sx,sy,sw,sh,tint`。
所以方向只能**离线预烘焙**：`client/tools/bake_facing.py` 把每个主体烘成一张
**两帧精灵表**。

| 帧索引 | 含义 | 来源 |
|---|---|---|
| 0 | 朝右 | 原图（提灯 / 眼睛在身体右侧） |
| 1 | 朝左 | 原图水平镜像（预乘 alpha → 镜像 → 反预乘，不带黑边） |

源矩形 = `(索引 * 帧宽, 0, 帧宽, 帧高)`，**帧宽是入库图像素**（64），不是显示像素
（显示 32×32）。取帧索引的纯函数在 `client/src/CrawlerFacing.zan`：

```
CrawlerFacing.PlayerFrame(facingRight)   // 0 = 朝右, 1 = 朝左
CrawlerFacing.PlayerSrcX(facingRight)    // 帧的源 X（源图像素）
CrawlerFacing.EnemyFrame(facingRight)    // 怪物同上
```

映射规则与帧数在 `client/tests/crawler_test.zan` 里钉死（往左走 → 帧号变化、
左右两帧索引不同、上下走不改朝向、怪贴身时面朝玩家）。

### 朝向可读性

原图是**正面视角**，光靠镜像看不出朝向，所以 bake 脚本给主体烘了不对称标记：

| 主体 | 标记 | 效果 |
|---|---|---|
| 玩家 | 提灯暖光（右下角） | 亮的那一侧 = 朝向的一侧；地面光池也落在那一侧 |
| 史莱姆 | 偏右的一只眼睛 | 一眼能看出转向 |
| 骷髅 | 长剑 / 盾左右互换 | 镜像即明显 |
| 蝙蝠 | 偏右的一只发光独眼 | 小而亮，暗处也看得见 |

## 二、位图（`client/assets/`）

### 主体精灵表（运行时用）

| 文件 | 尺寸 | 用途 |
|---|---|---|
| `player_sheet.png` | 128×64 | 玩家（披风探险者）两帧：0 朝右 / 1 朝左 |
| `slime_sheet.png` | 128×64 | 史莱姆两帧 |
| `skeleton_sheet.png` | 128×64 | 骷髅两帧 |
| `bat_sheet.png` | 128×64 | 蝙蝠两帧 |

### 场景与物件

| 文件 | 尺寸 | 类别 | 用途 |
|---|---|---|---|
| `floor.png` | 128×128 | 底板（不透明） | 地砖；2×2 放 4 个变体（大石板 + 缝隙 + 苔藓 + 湿渍） |
| `wall.png` | 128×128 | 底板（不透明） | 岩壁；2×2 放 4 个变体（错缝砌块 + 灰缝 + 顶部高光） |
| `torch.png` | 32×48 | 主体（alpha） | 墙上的火把（每隔若干格挂一只） |
| `moss.png` | 32×32 | 主体（alpha） | 地上的苔藓丛 |
| `puddle.png` | 32×24 | 主体（alpha） | 地上的积水/湿渍 |
| `door.png` | 64×64 | 主体（alpha） | 铁门（消耗 1 把钥匙打开） |
| `stairs.png` | 64×64 | 主体（alpha） | 下行楼梯（踩上去下潜一层） |
| `coin.png` | 64×64 | 主体（alpha） | 金币图标（+10 金币） |
| `potion.png` | 64×64 | 主体（alpha） | 药水图标（+1 瓶，回血 25） |
| `key.png` | 64×64 | 主体（alpha） | 钥匙图标（+1 把，开铁门） |

### 效果与 UI 底板

| 文件 | 尺寸 | 用途 |
|---|---|---|
| `shadow.png` | 48×24 | 椭圆落地投影（角色 / 怪物脚下） |
| `glow.png` | 128×128 | 环境暖光（提灯把身边照亮） |
| `lamp.png` | 64×64 | 提灯光池，落在**朝向的一侧**（朝向提示） |
| `ui_board.png` | 64×64 | HUD 面板底板（石板 + 铜边 + 铆钉），九宫格 |
| `ui_button.png` / `_hi` / `_down` | 48×32 | 次要按钮三态，九宫格 |
| `ui_button_primary.png` / `_hi` / `_down` | 48×32 | 主按钮三态（火把橙），九宫格 |

九宫格切角边长：面板 16px、按钮 12px（与 `client/src/CrawlerView.zan` 的
`NineSlice` 一致）。**引擎没有 border-image**，CSS 也没有九宫格，所以底板靠
`CDraw.BlitImage` 裁源矩形自拼 9 块。

### 烘焙源图（不再被运行时加载，只作为 bake 输入）

`player.png` / `slime.png` / `skeleton.png` / `bat.png`（各 64×64，gpt-image-2.5
生成后抠 alpha）——`bake_facing.py` 的输入。

### 生成脚本（都可重跑）

| 脚本 | 产出 |
|---|---|
| `client/tools/bake_facing.py` | 四张两帧朝向精灵表 |
| `client/tools/bake_tiles.py` | `floor/wall/torch/moss/puddle/shadow/glow/lamp` |
| `client/tools/bake_ui.py` | `ui_board.png` 与六张按钮底板 |

> 几何绘制只出现在界面部件（血条、战斗条、文字），符合
> `docs/REAL_GAME_STANDARD.md` 第 1 节"几何绘制只允许用在界面部件"。

## 三、皮肤包（`client/assets/skins/crawler/skin.css`）

地牢风：石板灰底 + 锈金描边 + 火把橙强调。令牌名照
`packages/Zan.Gui/src/Gui/skins/base.css` 抄，不自造；颜色用 `#AARRGGBB`，
与画布 `0xAARRGGBB` 同一套。

- 构建拷到 `build/crawler/skins/crawler/`（**exe 同级**，`Gui.Styling.Skin.Roots`
  查的是 `exe/skins/` 与 `exe/assets/skins/`）；控件基线 `base.css` **不拷**——
  zanc 会自动内嵌 stdlib 的 Gui 皮肤基线（含 base.css 与 dark/light），运行时
  `Skin.BaseCss()` 磁盘找不到就回落到内嵌那份（exe 旁再放一份反而会盖住它）。
- 启动时 `host.App().UseSkin("dark")` → `UseSkin("crawler")`（顺序反了会被
  默认皮肤盖回去）。
- 覆写三处：`:root` 令牌（`--primary` / `--bg-*` / `--text-*` / `--border-*` /
  `--border-radius-*` / `--font-size-*`）、`button`（含 `:hover` / `:active` /
  `button.primary`）、`panel.card`（设置浮层那张卡）。
- 皮肤包里的色值与 `client/src/CrawlerPalette.zan` 一一对应——画布上的 UI 与
  标准库控件是两套渲染路径，靠同一份色值保持观感统一。

## 四、音效（`client/assets/sfx/`）

全部 **22050 Hz / 16 bit / 单声道 WAV**，单个 <1 s，由 Python 合成。

| 文件 | 事件 | 触发时机 |
|---|---|---|
| `step.wav` | 走路 | 成功移动一格 |
| `bump.wav` | 撞墙 | 撞到岩壁 / 无钥匙撞门 |
| `hit.wav` | 命中 | 玩家攻击命中怪物 |
| `hurt.wav` | 受伤 | 玩家被怪物打中 |
| `kill.wav` | 击杀 | 怪物被击败 |
| `coin.wav` | 拾取金币 | 踩到金币 |
| `potion.wav` | 拾取药水 | 踩到药水 |
| `pickup.wav` | 拾取钥匙 | 踩到钥匙 |
| `heal.wav` | 喝药回血 | 喝下药水 |
| `door.wav` | 开门 | 用钥匙打开铁门 |
| `descend.wav` | 下潜 | 踩到楼梯进入下一层 |
| `flee.wav` | 逃跑成功 | 战斗中甩开怪物 |
| `death.wav` | 死亡 | 生命归零进结算 |
| `win.wav` | 通关 | 抵达第 5 层进结算 |

播放走公共包 `Game.Foundation.SfxBank`（磁盘优先 + 内嵌兜底 + 限频），
没有音频设备时整个库静默失效——无头 CI 与没声卡的机器上游戏照常跑。

## 五、授权与红线

- 位图：gpt-image-2.5 生成 + 项目自研加工；地砖/墙/UI 底板为程序化生成，
  无第三方素材引入。
- 音效：Python 纯合成，无采样库。
- **不引入** Cataclysm-DDA / Mindustry 等第三方素材：它们是 CC-BY-SA / GPLv3，
  传染性许可与本项目闭源发布口径冲突。本项目只借鉴"回合制地牢探索"这一
  玩法范式，美术与音效全部自制。
