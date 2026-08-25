[CmdletBinding()]
param(
    [string]$SourceCommit = $env:SOURCE_COMMIT
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if ([string]::IsNullOrWhiteSpace($SourceCommit)) {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($null -ne $git) {
        try { $SourceCommit = (& git -C $root rev-parse HEAD).Trim() } catch { $SourceCommit = $null }
    }
}
if ($SourceCommit -notmatch '^[0-9a-fA-F]{40}$') {
    throw "A full 40-character source commit is required before recording native Windows PASS evidence."
}
$SourceCommit = $SourceCommit.ToLowerInvariant()

$temp = Join-Path ([System.IO.Path]::GetTempPath()) ("Production Site Autopilot Юникод " + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    & (Join-Path $root "installers\install.ps1") -ProjectPath $temp
    & (Join-Path $root "installers\install.ps1") -ProjectPath $temp -Doctor | Out-Null
    & (Join-Path $root "installers\install.ps1") -ProjectPath $temp
    & (Join-Path $root "installers\install.ps1") -ProjectPath $temp -Uninstall
    if (Test-Path (Join-Path $temp ".codex\skills\production-site-autopilot")) {
        throw "Uninstall did not remove managed Skill"
    }
    @{
        schema_version = "1.0"
        check = "native-windows-runtime"
        status = "PASS"
        required_for_stable = $true
        source_commit = $SourceCommit
        reason = "Native Windows installer lifecycle completed locally."
        scenarios = @("powershell-installer", "path-with-spaces", "unicode-path", "upgrade", "doctor", "uninstall")
    } | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $root "evidence\windows-native.json") -Encoding utf8
}
finally {
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
