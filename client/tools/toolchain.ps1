# 共享：定位 zanc 编译器 / stdlib / 公共包根。
#
# 项目搬到仓库外后，公共包在 zan-lang 仓库（或它的干净 worktree）的
# packages/ 下；编译要带 --package-project 指向包根。定位顺序：
#   编译器：显式参数 → $ZANC → $ZAN_HOME → PATH → 包根附近
#   stdlib：显式参数 → $ZAN_STDLIB → $ZAN_HOME/stdlib → 包根/stdlib
#   包根  ：显式参数 → $ZAN_HOME
function Resolve-CrawlerToolchain {
    param(
        [string]$Compiler = '',
        [string]$Stdlib = '',
        [string]$PackageProject = '',
        [string[]]$CompilerRoots = @()
    )
    if (-not $PackageProject) {
        if ($env:ZAN_HOME) { $PackageProject = $env:ZAN_HOME }
    }
    $candidates = @()
    if ($Compiler) { $candidates += $Compiler }
    if ($env:ZANC) { $candidates += $env:ZANC }
    if ($env:ZAN_HOME) { $candidates += (Join-Path $env:ZAN_HOME 'build/zanc.exe') }
    try { $candidates += (Get-Command zanc -ErrorAction Stop).Source } catch { }
    $roots = @()
    if ($PackageProject) {
        $roots += $PackageProject
        $roots += (Split-Path -Parent $PackageProject)
    }
    $roots += $CompilerRoots
    foreach ($r in $roots) {
        if ($r) { $candidates += (Join-Path $r 'build/zanc.exe') }
    }
    $resolvedCompiler = ''
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { $resolvedCompiler = (Resolve-Path $c).Path; break }
    }
    if (-not $resolvedCompiler) {
        throw '找不到 zanc 编译器：请用 -Compiler <zanc.exe> 指定，或设置 $env:ZAN_HOME 指向 zan-lang 仓库。'
    }
    if (-not $Stdlib) {
        $stdlibCandidates = @()
        if ($env:ZAN_STDLIB) { $stdlibCandidates += $env:ZAN_STDLIB }
        if ($env:ZAN_HOME) { $stdlibCandidates += (Join-Path $env:ZAN_HOME 'stdlib') }
        if ($PackageProject) {
            $stdlibCandidates += (Join-Path $PackageProject 'stdlib')
            $stdlibCandidates += (Join-Path (Split-Path -Parent $PackageProject) 'stdlib')
        }
        foreach ($s in $stdlibCandidates) {
            if ($s -and (Test-Path $s)) { $Stdlib = (Resolve-Path $s).Path; break }
        }
    }
    if (-not $PackageProject) {
        throw '需要 -PackageProject 指向含 packages/ 的 zan-lang 仓库（或 $env:ZAN_HOME）'
    }
    if (-not (Test-Path (Join-Path $PackageProject 'packages'))) {
        throw "公共包根不对（没有 packages/ 目录）：$PackageProject"
    }
    return @{
        Compiler = $resolvedCompiler
        Stdlib = $Stdlib
        PackageProject = $PackageProject
    }
}
