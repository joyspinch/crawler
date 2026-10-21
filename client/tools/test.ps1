# 地底爬行 · CRAWLER 测试：三段全绿才算过。
#
#   1) crawler_test_OK      玩法断言用例（地图/移动/视野/战斗/物品/楼层/结算）
#   2) crawler_SAVE_OK      存档两遍：新进程读回上一遍写的档（局数 1 -> 2）
#   3) crawler_SMOKE_OK     无头冒烟：跑满 N 帧后程序自行退出
#
# 判据：每段都有明确标记输出；任何一段缺标记即判失败。
param(
    [string]$Compiler = $env:ZANC,
    [string]$PackageProject = '',
    [int]$TimeoutSeconds = 120
)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$repo = Split-Path -Parent $project
. (Join-Path $PSScriptRoot 'toolchain.ps1')
$tc = Resolve-CrawlerToolchain -Compiler $Compiler -PackageProject $PackageProject
$Compiler = $tc.Compiler
$PackageProject = $tc.PackageProject
$out = Join-Path $repo 'build/crawler'
& (Join-Path $PSScriptRoot 'build.ps1') -Compiler $Compiler -PackageProject $PackageProject -Output $out
$exe = Join-Path $out 'Crawler.exe'
if (-not (Test-Path $exe)) { throw "缺少可执行文件：$exe" }

# --- 第一段：玩法断言用例 ---
# 源码要排除 main.zan（它带 Main()，用例自己的 Main 才是入口）。
$caseSources = @(Get-ChildItem (Join-Path $project 'src') -Recurse -File -Filter *.zan |
    Where-Object { $_.Name -ne 'main.zan' } |
    Sort-Object FullName | ForEach-Object { $_.FullName })
$case = 'crawler_test.zan'
$stem = [IO.Path]::GetFileNameWithoutExtension($case)
$caseExe = Join-Path $out "$stem.exe"
$caseArgs = @((Join-Path $project "tests/$case")) + $caseSources +
    @('--auto-stdlib', '--package-project', $PackageProject)
if ($tc.Stdlib) { $caseArgs += @('--stdlib-path', $tc.Stdlib) }
$caseArgs += @('-o', $caseExe)
& $Compiler @caseArgs
if ($LASTEXITCODE -ne 0) { throw "玩法用例编译失败：$case (zanc=$LASTEXITCODE)" }
$caseOut = & $caseExe 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { throw "玩法用例运行失败：$case`n$caseOut" }
if ($caseOut -notmatch "$stem OK") { throw "玩法用例输出不对：$case`n$caseOut" }
Write-Host $caseOut.Trim()
Write-Host "crawler_test_OK"

# --- 第二段 + 第三段：存档两遍 + 无头冒烟 ---
# 存档落在临时目录里，不碰玩家机器上的 %LOCALAPPDATA%/Crawler。
$saveDir = Join-Path $out 'savetest'
if (Test-Path $saveDir) { Remove-Item $saveDir -Recurse -Force }
New-Item -ItemType Directory -Force $saveDir | Out-Null
$env:CRAWLER_SAVE = $saveDir
# 冒烟标记：跑满 N 帧后程序自行退出（不走 UiDriver 脚本，避免桌面事件污染）
$env:CRAWLER_SMOKE = '1'
$env:CRAWLER_FRAMES = '1500'
$log = Join-Path $out 'crawler_smoke.log'
if (Test-Path $log) { Remove-Item $log -Force }
$proc = Start-Process -FilePath $exe -WorkingDirectory $out -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $log -RedirectStandardError (Join-Path $out 'crawler_smoke.err')
if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    $proc.Kill()
    throw "无头冒烟超时：应用没在 $TimeoutSeconds 秒内退出"
}
if ($proc.ExitCode -ne 0) { throw "无头冒烟失败：exit=$($proc.ExitCode)`n$(Get-Content $log -Raw)" }
if (-not (Select-String -Path $log -Pattern 'CRAWLER_SMOKE_OK' -Quiet)) {
    throw "无头冒烟未收尾（缺 CRAWLER_SMOKE_OK）：$log"
}
# 存档落盘 + 读回：第二遍是新进程，必须读回第一遍写的档（局数 1 -> 2）。
$saveLine = Select-String -Path $log -Pattern 'CRAWLER_SAVE' | Select-Object -First 1
if (-not $saveLine) { throw "没有存档输出行（CRAWLER_SAVE）：$log" }
if ($saveLine.Line -notmatch 'runs=1') {
    throw "第一遍存档没写成局数 1：$($saveLine.Line)"
}
if (-not (Test-Path (Join-Path $saveDir 'crawler_slot0.json'))) {
    throw "存档文件没落盘：$saveDir"
}
$log2 = Join-Path $out 'crawler_smoke2.log'
if (Test-Path $log2) { Remove-Item $log2 -Force }
$proc2 = Start-Process -FilePath $exe -WorkingDirectory $out -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $log2 -RedirectStandardError (Join-Path $out 'crawler_smoke2.err')
if (-not $proc2.WaitForExit($TimeoutSeconds * 1000)) {
    $proc2.Kill()
    throw "第二遍无头冒烟超时"
}
if ($proc2.ExitCode -ne 0) { throw "第二遍无头冒烟失败：exit=$($proc2.ExitCode)`n$(Get-Content $log2 -Raw)" }
if (-not (Select-String -Path $log2 -Pattern 'CRAWLER_SMOKE_OK' -Quiet)) {
    throw "第二遍无头冒烟未收尾（缺 CRAWLER_SMOKE_OK）：$log2"
}
$saveLine2 = Select-String -Path $log2 -Pattern 'CRAWLER_SAVE' | Select-Object -First 1
if (-not $saveLine2 -or $saveLine2.Line -notmatch 'runs=2') {
    throw "第二遍没读回上一遍的存档（期望 runs=2）：$($saveLine2.Line)"
}
Write-Host "crawler_SAVE_OK runs=1 -> runs=2"
Write-Host "crawler_SMOKE_OK"
Write-Host "--- 第一遍存档行：$($saveLine.Line.Trim())"
Write-Host "--- 第二遍存档行：$($saveLine2.Line.Trim())"
