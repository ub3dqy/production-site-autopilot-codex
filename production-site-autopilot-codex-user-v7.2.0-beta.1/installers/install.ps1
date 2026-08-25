[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Position = 0)]
    [string]$ProjectPath = ".",
    [switch]$Uninstall,
    [switch]$Doctor
)

$ErrorActionPreference = "Stop"
$source = (Resolve-Path (Join-Path $PSScriptRoot "..\plugin\skills\production-site-autopilot")).Path
if ([string]::IsNullOrWhiteSpace($ProjectPath)) { $ProjectPath = "." }
$project = (Resolve-Path $ProjectPath).Path
$target = Join-Path $project ".codex\skills\production-site-autopilot"
$marker = Join-Path $target ".production-site-autopilot-install.json"

function Assert-NoReparsePoint([string]$Path) {
    $cursor = Get-Item $project
    $relative = [System.IO.Path]::GetRelativePath($project, $Path)
    foreach ($part in $relative.Split([System.IO.Path]::DirectorySeparatorChar)) {
        if ([string]::IsNullOrWhiteSpace($part)) { continue }
        $next = Join-Path $cursor.FullName $part
        $cursor = Get-Item -LiteralPath $next -ErrorAction SilentlyContinue
        if ($null -ne $cursor -and ($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Refusing reparse-point installation path: $($cursor.FullName)"
        }
    }
}

if ($Doctor) {
    [pscustomobject]@{
        Project = $project
        SourceExists = Test-Path $source
        Installed = Test-Path $marker
        Target = $target
        PowerShell = $PSVersionTable.PSVersion.ToString()
    } | ConvertTo-Json
    exit 0
}

if ($Uninstall) {
    if (-not (Test-Path $marker)) { throw "Managed installation marker not found; refusing to remove $target" }
    if ($PSCmdlet.ShouldProcess($target, "Remove managed Production Site Autopilot Skill")) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
    exit 0
}

$parent = Split-Path $target -Parent
New-Item -ItemType Directory -Force -Path $parent | Out-Null
Assert-NoReparsePoint $parent
if (Test-Path $target) {
    $stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
    $backup = "$target.backup-$stamp"
    if ($PSCmdlet.ShouldProcess($target, "Back up existing installation to $backup")) {
        Move-Item -LiteralPath $target -Destination $backup
    }
}
if ($PSCmdlet.ShouldProcess($target, "Install Production Site Autopilot Skill")) {
    Copy-Item -LiteralPath $source -Destination $target -Recurse
    @{
        schema_version = "1.0"
        installed_at = (Get-Date).ToUniversalTime().ToString("o")
        source = $source
        version = (Get-Content (Join-Path $PSScriptRoot "..\VERSION") -Raw).Trim()
    } | ConvertTo-Json | Set-Content -LiteralPath $marker -Encoding UTF8
}
Write-Host "Installed: $target"
