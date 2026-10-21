# 地底爬行 · CRAWLER 构建：编译 client/src/ 下全部 .zan → 可执行文件。
#
# 公共包（Gui / Game.Kit / Game.Foundation …）住在 zan-lang 仓库的
# packages/ 下，编译要带 --package-project 指向包根：仓库内 = 仓库根；
# 项目搬到仓库外后 = zan-lang 仓库（或它的干净 worktree），由
# -PackageProject / $ZAN_HOME 指定。
#
# assets/ 由 zanc 自动内嵌进 exe（入口源文件带目录前缀时才会定位到），
# 这里再在 exe 旁留一份磁盘副本——运行时磁盘优先，换图即生效。
param(
    [string]$Compiler = $env:ZANC,
    [string]$Stdlib = $env:ZAN_STDLIB,
    [string]$Output = '',
    [string]$PackageProject = '',
    # 找不到编译器时额外去哪里找（<root>\build\zanc.exe）
    [string[]]$CompilerRoots = @(),
    # 透传给 zanc 的额外参数（如 --publish --target android-arm64 ...）
    [string[]]$ZancArgs = @()
)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$repo = Split-Path -Parent $project

# --- 定位编译器 / stdlib / 公共包根（见 toolchain.ps1）---------------------
. (Join-Path $PSScriptRoot 'toolchain.ps1')
$tc = Resolve-CrawlerToolchain -Compiler $Compiler -Stdlib $Stdlib `
    -PackageProject $PackageProject -CompilerRoots $CompilerRoots
$Compiler = $tc.Compiler
$Stdlib = $tc.Stdlib
$PackageProject = $tc.PackageProject

if (-not $Output) { $Output = Join-Path $repo 'build/crawler' }
$Output = [IO.Path]::GetFullPath($Output)
New-Item -ItemType Directory -Force -Path $Output | Out-Null

# 入口 main.zan 必须排第一：zanc 只把 Main() 给第一个编译输入
# （genrun.c 的 emitMain=paths[0]）。其余 .zan 递归枚举——zanc 不会自动
# 带上同目录的其它文件，少传一个就是 "undefined type"。
$entry = Join-Path $project 'src/main.zan'
$sources = @()
if (Test-Path $entry) { $sources += $entry }
$sources += @(Get-ChildItem (Join-Path $project 'src') -Recurse -File -Filter *.zan |
    Where-Object { $_.FullName -ne $entry } | Sort-Object FullName | ForEach-Object { $_.FullName })
$zargs = @($sources) + @('--auto-stdlib', '--package-project', $PackageProject)
if ($Stdlib) { $zargs += @('--stdlib-path', $Stdlib) }
if ($ZancArgs) { $zargs += $ZancArgs }
$exe = Join-Path $Output 'Crawler.exe'
$zargs += @('-o', $exe)
& $Compiler @zargs
if ($LASTEXITCODE -ne 0) { throw "zanc failed ($LASTEXITCODE)" }

# 音效与贴图：磁盘副本（运行时磁盘优先，替换即生效）。
$assets = Join-Path $project 'assets'
if (Test-Path $assets) { Copy-Item $assets $Output -Recurse -Force }
# 皮肤包必须与 exe 同级：build/crawler/skins/crawler/skin.css
# （Gui.Styling.Skin.Roots 查的是 exe 同级 skins/ 与 assets/skins/，
# 前者优先；assets/ 下那份是发布内嵌用的备份）。
$skinSrc = Join-Path $assets 'skins/crawler'
if (Test-Path $skinSrc) {
    $skinDst = Join-Path $Output 'skins/crawler'
    New-Item -ItemType Directory -Force -Path $skinDst | Out-Null
    Copy-Item (Join-Path $skinSrc '*') $skinDst -Recurse -Force
}

# 控件基线 base.css **不在这里拷**：zanc 会自动内嵌 stdlib 的 Gui 皮肤基线
# （含 base.css 与 dark/light——见 src/compiler/main.c 的 skins 自动内嵌分支；
# embedres 的过滤器只作用于 depth-1 的皮肤包目录，base.css 是文件照内嵌）。
# 运行时 Gui 也是磁盘优先、内嵌兜底（Gui.Styling.Skin.BaseCss），所以 exe 旁
# 不必再放一份 base.css——省掉它还免了"磁盘旧基线盖住 exe 内嵌新基线"的漂移。
# 只有"整体替换基线"（自带完整 base.css 替身）才会让编译器跳过基线自动内嵌。
# 清掉旧版遗留的磁盘 base.css（老构建拷过一份）：留着会盖住 exe 内嵌的
# 基线，让"内嵌兜底到底有没有生效"这件事永远测不出来。
$staleBase = Join-Path $Output 'skins/base.css'
if (Test-Path $staleBase) { Remove-Item $staleBase -Force }
Write-Host "Built $exe  (compiler=$Compiler  packages=$PackageProject  stdlib=$Stdlib)"
