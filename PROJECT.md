# 地底爬行 · CRAWLER —— 回合制 Roguelike 地牢探索

> 仓库外的独立项目。素材清单见 [`client/ASSETS.md`](client/ASSETS.md)；
> 交付标准见 zan-lang 仓库的 `docs/REAL_GAME_STANDARD.md`。

## 玩法

一局 = 往地底深处钻。**目标：抵达第 5 层**（胜利）；**血掉光**（失败）。

| 要素 | 内容 |
|---|---|
| 地图 | 40×24 网格，**种子随机生成**（房间 + 走廊 + 铁门 + 下行楼梯）。同种子同结果。 |
| 视野 | 半径有限（4/6/8 格可调）。视野外黑着，**记住过但当前看不见**的格子压暗显示。 |
| 移动 | 方向键 / WASD，按一次走一格，按住连续走。撞墙不消耗回合。 |
| 战斗 | 走到怪的那一格进入回合制战斗：**空格**攻击 / **F** 喝药 / **R** 逃跑。怪会反击。 |
| 敌人 | 史莱姆（8HP/3伤，隔回合动）、骷髅（16HP/7伤，寻路追）、蝙蝠（6HP/4伤，两步乱飞）。**越深血厚伤高、怪更多。** |
| 物品 | 金币（+10）、药水（回 25，不超上限）、钥匙（开铁门）。 |
| 楼层 | 踩到楼梯下潜一层（回 8 血）；本层怪清空额外 +20 金币。 |
| 结算 | 到达层数 / 击杀 / 金币 / 回合 / 用时，并计入累计战绩。 |

### 闭环

`方向键移动` → `状态变化（位置/血/资源）` → `画面变化（迷雾揭开、贴图变化）+ 音效` →
`目标（到第 5 层）+ 失败条件（死亡）+ 成长（累计金币/击杀/通关次数入存档）`。

### 操作

| 键 | 作用 |
|---|---|
| 方向键 / WASD | 移动一格（可按住连走） |
| 空格 / 回车 | 菜单开始、结算再来一局、战斗攻击 |
| F | 喝药水（探索与战斗中都可用） |
| R | 战斗中逃跑 |
| M | 结算时回主菜单 |
| Esc | 打开/关闭设置浮层（怪物凶险 / 视野半径 / 音效） |

鼠标可点"开始新的一局" / "再来一局" / "回到主菜单" / "设置"。

## 目录

```
crawler/
  client/
    src/          玩法与渲染代码（11 个 .zan）
    assets/       22 张位图 + assets/skins/crawler/skin.css + assets/sfx/ 14 个音效
    tests/        crawler_test.zan（127 条玩法断言）
    tools/        build.ps1 / test.ps1 / toolchain.ps1 / bake_*.py / shot_*.script
  build/          编译产物（不入库）
  _scratch/       一次性脚本与探针（不入库）
```

### 模块

| 文件 | 职责 |
|---|---|
| `main.zan` | GuiHost 入口 |
| `CrawlerApp.zan` | 帧循环、输入（持续方向键 + 离散动作）、菜单/结算按钮、皮肤包挂载 |
| `CrawlerGame.zan` | 玩法核心：状态机（菜单/游戏中/结算）、回合、拾取、下潜、死亡/通关 |
| `CrawlerMap.zan` | 种子化地图生成、视野（迷雾）、连通性、**BFS 寻路** |
| `CrawlerEntities.zan` | 敌人/物品数值表与实体（含敌人朝向） |
| `CrawlerCombat.zan` | 回合制战斗（攻击 / 反击 / 逃跑） |
| `CrawlerView.zan` | 渲染：位图贴图、九宫格 UI 底板、柔化迷雾、火光、投影、HUD、菜单、结算 |
| `CrawlerFacing.zan` | 朝向 → 取帧索引的纯函数（左右两帧精灵表） |
| `CrawlerPalette.zan` | 全项目唯一色板（与皮肤包同色值） |
| `CrawlerSfx.zan` | 音效事件 → WAV（走公共包 `Game.Foundation.SfxBank`） |
| `GameShell.zan` | 存档（最深层数/累计金币/累计击杀/通关次数/局数）+ 设置浮层 |

## 观感品质（第二轮）

| 项 | 做法 |
|---|---|
| **朝向** | 引擎运行时转不了图（`Canvas.BlitImage` 只有源矩形，无旋转/翻转），所以左右两帧**离线烘焙**：`client/tools/bake_facing.py` 产出两帧精灵表，取帧索引是纯函数 `CrawlerFacing.PlayerFrame(facingRight)`，用例钉住映射。玩家按最后移动方向取帧，怪物面朝玩家/移动方向。 |
| **UI 图形化** | 游戏自带皮肤包 `client/assets/skins/crawler/skin.css`（石板 + 锈金 + 火把橙），构建拷到 exe 同级 `build/crawler/skins/crawler/`，启动时 `UseSkin("dark")` → `UseSkin("crawler")`；画布上的 HUD 面板与按钮改用**美术底板**（`client/assets/ui_*.png`，九宫格自切，按钮三态），不再用圆角纯色块；颜色统一收在 `client/src/CrawlerPalette.zan`。 |
| **地牢氛围** | 地砖/墙改为**程序化生成的低频结构**（大块石板 + 缝隙 + 苔藓 + 湿渍 / 错缝砌块 + 顶部高光），不再是 AI 高频噪点；墙上挂火把、地上有苔藓与积水；角色与怪物带椭圆落地投影；视野迷雾按到玩家的距离**连续变浓**（每格再分 2×2 算浓度），边界是渐变带而不是一刀切的方块；提灯的暖光与光池落在**朝向的一侧**，既是氛围也是朝向提示。 |

## 编译

```powershell
pwsh -File client/tools/build.ps1 -PackageProject "$env:ZAN_HOME"
```

`-PackageProject` 指向含 `packages/` 的 zan-lang 仓库（或它的干净 worktree）。
不传时按 `$ZAN_HOME` → 参数 → 已知仓库位置找编译器与 stdlib
（见 `client/tools/toolchain.ps1`）。

产物：`build/crawler/Crawler.exe`（素材同时内嵌进 exe 与磁盘副本，磁盘优先）。

## 测试

```powershell
pwsh -File client/tools/test.ps1 -PackageProject "$env:ZAN_HOME"
```

三段全绿才算过：

1. `crawler_test_OK` —— 127 条玩法断言（地图可达性 / 同种子可复现 / 撞墙不移动 /
   视野半径 / 战斗扣血与击杀 / 药水不超上限 / 拾取计数 / 楼梯下潜重建 /
   死亡进结算 / **朝向映射（左右帧索引不同、往左走帧号变化、怪面朝玩家）** /
   三个种子跑完整流程状态自洽）。
2. `crawler_SAVE_OK runs=1 -> runs=2` —— 存档写两遍，新进程读回上一遍的档。
3. `crawler_SMOKE_OK` —— 无头冒烟：自动打完一整局（会真的下潜、打怪、通关）后退出。

存档目录默认 `%LOCALAPPDATA%/Crawler`；测试用 `CRAWLER_SAVE` 指到临时目录。

## 截图验收

窗口像素抓取（`scripts/shot_window.py` 抓的是窗口真实像素，不是后端画布）：

```powershell
$out = (Resolve-Path 'build/crawler').Path
$env:ZAN_UI_OUT = "$out/uidrv"
$env:CRAWLER_SAVE = "$out/savetest"
$env:ZAN_UI_SCRIPT = (Resolve-Path 'client/tools/shot_face_right.script').Path
python "$env:ZAN_HOME/scripts/shot_window.py" "$out/Crawler.exe" "$out/ui_face_right.png" 4.0 "$out"
```

| 脚本 | 产出 | 说明 |
|---|---|---|
| `shot_face_right.script` | `ui_face_right.png` | 先左后右，角色朝右（提灯光池在右侧） |
| `shot_face_left.script` | `ui_face_left.png` | 往左走一小段，角色朝左（光池在左侧） |
| `shot_settings.script` | `ui_settings.png` | `Esc` 打开设置浮层（皮肤包外观） |
| `shot_dungeon.script` | `ui_dungeon.png` | 地牢全景（地砖/墙/火把/迷雾/投影） |

脚本用引擎自带的 UiDriver 注入合成输入（**不移动系统鼠标**）。
⚠️ `ZAN_UI_SCRIPT` 必须是**绝对路径**：脚本路径按进程工作目录解析，相对路径
在 `build/crawler` 下找不到，驱动不会启动（画面会停在主菜单）。

## 其它运行模式

| 环境变量 | 作用 |
|---|---|
| `CRAWLER_SMOKE=1` | 冒烟模式：自动开局并自动行动，跑满 `CRAWLER_FRAMES` 帧后退出 |
| `CRAWLER_DEMO=1` | 演示模式：自动开局并自动行动，不退出（截图/录像用） |
| `CRAWLER_FRAMES=<n>` | 冒烟帧数上限（默认 90） |
| `CRAWLER_SAVE=<dir>` | 存档目录覆盖 |

## 参考源与授权边界

- **玩法范式参考**：Cataclysm-DDA 的"逐层下降 + 回合制"节奏。
- **不取用任何第三方素材**：CDDA 是 CC-BY-SA、Mindustry 是 GPLv3，传染性许可与
  本项目口径冲突。位图由 gpt-image-2.5 生成后自研加工，音效由 Python 合成。
