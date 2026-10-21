# 灰烬地窟 —— 2D 回合制地牢探索

> 本文件是 crawler 项目的落地说明。**素材清单见 `client/ASSETS.md`**，全局规格见工作区根的 `ASSET-PIPELINE.md`。

## 参考源与授权边界

- **参考**：Cataclysm-DDA（`CleverRaven/Cataclysm-DDA`）
- **抄什么**：抄回合制回合、属性/状态效果、物品栏与装备、程序化地牢生成、线索与解锁。瓦片与图标自研。

**红线与差异**：

- CDDA 素材是 CC-BY-SA，**整体打包前须逐件核对**；本项目像素全部重画。
- 不抄 CDDA 的 JSON 配方/物品定义文本（属受版权保护的内容）；只借鉴数据形状与属性分层思路。
- 不引入 CDDA 的真实枪械/药物数据库，避免题材与合规风险。

## 渲染路线

2D 贴图批 + 视口裁剪。瓦片 32×32、怪物 4 帧、物品图标 32×32。

## 目录

    crawler/
      client/       src/ 源码、assets/ 素材、data/ 数据、skins/ 皮肤、tools/ 脚本、tests/ 用例
      build/        编译产物（不入库）

所有命令都在**项目根**下执行（路径相对项目根）。

## 编译

```powershell
$env:ZAN_HOME = 'D:/project/zan-lang'   # 编译器与 stdlib 同源；公共包在它的 packages/ 下
pwsh -File client/tools/build.ps1
```

ZAN_HOME 指向 zan-lang 仓库时用它的 `build/zanc.exe` 与 `stdlib/`；不设则用 PATH 上的 `zanc`。
编译时加 `--package-project $env:ZAN_HOME` 可直接吃仓库里的 `packages/`。

## 测试

```powershell
pwsh -File client/tools/test.ps1     # 无头冒烟：跑满 90 帧后自行退出
```

工作区批量冒烟：在 zan-lang 仓库侧跑 `pwsh -File scripts/smoke_all_game_projects.ps1`（一次跑完仓库外全部游戏项目）。

## 当前状态

骨架可编译可运行（90 帧无头冒烟通过）：回合制地牢、属性面板、程序化房间生成。

## 后续（按优先级）

1. 接入真实位图 sprite 与音效（素材见 `client/ASSETS.md`）。
2. 补玩法深度：参照源的关卡/数值/AI 三个维度逐项对齐。
3. 需要时再评估联网（`legend` 有服务端可参考）。