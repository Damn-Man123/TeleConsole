# TeleConsole installer / launcher
# Usage (PowerShell):  irm https://raw.githubusercontent.com/Damn-Man123/TeleConsole/main/install.ps1 | iex
#
# Downloads the latest TeleConsole.exe from GitHub Releases (with a progress bar),
# checks its SHA-256 checksum, saves it to %LOCALAPPDATA%\TeleConsole and runs it.

& {
    $ErrorActionPreference = 'Stop'
    $ProgressPreference    = 'SilentlyContinue'   # hides PowerShell's slow built-in bar; we draw our own
    [Net.ServicePointManager]::SecurityProtocol =
        [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    $repo = 'Damn-Man123/TeleConsole'
    $base = "https://github.com/$repo/releases/latest/download"
    $dir  = Join-Path $env:LOCALAPPDATA 'TeleConsole'
    $exe  = Join-Path $dir 'TeleConsole.exe'
    $tmp  = Join-Path $env:TEMP ('TeleConsole_' + [guid]::NewGuid().ToString('N'))

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

    $oldEncoding = $null
    try {
        try {
            $oldEncoding = [Console]::OutputEncoding
            [Console]::OutputEncoding = [Text.Encoding]::UTF8   # so the bar characters display correctly
        } catch { }

        New-Item -ItemType Directory -Force -Path $dir, $tmp | Out-Null
        $dl = Join-Path $tmp 'TeleConsole.exe'
        $hf = Join-Path $tmp 'TeleConsole.exe.sha256'

        Write-Host 'Getting the latest TeleConsole...' -ForegroundColor Cyan
        Get-FileWithProgress "$base/TeleConsole.exe" $dl 'Downloading'
        Invoke-WebRequest -Uri "$base/TeleConsole.exe.sha256" -OutFile $hf -UseBasicParsing

        Write-Host '  Verifying download...' -ForegroundColor Cyan
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
        Write-Host '  Ready.' -ForegroundColor Green
    }
    catch {
        Write-Host "TeleConsole install failed: $($_.Exception.Message)" -ForegroundColor Red
        return
    }
    finally {
        if ($oldEncoding) { try { [Console]::OutputEncoding = $oldEncoding } catch { } }
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }

    # Run from the app folder so session/config files are kept in one place
    Push-Location $dir
    try { & $exe } finally { Pop-Location }
}