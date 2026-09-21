# TeleConsole

A menu-driven Telegram console tool for Windows, built on [Telethon](https://github.com/LonamiWebs/Telethon). It runs in PowerShell or CMD and works with your own Telegram account.

## Run it

Open PowerShell and run:

```powershell
irm https://raw.githubusercontent.com/Damn-Man123/TeleConsole/main/install.ps1 | iex
```

The script downloads the latest release, verifies its SHA-256 checksum, saves it to `%LOCALAPPDATA%\TeleConsole`, and starts it. Running the same command later updates to the newest version.

Prefer to read the script first? Download it, review it, then run it:

```powershell
irm https://raw.githubusercontent.com/Damn-Man123/TeleConsole/main/install.ps1 -OutFile install.ps1
notepad install.ps1
.\install.ps1
```

You can also download `TeleConsole.exe` and its `.sha256` file directly from the [Releases](../../releases) page.

## First-time setup

You need your own **API ID** and **API Hash** from <https://my.telegram.org> (API development tools). The tool asks for them on first launch. Do not share them.

## Your data

- Config and login session files are stored in `%LOCALAPPDATA%\TeleConsole`.
- A `.session` file gives full access to your Telegram account. Never share it or upload it anywhere.
- Choose "Logout + Delete session + Config" inside the tool to remove your login data.

To uninstall completely, delete the folder:

```powershell
Remove-Item "$env:LOCALAPPDATA\TeleConsole" -Recurse -Force
```

## Responsible use

This tool is intended for managing accounts, groups, and channels that you own or administer. Automating Telegram with a personal account can break Telegram's Terms of Service, and bulk messaging, mass inviting, or scraping members can lead to limits or a permanent ban of your account. Collecting or contacting people without their consent may also violate privacy and anti-spam laws where you live. You are responsible for how you use it. This project is not affiliated with or endorsed by Telegram.

## Building it yourself

```powershell
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --console --name TeleConsole consoleT.py
```

Releases are built automatically by GitHub Actions when a tag such as `v1.0.0` is pushed.

## About

This tool was created by Soksambatt Sar (Jasmine). All rights reserved. Modification, redistribution, and licensing are controlled by the author.
