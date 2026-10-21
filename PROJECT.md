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
    src/          玩法与渲染代码（9 个 .zan）
    assets/       11 张位图 + assets/sfx/ 14 个音效
    tests/        crawler_test.zan（106 条玩法断言）
    tools/        build.ps1 / test.ps1 / toolchain.ps1
  build/          编译产物（不入库）
  _scratch/       一次性脚本与探针（不入库）
```

### 模块

| 文件 | 职责 |
|---|---|
| `main.zan` | GuiHost 入口 |
| `CrawlerApp.zan` | 帧循环、输入（持续方向键 + 离散动作）、菜单/结算按钮 |
| `CrawlerGame.zan` | 玩法核心：状态机（菜单/游戏中/结算）、回合、拾取、下潜、死亡/通关 |
| `CrawlerMap.zan` | 种子化地图生成、视野（迷雾）、连通性、**BFS 寻路** |
| `CrawlerEntities.zan` | 敌人/物品数值表与实体 |
| `CrawlerCombat.zan` | 回合制战斗（攻击 / 反击 / 逃跑） |
| `CrawlerView.zan` | 渲染：位图贴图、迷雾、HUD、菜单、结算面板 |
| `CrawlerSfx.zan` | 音效事件 → WAV（走公共包 `Game.Foundation.SfxBank`） |
| `GameShell.zan` | 存档（最深层数/累计金币/累计击杀/通关次数/局数）+ 设置浮层 |

## 编译

```powershell
pwsh -File client/tools/build.ps1 -PackageProject D:\project\zan-head
```

`-PackageProject` 指向含 `packages/` 的 zan-lang 仓库（或它的干净 worktree）。
不传时按 `$ZAN_HOME` → 参数 → 已知仓库位置找编译器与 stdlib
（见 `client/tools/toolchain.ps1`）。

产物：`build/crawler/Crawler.exe`（素材同时内嵌进 exe 与磁盘副本，磁盘优先）。

## 测试

```powershell
pwsh -File client/tools/test.ps1 -PackageProject D:\project\zan-head
```

三段全绿才算过：

1. `crawler_test_OK` —— 106 条玩法断言（地图可达性 / 同种子可复现 / 撞墙不移动 /
   视野半径 / 战斗扣血与击杀 / 药水不超上限 / 拾取计数 / 楼梯下潜重建 /
   死亡进结算 / 三个种子跑完整流程状态自洽）。
2. `crawler_SAVE_OK runs=1 -> runs=2` —— 存档写两遍，新进程读回上一遍的档。
3. `crawler_SMOKE_OK` —— 无头冒烟：自动打完一整局（会真的下潜、打怪、通关）后退出。

存档目录默认 `%LOCALAPPDATA%/Crawler`；测试用 `CRAWLER_SAVE` 指到临时目录。

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
