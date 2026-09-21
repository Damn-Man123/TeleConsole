# TeleConsole installer / launcher
# Usage (PowerShell):  irm https://raw.githubusercontent.com/Damn-Man123/TeleConsole/main/install.ps1 | iex
#
# What it does: downloads the latest TeleConsole.exe from GitHub Releases,
# checks its SHA-256 checksum, saves it to %LOCALAPPDATA%\TeleConsole and runs it.

& {
    $ErrorActionPreference = 'Stop'
    $ProgressPreference    = 'SilentlyContinue'   # much faster downloads on Windows PowerShell 5.1
    [Net.ServicePointManager]::SecurityProtocol =
        [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    $repo = 'Damn-Man123/TeleConsole'                   # <-- change this
    $base = "https://github.com/$repo/releases/latest/download"
    $dir  = Join-Path $env:LOCALAPPDATA 'TeleConsole'
    $exe  = Join-Path $dir 'TeleConsole.exe'
    $tmp  = Join-Path $env:TEMP ('TeleConsole_' + [guid]::NewGuid().ToString('N'))

    try {
        New-Item -ItemType Directory -Force -Path $dir, $tmp | Out-Null
        $dl = Join-Path $tmp 'TeleConsole.exe'
        $hf = Join-Path $tmp 'TeleConsole.exe.sha256'

        Write-Host 'Downloading TeleConsole...' -ForegroundColor Cyan
        Invoke-WebRequest -Uri "$base/TeleConsole.exe"        -OutFile $dl -UseBasicParsing
        Invoke-WebRequest -Uri "$base/TeleConsole.exe.sha256" -OutFile $hf -UseBasicParsing

        $expected = ((Get-Content $hf -Raw).Trim() -split '\s+')[0].ToLower()
        $actual   = (Get-FileHash $dl -Algorithm SHA256).Hash.ToLower()
        if ($actual -ne $expected) {
            throw 'Checksum mismatch: the download is corrupted or has been tampered with.'
        }

        try {
            Copy-Item $dl $exe -Force
        } catch {
            throw 'Could not update TeleConsole.exe. Close any running TeleConsole window and try again.'
        }
    }
    catch {
        Write-Host "TeleConsole install failed: $($_.Exception.Message)" -ForegroundColor Red
        return
    }
    finally {
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }

    # Run from the app folder so session/config files are kept in one place
    Push-Location $dir
    try { & $exe } finally { Pop-Location }
}
