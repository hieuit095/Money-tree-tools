$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Convert-ToWslPath {
    param(
        [Parameter(Mandatory = $true)]
        [string] $WindowsPath
    )

    $full = [System.IO.Path]::GetFullPath($WindowsPath)
    if ($full.Length -lt 3 -or $full[1] -ne ":" -or $full[2] -ne "\") {
        throw "Unsupported Windows path format: $full"
    }

    $drive = $full.Substring(0, 1).ToLowerInvariant()
    $rest = $full.Substring(2) -replace "\\", "/"
    return "/mnt/$drive$rest"
}

function Escape-BashSingleQuoted {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Value
    )
    return $Value -replace "'", "'\\''"
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($IsLinux) {
    & bash (Join-Path $repoRoot "install.sh")
    exit $LASTEXITCODE
}

if ($IsMacOS) {
    throw "This installer targets Debian/Ubuntu Linux. Use a Linux host or WSL2."
}

if (-not $IsWindows) {
    throw "Unsupported OS. This installer targets Debian/Ubuntu Linux."
}

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw "wsl.exe not found. Install WSL2 (Ubuntu recommended) or run install.sh on a Debian/Ubuntu Linux host."
}

$setupSh = Join-Path $repoRoot "setup.sh"
if (-not (Test-Path $setupSh)) {
    throw "setup.sh not found in repo root: $repoRoot"
}

$wslRepoRoot = Convert-ToWslPath -WindowsPath $repoRoot
$wslRepoRootEscaped = Escape-BashSingleQuoted -Value $wslRepoRoot
$bashCmd = "cd '$wslRepoRootEscaped' && sudo bash ./setup.sh"

& wsl.exe -e bash -lc $bashCmd
exit $LASTEXITCODE
