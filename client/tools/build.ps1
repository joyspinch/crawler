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
Write-Host "Built $exe  (compiler=$Compiler  packages=$PackageProject  stdlib=$Stdlib)"
