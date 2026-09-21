# TeleConsole one-time launcher
# Usage (PowerShell):  irm https://raw.githubusercontent.com/Damn-Man123/TeleConsole/main/install.ps1 | iex
#
# Downloads the latest TeleConsole.exe into a temporary folder (with a progress bar), verifies its
# SHA-256 checksum, runs it, and deletes everything (program + login data) when you close it.
# Nothing is installed on the computer. Shows the author's name and license notice first.
# The tool is started in your Documents folder, so any
# files it exports (for example saved member lists) are kept.

& {
    $ErrorActionPreference = 'Stop'
    $ProgressPreference    = 'SilentlyContinue'   # hides PowerShell's slow built-in bar; we draw our own
    [Net.ServicePointManager]::SecurityProtocol =
        [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    $repo = 'Damn-Man123/TeleConsole'
    $base = "https://github.com/$repo/releases/latest/download"
    $work = Join-Path $env:TEMP ('TeleConsole_run_' + [guid]::NewGuid().ToString('N'))
    $data = Join-Path $work 'data'                # login/config files live here for this run only
    $exe  = Join-Path $work 'TeleConsole.exe'

    # Builds one line of the progress bar, e.g.
    #   Downloading  [########............]  50%  12.5/25.0 MB  8.2 MB/s
    function Format-Bar([long]$Done, $Total, [double]$Secs, [string]$Label) {
        $mb    = $Done / 1MB
        $speed = $mb / [Math]::Max($Secs, 0.001)
        if ($Total) {
            $ratio  = [Math]::Min([double]$Done / [double]$Total, 1.0)
            $filled = [int][Math]::Floor($ratio * 24)
            $bar    = ([string][char]0x2588) * $filled + ([string][char]0x2591) * (24 - $filled)
            $pct    = [int][Math]::Floor($ratio * 100)
            $line   = '  {0} {1} {2,3}%  {3:N1}/{4:N1} MB  {5:N1} MB/s' -f $Label, $bar, $pct, $mb, ($Total / 1MB), $speed
        } else {
            $line   = '  {0}  {1:N1} MB  {2:N1} MB/s' -f $Label, $mb, $speed
        }
        return $line.PadRight(70)
    }

    # Streams a file to disk and redraws the progress bar on one line
    function Get-FileWithProgress([string]$Url, [string]$OutFile, [string]$Label) {
        Add-Type -AssemblyName System.Net.Http
        $client = New-Object System.Net.Http.HttpClient
        $client.Timeout = [TimeSpan]::FromMinutes(15)
        $in = $null
        $out = $null
        try {
            $resp = $client.GetAsync($Url, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
            [void]$resp.EnsureSuccessStatusCode()
            $total = $resp.Content.Headers.ContentLength
            $in    = $resp.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
            $out   = [System.IO.File]::Create($OutFile)

            $buf  = New-Object byte[] 81920
            $done = [long]0
            $sw   = [Diagnostics.Stopwatch]::StartNew()
            $last = -1000

            while ($true) {
                $n = $in.Read($buf, 0, $buf.Length)
                if ($n -le 0) { break }
                $out.Write($buf, 0, $n)
                $done += $n
                if (($sw.ElapsedMilliseconds - $last) -ge 100) {
                    $last = $sw.ElapsedMilliseconds
                    Write-Host ("`r" + (Format-Bar $done $total $sw.Elapsed.TotalSeconds $Label)) -NoNewline
                }
            }
            Write-Host ("`r" + (Format-Bar $done $total $sw.Elapsed.TotalSeconds $Label))
        }
        finally {
            if ($out) { $out.Dispose() }
            if ($in)  { $in.Dispose() }
            $client.Dispose()
        }
    }

    # Deletes a folder, retrying briefly in case antivirus is still scanning a file inside it.
    # Returns $true when the folder is gone, $false if it could not be removed.
    function Remove-Folder([string]$Path) {
        for ($i = 0; $i -lt 6; $i++) {
            if (-not (Test-Path -LiteralPath $Path)) { return $true }
            Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue
            if (-not (Test-Path -LiteralPath $Path)) { return $true }
            Start-Sleep -Milliseconds 700
        }
        return $false
    }

    # Clean up leftovers from earlier runs that were closed abruptly (older than 1 day)
    Get-ChildItem -LiteralPath $env:TEMP -Directory -Filter 'TeleConsole_run_*' -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } |
        ForEach-Object { $null = Remove-Folder $_.FullName }

    # ---------- notice ----------
    Write-Host ''
    Write-Host '  TeleConsole - created by SSSB (Jasmine)' -ForegroundColor Cyan
    Write-Host '  All rights reserved. Copying, modifying or redistributing this tool' -ForegroundColor DarkGray
    Write-Host "  without the author's permission is not allowed." -ForegroundColor DarkGray
    Write-Host ''

    # ---------- download and verify ----------
    $ready = $false
    $oldEncoding = $null
    try {
        try {
            $oldEncoding = [Console]::OutputEncoding
            [Console]::OutputEncoding = [Text.Encoding]::UTF8   # so the bar characters display correctly
        } catch { }

        New-Item -ItemType Directory -Force -Path $data | Out-Null
        $hf = Join-Path $work 'TeleConsole.exe.sha256'

        Write-Host 'Getting the latest TeleConsole...' -ForegroundColor Cyan
        Get-FileWithProgress "$base/TeleConsole.exe" $exe 'Downloading'
        Invoke-WebRequest -Uri "$base/TeleConsole.exe.sha256" -OutFile $hf -UseBasicParsing

        Write-Host '  Verifying download...' -ForegroundColor Cyan
        $expected = ((Get-Content $hf -Raw).Trim() -split '\s+')[0].ToLower()
        $actual   = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
        if ($actual -ne $expected) {
            throw 'Checksum mismatch: the download is corrupted or has been tampered with.'
        }
        Write-Host '  Ready.' -ForegroundColor Green
        $ready = $true
    }
    catch {
        Write-Host "TeleConsole download failed: $($_.Exception.Message)" -ForegroundColor Red
    }
    finally {
        if ($oldEncoding) { try { [Console]::OutputEncoding = $oldEncoding } catch { } }
    }

    if (-not $ready) {
        $null = Remove-Folder $work
        return
    }

    # ---------- run, then delete everything ----------
    # Start the tool in Documents so files it saves (e.g. member lists) are not deleted with the temp folder
    $startDir = [Environment]::GetFolderPath('MyDocuments')
    if (-not $startDir -or -not (Test-Path -LiteralPath $startDir)) { $startDir = $HOME }

    $oldAppData = $env:APPDATA
    try {
        $env:APPDATA = $data                 # the app saves its login files under APPDATA, so they land in our temp folder
        $env:TELECONSOLE_TEMP = '1'          # tells the app this is a one-time run
        Push-Location $startDir
        try { & $exe } finally { Pop-Location }
    }
    catch {
        Write-Host "Could not start TeleConsole: $($_.Exception.Message)" -ForegroundColor Red
    }
    finally {
        $env:APPDATA = $oldAppData
        Remove-Item Env:\TELECONSOLE_TEMP -ErrorAction SilentlyContinue
        if (Remove-Folder $work) {
            Write-Host 'Temporary files removed.' -ForegroundColor DarkGray
        } else {
            Write-Host "Could not remove everything. Delete this folder yourself: $work" -ForegroundColor Yellow
        }
    }
}