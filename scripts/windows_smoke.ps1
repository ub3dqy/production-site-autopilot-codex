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

$py = Get-Command py -ErrorAction SilentlyContinue
$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $py -and $null -eq $python) { throw "Python 3 is required for runtime validation." }

function Invoke-AutopilotRuntime([string]$Runner, [string[]]$Arguments) {
    if ($null -ne $py) {
        & $py.Source -3 $Runner @Arguments
    }
    else {
        & $python.Source $Runner @Arguments
    }
    if ($LASTEXITCODE -ne 0) { throw "Bundled runtime failed with exit code $LASTEXITCODE" }
}

$temp = Join-Path ([System.IO.Path]::GetTempPath()) ("Production Site Autopilot Юникод " + [guid]::NewGuid().ToString("N"))
$mappedDrive = $null
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    $project = Join-Path $temp "CMD Project Юникод"
    New-Item -ItemType Directory -Path $project | Out-Null
    $launcher = Join-Path $root "installers\START_SITE_AUTOPILOT_WINDOWS.cmd"
    $commandLine = '"{0}" "{1}"' -f $launcher, $project
    & $env:ComSpec /d /s /c $commandLine
    if ($LASTEXITCODE -ne 0) { throw "CMD launcher failed with exit code $LASTEXITCODE" }

    $runner = Join-Path $project ".codex\skills\production-site-autopilot\run.py"
    if (-not (Test-Path $runner)) { throw "Bundled runtime runner is missing after installation" }
    Invoke-AutopilotRuntime $runner @("--version")
    Invoke-AutopilotRuntime $runner @("doctor", $project)

    & (Join-Path $root "installers\install.ps1") -ProjectPath $project -Doctor | Out-Null
    & (Join-Path $root "installers\install.ps1") -ProjectPath $project
    & (Join-Path $root "installers\install.ps1") -ProjectPath $project -Uninstall
    if (Test-Path (Join-Path $project ".codex\skills\production-site-autopilot")) {
        throw "Uninstall did not remove managed Skill"
    }

    $freeLetter = $null
    foreach ($code in 90..68) {
        $letter = [char]$code
        if (-not (Test-Path ("{0}:\" -f $letter))) { $freeLetter = $letter; break }
    }
    if ($null -eq $freeLetter) { throw "No free drive letter is available for the non-system-drive scenario" }
    $mappedRoot = Join-Path $temp "Mapped Root"
    New-Item -ItemType Directory -Path $mappedRoot | Out-Null
    $mappedDrive = "${freeLetter}:"
    & $env:ComSpec /d /c "subst $mappedDrive `"$mappedRoot`""
    if ($LASTEXITCODE -ne 0) { throw "subst failed with exit code $LASTEXITCODE" }
    $mappedProject = Join-Path "$mappedDrive\" "Project Юникод"
    New-Item -ItemType Directory -Path $mappedProject | Out-Null
    & (Join-Path $root "installers\install.ps1") -ProjectPath $mappedProject
    $mappedRunner = Join-Path $mappedProject ".codex\skills\production-site-autopilot\run.py"
    Invoke-AutopilotRuntime $mappedRunner @("doctor", $mappedProject)
    & (Join-Path $root "installers\install.ps1") -ProjectPath $mappedProject -Uninstall

    @{
        schema_version = "1.0"
        check = "native-windows-runtime"
        status = "PASS"
        required_for_stable = $true
        source_commit = $SourceCommit
        reason = "Native Windows CMD, PowerShell, bundled runtime, and mapped-drive lifecycle completed locally."
        scenarios = @("cmd-launcher", "powershell-installer", "path-with-spaces", "unicode-path", "non-system-drive", "upgrade", "doctor", "uninstall")
    } | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $root "evidence\windows-native.json") -Encoding utf8
}
finally {
    if ($null -ne $mappedDrive) {
        & $env:ComSpec /d /c "subst $mappedDrive /d" | Out-Null
    }
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
