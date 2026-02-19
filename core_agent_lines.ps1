$ErrorActionPreference = "Stop"

# Count core agent lines (excluding channels/, cli/, providers/ adapters)
Set-Location -Path $PSScriptRoot

function Get-WcLineCount {
    param(
        [string[]]$Paths
    )

    $total = 0
    foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path)) {
            continue
        }
        $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $path))
        foreach ($b in $bytes) {
            if ($b -eq 10) {
                $total++
            }
        }
    }
    return $total
}

Write-Output "nanobot core agent line count"
Write-Output "================================"
Write-Output ""

# NOTE: each entry is scanned non-recursively (Get-ChildItem -File, no -Recurse).
# All subdirectories containing .py files must be listed here explicitly
# (e.g. "agent/tools" alongside "agent") so per-directory totals still sum to
# the overall total.  If a new nested package is added, add it to this list too.
$dirs = @("agent", "agent/tools", "bus", "config", "cron", "heartbeat", "session", "utils")

foreach ($dir in $dirs) {
    $path = Join-Path "nanobot" $dir
    $files = Get-ChildItem -Path $path -File -Filter "*.py" -ErrorAction SilentlyContinue
    $count = if ($files) { Get-WcLineCount -Paths $files.FullName } else { 0 }
    Write-Output ("  {0,-16} {1,5} lines" -f "$dir/", $count)
}

$rootFiles = @("nanobot/__init__.py", "nanobot/__main__.py")
$root = Get-WcLineCount -Paths $rootFiles
Write-Output ("  {0,-16} {1,5} lines" -f "(root)", $root)

Write-Output ""
$totalFiles = Get-ChildItem -Path "nanobot" -Recurse -File -Filter "*.py" | Where-Object {
    $_.FullName -notmatch "[\\/](channels|cli|providers)[\\/]"
}
$total = if ($totalFiles) { Get-WcLineCount -Paths $totalFiles.FullName } else { 0 }
Write-Output "  Core total:     $total lines"
Write-Output ""
Write-Output "  (excludes: channels/, cli/, providers/)"