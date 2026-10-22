# 地底爬行 · CRAWLER

> 回合制 Roguelike 地牢探索：往地底深处钻，抵达第 5 层即胜利，血掉光即失败。

用 [Zan](https://github.com/joyspinch/zan-lang) 语言写的独立游戏项目（仓库根自带 git 仓库）。完整设计与实现说明见 [`PROJECT.md`](PROJECT.md)。

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

## 构建

需要 [zan-lang](https://github.com/joyspinch/zan-lang) 仓库（`zanc` 编译器、公共包与 stdlib 都在里面）：

```powershell
git clone https://github.com/joyspinch/zan-lang.git
$env:ZAN_HOME = 'D:/path/to/zan-lang'   # 指到刚克隆的 zan-lang 仓库根

pwsh -File client/tools/build.ps1
```

产物：`build/crawler/Crawler.exe`（运行目录要带上它旁边的 `assets/` 与 `skins/`）。

## 运行

```powershell
cd build/crawler
.\Crawler.exe
```

## 测试

```powershell
pwsh -File client/tools/test.ps1
```

## 目录结构

```
crawler/
client/
  src/      # 游戏源码（.zan 源码 + HTML 界面设计稿）
  assets/   # 位图 / 音频素材
  data/     # 数值表与数据文件
  tests/    # 玩法断言用例
  tools/    # 构建与测试脚本
PROJECT.md
```

## 素材与授权

- 素材清单与授权说明见 [`client/ASSETS.md`](client/ASSETS.md)。

## 许可

本仓库采用 [MIT 许可](LICENSE)。依赖的 zan-lang 仓库采用 ZCSL（Zan Community Source License 1.0）。

## 更多文档

- [`PROJECT.md`](PROJECT.md) —— 完整设计与实现说明
- [`client/ASSETS.md`](client/ASSETS.md) —— 素材清单
