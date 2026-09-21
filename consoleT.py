import os
import json
import asyncio
import nest_asyncio
from datetime import datetime
from telethon import TelegramClient, errors, functions, types
from telethon.tl.types import UserStatusOnline, UserStatusOffline, UserStatusRecently, UserStatusLastWeek, UserStatusLastMonth
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box
import questionary
from questionary import Style

nest_asyncio.apply()

console = Console()

custom_style = Style([
    ("qmark", "fg:#673ab7 bold"), 
    ("question", "bold"),
    ("answer", "fg:#f44336 bold"),
    ("pointer", "fg:#ffff00 bold"), #Yellow collor arrow
    ("highlighted", "fg:#673ab7 bold"),#Text color selection
    ("selected", "fg:#cc5454"),
    ("separator", "fg:#cc5454"),
    ("instruction", ""),
    ("text", ""),
    ("disabled", "fg:#858585 italic")
])

#CONFIG_FILE = "telegram_config.json" uncheck if use individually
#*******************************************************************
DATA_DIR = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "TeleConsole")
os.makedirs(DATA_DIR, exist_ok=True) 
CONFIG_FILE = os.path.join(DATA_DIR, "telegram_config.json")
#**********************READY FOR DEPLOYMENT**********************************************
class TeleConsole:
    def __init__(self):
        self.client = None
        self.api_id = None
        self.api_hash = None
        self.phone = None
        self.is_running = False
        self.full_users_data = []
        self.full_groups_data = []

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.api_id = data.get("api_id")
                    self.api_hash = data.get("api_hash")
                    self.phone = data.get("phone")
            except:
                pass

    def save_config(self):
        if all([self.api_id, self.api_hash, self.phone]):
            with open(CONFIG_FILE, "w") as f:
                json.dump({
                    "api_id": self.api_id,
                    "api_hash": self.api_hash,
                    "phone": self.phone
                }, f, indent=2)

    def clear(self):
        os.system("cls" if os.name == "nt" else "clear")

    def banner(self):
        self.clear()
        console.print(Panel.fit(
            "[bold cyan]TELE API CONFIGURATION[/bold cyan]\n[dim]Console Edition v1.2 • By Sbxtt[/dim]",
            border_style="cyan",
            padding=(1, 4)
        ))

    def log(self, message, style="white"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        console.print(f"[dim]{timestamp}[/dim] {message}", style=style)

    async def safe_get_entity(self, peer):
        try:
            return await self.client.get_input_entity(peer)
        except Exception:
            try:
                # Fallback to full entity
                return await self.client.get_entity(peer)
            except Exception as e:
                self.log(f"Entity error for {peer}: {e}", "red")
                return None

    def select_menu(self, title, choices):
        return questionary.select(
            title,
            choices=choices,
            style=custom_style,
            qmark="➤",
            pointer="➤"
        ).ask()

    # ==================== LOGIN ====================
    async def login(self):
        self.banner()
        console.print(Panel("[bold]Login Required[/bold]", border_style="yellow"))

        self.load_config()

        if self.api_id and self.api_hash and self.phone:
            console.print(f"[green]Saved credentials found for {self.phone}[/green]")
            use_saved = questionary.confirm("Use saved credentials?", default=True, style=custom_style).ask()
            if not use_saved:
                self.api_id = self.api_hash = self.phone = None

        if not self.api_id:
            self.api_id = questionary.text("API ID:", style=custom_style).ask().strip()
            self.api_hash = questionary.text("API Hash:", style=custom_style).ask().strip()
            self.phone = questionary.text("Phone number (with +):", style=custom_style).ask().strip()

            if questionary.confirm("Save credentials?", default=True, style=custom_style).ask():
                self.save_config()

        session_name = f"session_{self.phone}"
        self.client = TelegramClient(session_name, int(self.api_id), self.api_hash)

        await self.client.connect()

        if await self.client.is_user_authorized():
            me = await self.client.get_me()
            name = me.username or me.first_name or "User"
            console.print(f"\n[bold green]✓ Already logged in as {name}[/bold green]")
            await asyncio.sleep(1)
            return True

        console.print("\n[yellow]Sending verification code...[/yellow]")

        try:
            await self.client.send_code_request(self.phone)
        except Exception as e:
            console.print(f"[yellow]Telegram returned a warning: {e}[/yellow]")
            console.print("[yellow]The code was still sent. Please enter it below.[/yellow]")

        code = questionary.text("Enter the code you received:", style=custom_style).ask()

        try:
            await self.client.sign_in(self.phone, code)
        except errors.SessionPasswordNeededError:
            password = questionary.password("2FA Password:", style=custom_style).ask()
            await self.client.sign_in(password=password)
        except Exception as e:
            console.print(f"[red]Login failed: {e}[/red]")
            return False

        me = await self.client.get_me()
        name = me.username or me.first_name or "User"
        console.print(f"\n[bold green]✓ Successfully logged in as {name}[/bold green]")
        await asyncio.sleep(1.2)
        return True

    # ==================== MAIN MENU ====================
    async def main_menu(self):
        while True:
            self.banner()
            me = await self.client.get_me()
            name = me.username or me.first_name or "User"
            console.print(f"[bold]Logged in as:[/bold] [cyan]{name}[/cyan]\n")

            choice = self.select_menu(
                "Main Menu",
                [
                    "1. Send Message / File",
                    "2. Delete Messages / Files",
                    "3. Groups Manager",
                    "4. Invite Users & Make Admin",
                    "5. ID Finder (Users & Groups)",
                    "6. Settings / Logout",
                    "0. Exit"
                ]
            )

            if choice is None:
                continue

            if choice.startswith("1"):
                await self.send_menu()
            elif choice.startswith("2"):
                await self.delete_menu()
            elif choice.startswith("3"):
                await self.groups_menu()
            elif choice.startswith("4"):
                await self.invite_admin_menu()
            elif choice.startswith("5"):
                await self.id_finder_menu()
            elif choice.startswith("6"):
                result = await self.settings_menu()
                if result is False:
                    return
            elif choice.startswith("0"):
                await self.exit_app()
                break

    # ==================== 1. SEND ====================
    async def send_menu(self):
        while True:
            self.banner()
            choice = self.select_menu(
                "Send Message / File",
                [
                    "1. Send Text Message",
                    "2. Send File(s)",
                    "3. Forward Messages",
                    "0. Back"
                ]
            )

            if choice is None or choice.startswith("0"):
                break
            elif choice.startswith("1"):
                await self.send_text()
            elif choice.startswith("2"):
                await self.send_file()
            elif choice.startswith("3"):
                await self.forward_messages()

    async def send_text(self):
        self.banner()
        console.print(Panel("[bold]Send Text Message[/bold]", border_style="green"))

        targets_raw = questionary.text("Target Chat ID(s) / Username(s) (comma separated):", style=custom_style).ask()
        targets = [t.strip() for t in targets_raw.split(",") if t.strip()]
        targets = [int(t) if t.lstrip("-").isdigit() else t for t in targets]

        message = questionary.text("Message:", style=custom_style).ask()
        repeat = int(questionary.text("Repeat times:", default="1", style=custom_style).ask())
        interval = float(questionary.text("Delay between rounds (seconds):", default="0.5", style=custom_style).ask())

        if not questionary.confirm(f"Send to {len(targets)} target(s), {repeat} time(s)?", style=custom_style).ask():
            return

        self.is_running = True
        total = repeat * len(targets)
        current = 0

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                      BarColumn(), TaskProgressColumn(), console=console) as progress:
            task = progress.add_task("Sending...", total=total)

            for i in range(1, repeat + 1):
                if not self.is_running:
                    break
                for chat_id in targets:
                    if not self.is_running:
                        break
                    try:
                        entity = await self.safe_get_entity(chat_id)
                        if entity:
                            await self.client.send_message(entity, message)
                            self.log(f"Sent to {chat_id}", "green")
                        else:
                            self.log(f"Could not find: {chat_id}", "red")
                    except errors.FloodWaitError as e:
                        self.log(f"FloodWait {e.seconds}s", "yellow")
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        self.log(f"Failed: {e}", "red")

                    current += 1
                    progress.update(task, completed=current)
                    await asyncio.sleep(0.5)

                if i < repeat and self.is_running:
                    await asyncio.sleep(interval)

        self.is_running = False
        console.print("\n[bold green]Finished![/bold green]")
        questionary.press_any_key_to_continue("Press any key to continue...").ask()

    async def send_file(self):
        self.banner()
        console.print(Panel("[bold]Send File(s)[/bold]", border_style="green"))

        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        file_paths = filedialog.askopenfilenames(
            title="Select file(s) you want to send",
            filetypes=[("All Files", "*.*")]
        )
        root.destroy()

        if not file_paths:
            console.print("[yellow]No file selected.[/yellow]")
            questionary.press_any_key_to_continue().ask()
            return

        # Show selected files cleanly
        console.print(f"\n[green]Selected {len(file_paths)} file(s):[/green]")
        for i, path in enumerate(file_paths, 1):
            filename = path.split("/")[-1].split("\\")[-1]
            console.print(f"  {i}. {filename}")

        caption = questionary.text("Caption (optional, applied to all files):", default="", style=custom_style).ask()

        targets_raw = questionary.text("Target Chat ID(s) / Username(s) (comma separated):", style=custom_style).ask()
        targets = [t.strip() for t in targets_raw.split(",") if t.strip()]
        targets = [int(t) if t.lstrip("-").isdigit() else t for t in targets]

        if not targets:
            console.print("[red]No targets provided.[/red]")
            questionary.press_any_key_to_continue().ask()
            return

        repeat = int(questionary.text("Repeat times:", default="1", style=custom_style).ask() or 1)

        # ===== Speed Options =====
        speed_choice = self.select_menu(
            "Sending Speed",
            [
                "1. Safe (slower, more stable)",
                "2. Balanced (recommended)",
                "3. Fast (higher chance of FloodWait)"
            ]
        )

        if speed_choice is None:
            return

        if speed_choice.startswith("1"):
            delay = 0.70
            speed_name = "Safe"
        elif speed_choice.startswith("2"):
            delay = 0.35
            speed_name = "Balanced"
        else:
            delay = 0.15
            speed_name = "Fast"

        total_actions = len(file_paths) * len(targets) * repeat

        confirm_msg = (
            f"Send {len(file_paths)} file(s) → {len(targets)} target(s) × {repeat} time(s)\n"
            f"Speed: {speed_name} ({delay}s delay)\n"
            f"Total actions: {total_actions}"
        )

        if not questionary.confirm(confirm_msg, style=custom_style).ask():
            return

        self.is_running = True
        current = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task(f"Sending files ({speed_name})...", total=total_actions)

            for round_num in range(1, repeat + 1):
                if not self.is_running:
                    break

                for chat_id in targets:
                    if not self.is_running:
                        break

                    for file_path in file_paths:
                        if not self.is_running:
                            break

                        try:
                            entity = await self.safe_get_entity(chat_id)
                            if entity:
                                await self.client.send_file(entity, file_path, caption=caption)
                                filename = file_path.split("/")[-1].split("\\")[-1]
                                self.log(f"[FILE] Sent → {chat_id} | {filename}", "green")
                            else:
                                self.log(f"[FILE] Could not find: {chat_id}", "red")
                        except errors.FloodWaitError as e:
                            self.log(f"FloodWait {e.seconds}s — waiting...", "yellow")
                            await asyncio.sleep(e.seconds)
                        except Exception as e:
                            self.log(f"[FILE] Failed: {e}", "red")

                        current += 1
                        progress.update(task, completed=current)
                        await asyncio.sleep(delay)

                if round_num < repeat and self.is_running:
                    await asyncio.sleep(delay)

        self.is_running = False
        console.print("\n[bold green]File sending finished![/bold green]")
        questionary.press_any_key_to_continue().ask()

    #Forward message function
    async def forward_messages(self):
        self.banner()
        console.print(Panel("[bold]Forward Messages[/bold]", border_style="green"))

        # ===== 1. Source Chat =====
        source_raw = questionary.text("Source Chat ID / Username:", style=custom_style).ask()
        if not source_raw:
            return
        source = int(source_raw) if source_raw.lstrip("-").isdigit() else source_raw.strip()

        source_entity = await self.safe_get_entity(source)
        if not source_entity:
            console.print("[red]Source chat not found.[/red]")
            questionary.press_any_key_to_continue().ask()
            return

        # ===== 2. Filter Type =====
        filter_choice = self.select_menu(
            "What type of messages to load?",
            [
                "1. All messages",
                "2. Only Media (Photo + Video)",
                "3. Only Files / Documents",
                "4. Only Text"
            ]
        )
        if filter_choice is None:
            return

        # ===== 3. How many messages =====
        limit = int(questionary.text("How many recent messages to load?", default="30", style=custom_style).ask() or 30)

        console.print("\n[yellow]Loading messages...[/yellow]")

        messages = []
        try:
            async for msg in self.client.iter_messages(source_entity, limit=limit * 3):  # load extra to filter
                if filter_choice.startswith("1"):  # All
                    messages.append(msg)
                elif filter_choice.startswith("2"):  # Media
                    if msg.photo or msg.video:
                        messages.append(msg)
                elif filter_choice.startswith("3"):  # Files
                    if msg.document and not (msg.photo or msg.video):
                        messages.append(msg)
                elif filter_choice.startswith("4"):  # Text
                    if msg.text and not msg.media:
                        messages.append(msg)

                if len(messages) >= limit:
                    break
        except Exception as e:
            console.print(f"[red]Failed to load messages: {e}[/red]")
            questionary.press_any_key_to_continue().ask()
            return

        if not messages:
            console.print("[yellow]No messages found with this filter.[/yellow]")
            questionary.press_any_key_to_continue().ask()
            return

        # Reverse so newest is at the bottom (more natural)
        messages = list(reversed(messages))

        # ===== 4. Show messages =====
        table = Table(title=f"Messages from source ({len(messages)} found)", box=box.ROUNDED)
        table.add_column("No", style="dim", width=5)
        table.add_column("Type", style="cyan", width=12)
        table.add_column("Preview / Info")

        for i, msg in enumerate(messages, 1):
            if msg.photo:
                msg_type = "Photo"
                preview = "🖼 Photo"
            elif msg.video:
                msg_type = "Video"
                preview = "🎬 Video"
            elif msg.document:
                msg_type = "File"
                name = getattr(msg.file, "name", None) or "Document"
                preview = f"📄 {name}"
            elif msg.text:
                msg_type = "Text"
                preview = (msg.text[:60] + "...") if len(msg.text) > 60 else msg.text
            else:
                msg_type = "Other"
                preview = "—"

            table.add_row(str(i), msg_type, preview)

        console.print(table)
        console.print()

        # ===== 5. Select messages =====
        selection = questionary.text(
            "Select messages to forward (e.g. 1,3,5-8 or 'all'):",
            style=custom_style
        ).ask()

        if not selection:
            return

        selected_msgs = []
        if selection.lower().strip() == "all":
            selected_msgs = messages
        else:
            try:
                parts = selection.replace(" ", "").split(",")
                indexes = set()
                for part in parts:
                    if "-" in part:
                        start, end = map(int, part.split("-"))
                        indexes.update(range(start, end + 1))
                    else:
                        indexes.add(int(part))
                for idx in sorted(indexes):
                    if 1 <= idx <= len(messages):
                        selected_msgs.append(messages[idx - 1])
            except:
                console.print("[red]Invalid selection format.[/red]")
                questionary.press_any_key_to_continue().ask()
                return

        if not selected_msgs:
            console.print("[yellow]No messages selected.[/yellow]")
            questionary.press_any_key_to_continue().ask()
            return

        console.print(f"\n[green]Selected {len(selected_msgs)} message(s)[/green]")

        # ===== 6. Normal or Anonymous =====
        mode_choice = self.select_menu(
            "Forward Mode",
            [
                "1. Normal Forward (keep original sender)",
                "2. Anonymous (appear as sent by you)"
            ]
        )
        if mode_choice is None:
            return

        drop_author = mode_choice.startswith("2")

        # ===== 7. Targets =====
        targets_raw = questionary.text("Target Chat ID(s) / Username(s) (comma separated):", style=custom_style).ask()
        targets = [t.strip() for t in targets_raw.split(",") if t.strip()]
        targets = [int(t) if t.lstrip("-").isdigit() else t for t in targets]

        if not targets:
            console.print("[red]No targets provided.[/red]")
            questionary.press_any_key_to_continue().ask()
            return

        # ===== 8. Speed =====
        speed_choice = self.select_menu(
            "Sending Speed",
            [
                "1. Safe (slower, more stable)",
                "2. Balanced (recommended)",
                "3. Fast (higher chance of FloodWait)"
            ]
        )
        if speed_choice is None:
            return

        if speed_choice.startswith("1"):
            delay = 0.70
            speed_name = "Safe"
        elif speed_choice.startswith("2"):
            delay = 0.35
            speed_name = "Balanced"
        else:
            delay = 0.15
            speed_name = "Fast"

        # ===== 9. Repeat times =====
        repeat = int(questionary.text("Repeat times:", default="1", style=custom_style).ask() or 1)

        total_actions = len(selected_msgs) * len(targets) * repeat

        mode_text = "Anonymous" if drop_author else "Normal"
        confirm_msg = (
            f"Forward {len(selected_msgs)} message(s) → {len(targets)} target(s) × {repeat} time(s)\n"
            f"Mode: {mode_text} | Speed: {speed_name}\n"
            f"Total actions: {total_actions}"
        )

        if not questionary.confirm(confirm_msg, style=custom_style).ask():
            return

        # ===== 10. Start Forwarding =====
        self.is_running = True
        current = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task(f"Forwarding ({mode_text})...", total=total_actions)

            for round_num in range(1, repeat + 1):
                if not self.is_running:
                    break

                for target in targets:
                    if not self.is_running:
                        break

                    target_entity = await self.safe_get_entity(target)
                    if not target_entity:
                        self.log(f"Target not found: {target}", "red")
                        current += len(selected_msgs)
                        progress.update(task, completed=current)
                        continue

                    for msg in selected_msgs:
                        if not self.is_running:
                            break

                        try:
                            await self.client.forward_messages(
                                entity=target_entity,
                                messages=msg,
                                from_peer=source_entity,
                                drop_author=drop_author
                            )
                            self.log(f"[Round {round_num}] Forwarded → {target}", "green")
                        except errors.FloodWaitError as e:
                            self.log(f"FloodWait {e.seconds}s", "yellow")
                            await asyncio.sleep(e.seconds)
                        except Exception as e:
                            self.log(f"Failed → {target}: {e}", "red")

                        current += 1
                        progress.update(task, completed=current)
                        await asyncio.sleep(delay)

                # Small pause between rounds
                if round_num < repeat and self.is_running:
                    await asyncio.sleep(delay)

        self.is_running = False
        console.print("\n[bold green]Forwarding finished![/bold green]")
        questionary.press_any_key_to_continue().ask()

    # ==================== 2. DELETE ====================
    async def delete_menu(self):
        while True:
            self.banner()
            choice = self.select_menu(
                "Delete Messages / Files",
                [
                    "1. Delete Recent Messages",
                    "2. Delete Recent Files",
                    "0. Back"
                ]
            )

            if choice is None or choice.startswith("0"):
                break
            elif choice.startswith("1"):
                await self.delete_recent_messages()
            elif choice.startswith("2"):
                await self.delete_recent_files()

    async def delete_recent_messages(self):
        self.banner()
        console.print(Panel("[bold]Delete Recent Messages[/bold]", border_style="red"))

        limit = int(questionary.text("How many recent messages to delete per chat?", default="50", style=custom_style).ask())
        targets_raw = questionary.text("Target Chat ID(s) / Username(s) (comma separated):", style=custom_style).ask()
        targets = [t.strip() for t in targets_raw.split(",") if t.strip()]
        targets = [int(t) if t.lstrip("-").isdigit() else t for t in targets]

        if not questionary.confirm(f"Delete last {limit} messages from {len(targets)} chat(s)?", style=custom_style).ask():
            return

        for chat_id in targets:
            try:
                entity = await self.safe_get_entity(chat_id)
                if not entity:
                    continue
                messages = []
                async for msg in self.client.iter_messages(entity, limit=limit):
                    messages.append(msg.id)
                if messages:
                    await self.client.delete_messages(entity, messages)
                    self.log(f"Deleted {len(messages)} messages from {chat_id}", "green")
                else:
                    self.log(f"No messages found in {chat_id}", "yellow")
            except Exception as e:
                self.log(f"Error on {chat_id}: {e}", "red")

        console.print("\n[bold green]Done![/bold green]")
        questionary.press_any_key_to_continue().ask()

    async def delete_recent_files(self):
        self.banner()
        console.print(Panel("[bold]Delete Recent Files[/bold]", border_style="red"))

        limit = int(questionary.text("How many recent files to delete per chat?", default="30", style=custom_style).ask())
        targets_raw = questionary.text("Target Chat ID(s) / Username(s) (comma separated):", style=custom_style).ask()
        targets = [t.strip() for t in targets_raw.split(",") if t.strip()]
        targets = [int(t) if t.lstrip("-").isdigit() else t for t in targets]

        if not questionary.confirm(f"Delete last {limit} files from {len(targets)} chat(s)?", style=custom_style).ask():
            return

        for chat_id in targets:
            try:
                entity = await self.safe_get_entity(chat_id)
                if not entity:
                    continue
                file_ids = []
                async for msg in self.client.iter_messages(entity, limit=limit * 3):
                    if msg.media:
                        file_ids.append(msg.id)
                        if len(file_ids) >= limit:
                            break
                if file_ids:
                    await self.client.delete_messages(entity, file_ids)
                    self.log(f"Deleted {len(file_ids)} files from {chat_id}", "green")
                else:
                    self.log(f"No files found in {chat_id}", "yellow")
            except Exception as e:
                self.log(f"Error on {chat_id}: {e}", "red")

        console.print("\n[bold green]Done![/bold green]")
        questionary.press_any_key_to_continue().ask()

    # ==================== 3. GROUPS ====================
    async def groups_menu(self):
        while True:
            self.banner()
            choice = self.select_menu(
                "Groups Manager",
                [
                    "1. Create Groups (bulk)",
                    "2. Leave Groups",
                    "3. Scrape Members",
                    "0. Back"
                ]
            )

            if choice is None or choice.startswith("0"):
                break
            elif choice.startswith("1"):
                await self.create_groups_bulk()
            elif choice.startswith("2"):
                await self.leave_groups_bulk()
            elif choice.startswith("3"):
                await self.scrape_members()

    async def create_groups_bulk(self):
        self.banner()
        console.print(Panel("[bold]Bulk Create Groups[/bold]", border_style="blue"))

        names_raw = questionary.text("Group names (comma separated):", style=custom_style).ask()
        names = [n.strip() for n in names_raw.split(",") if n.strip()]

        if not names:
            console.print("[red]No names provided[/red]")
            questionary.press_any_key_to_continue().ask()
            return

        # Ask type of group
        group_type = self.select_menu(
            "Group Type",
            [
                "1. Supergroup (recommended, unlimited members)",
                "2. Basic Group (max 200 members)"
            ]
        )
        if group_type is None:
            return

        is_megagroup = group_type.startswith("1")

        about = questionary.text("Description / About (optional):", default="", style=custom_style).ask() or ""

        if not questionary.confirm(f"Create {len(names)} {'supergroup(s)' if is_megagroup else 'basic group(s)'}?", style=custom_style).ask():
            return

        created_ids = []

        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
            task = progress.add_task("Creating...", total=len(names))
            for name in names:
                try:
                    if is_megagroup:
                        result = await self.client(functions.channels.CreateChannelRequest(
                            title=name,
                            about=about,
                            megagroup=True
                        ))
                        created = result.chats[0] if result.chats else None
                        chat_id = created.id if created else None
                        if chat_id:
                            # Telegram channel IDs are usually shown with -100 prefix
                            full_id = int(f"-100{chat_id}") if not str(chat_id).startswith("-") else chat_id
                            created_ids.append(str(full_id))
                            self.log(f"Created supergroup: {name} (ID: {full_id})", "green")
                        else:
                            self.log(f"Created supergroup: {name} (ID unknown)", "yellow")
                    else:
                        result = await self.client(functions.messages.CreateChatRequest(
                            users=[],
                            title=name
                        ))

                        chat_id = None

                        # Try get ID from result
                        if hasattr(result, "chats") and result.chats:
                            chat_id = result.chats[0].id
                        elif hasattr(result, "chat") and result.chat:
                            chat_id = result.chat.id

                        # Fallback: search recent dialogs by title
                        if not chat_id:
                            await asyncio.sleep(1.2)
                            async for dialog in self.client.iter_dialogs(limit=10):
                                if dialog.name == name and dialog.is_group:
                                    chat_id = dialog.id
                                    break

                        if chat_id:
                            created_ids.append(str(chat_id))
                            self.log(f"Created basic group: {name} (ID: {chat_id})", "green")
                        else:
                            self.log(f"Created basic group: {name} (ID not found)", "yellow")
                except Exception as e:
                    self.log(f"Failed to create {name}: {e}", "red")
                progress.advance(task)
                await asyncio.sleep(1.8)

        console.print("\n[bold green]Finished creating groups![/bold green]")

        if created_ids:
            ids_str = ", ".join(created_ids)
            console.print(f"\n[bold cyan]Created Group IDs:[/bold cyan]")
            console.print(f"[white]{ids_str}[/white]")
            console.print("\n[dim]↑ You can copy the IDs above[/dim]")

        questionary.press_any_key_to_continue().ask()

    async def leave_groups_bulk(self):
        self.banner()
        console.print(Panel("[bold]Leave Groups[/bold]", border_style="blue"))

        ids_raw = questionary.text("Group IDs (comma separated):", style=custom_style).ask()
        group_ids = [t.strip() for t in ids_raw.split(",") if t.strip()]
        group_ids = [int(t) if t.lstrip("-").isdigit() else t for t in group_ids]

        if not group_ids:
            console.print("[red]No group IDs provided.[/red]")
            questionary.press_any_key_to_continue().ask()
            return

        if not questionary.confirm(f"Leave {len(group_ids)} group(s)?", style=custom_style).ask():
            return

        for gid in group_ids:
            try:
                entity = await self.client.get_entity(gid)

                if isinstance(entity, types.Channel):
                    # For channels / supergroups
                    await self.client(functions.channels.LeaveChannelRequest(channel=entity))
                    self.log(f"Left channel/supergroup: {gid}", "green")
                else:
                    # For basic groups
                    await self.client.delete_dialog(entity)
                    self.log(f"Left basic group: {gid}", "green")

            except errors.FloodWaitError as e:
                self.log(f"FloodWait {e.seconds}s on {gid}", "yellow")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                self.log(f"Error leaving {gid}: {e}", "red")

            await asyncio.sleep(1.2)

        console.print("\n[bold green]Done![/bold green]")
        questionary.press_any_key_to_continue().ask()

    # ==================== NEW: SCRAPE MEMBERS ====================
    async def scrape_members(self):
        self.banner()
        console.print(Panel("[bold]Scrape Members[/bold]", border_style="cyan"))
        console.print("[yellow]Loading your groups and channels...[/yellow]")

        groups = []
        async for dialog in self.client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                entity = dialog.entity
                title = dialog.name or "Unknown"
                chat_id = dialog.id

                if dialog.is_channel:
                    chat_type = "Supergroup" if getattr(entity, "megagroup", False) else "Channel"
                else:
                    chat_type = "Basic Group"

                display = f"[{chat_type}] {title}  (ID: {chat_id})"
                groups.append({
                    "display": display,
                    "id": chat_id,
                    "title": title,
                    "type": chat_type
                })

        if not groups:
            console.print("[red]No groups or channels found.[/red]")
            questionary.press_any_key_to_continue().ask()
            return

        choices = [g["display"] for g in groups]
        selected = self.select_menu("Select a Group / Channel to scrape:", choices)
        if not selected:
            return

        selected_group = next((g for g in groups if g["display"] == selected), None)
        if not selected_group:
            console.print("[red]Selection error.[/red]")
            return

        console.print(f"\n[green]Selected:[/green] {selected_group['title']} ({selected_group['type']})")

        # Ask scraping mode
        scrape_mode = self.select_menu(
            "Scraping Mode",
            [
                "1. Normal (safer, recommended)",
                "2. Aggressive (faster but higher FloodWait / ban risk)"
            ]
        )
        if scrape_mode is None:
            return

        use_aggressive = scrape_mode.startswith("2")

        console.print("[yellow]Scraping members... This can take time on large groups.[/yellow]\n")

        members = []
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[cyan]{task.completed} members"),
                console=console,
                transient=False
            ) as progress:
                task = progress.add_task("Scraping...", total=None)

                async for user in self.client.iter_participants(
                    selected_group["id"],
                    aggressive=use_aggressive
                ):
                    name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
                    name = name.strip() or "Deleted Account"
                    username = f"@{user.username}" if user.username else "-"
                    user_id = str(user.id)
                    is_bot = "Bot" if user.bot else "User"

                    status = user.status
                    if isinstance(status, UserStatusOnline):
                        last_active = "Online"
                    elif isinstance(status, UserStatusOffline):
                        last_active = status.was_online.astimezone().strftime("%d/%m/%Y %H:%M")
                    elif isinstance(status, UserStatusRecently):
                        last_active = "Recently"
                    elif isinstance(status, UserStatusLastWeek):
                        last_active = "Last Week"
                    elif isinstance(status, UserStatusLastMonth):
                        last_active = "Last Month"
                    else:
                        last_active = "Unknown"

                    members.append({
                        "name": name,
                        "id": user_id,
                        "username": username,
                        "status": last_active,
                        "type": is_bot
                    })
                    progress.update(task, completed=len(members), description=f"Scraping... ({len(members)})")

        except errors.FloodWaitError as e:
            console.print(f"\n[yellow]FloodWait: waiting {e.seconds}s...[/yellow]")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            console.print(f"\n[red]Failed to scrape: {e}[/red]")
            questionary.press_any_key_to_continue().ask()
            return

        total = len(members)
        if total == 0:
            console.print("[yellow]No members found.[/yellow]")
            questionary.press_any_key_to_continue().ask()
            return

        console.print(f"\n[bold green]✓ Scraped {total} members[/bold green]\n")

        # ========== SHOW MEMBERS ==========
        if total <= 100:
            table = Table(title=f"Members of {selected_group['title']}  |  Total: {total}", box=box.ROUNDED)
            table.add_column("No", style="dim", width=5)
            table.add_column("Name", style="cyan")
            table.add_column("User ID", style="green")
            table.add_column("Username")
            table.add_column("Status")
            table.add_column("Type")

            for i, m in enumerate(members, 1):
                table.add_row(str(i), m["name"], m["id"], m["username"], m["status"], m["type"])

            console.print(table)
            console.print()

            save_choice = self.select_menu(
                "What do you want to do?",
                [
                    "1. Save as .txt",
                    "2. Save as .csv",
                    "3. Copy all User IDs (comma separated)",
                    "4. Skip"
                ]
            )

            if save_choice is None or save_choice.startswith("4"):
                console.print("[yellow]Skipped.[/yellow]")
            elif save_choice.startswith("3"):
                ids = ",".join([m["id"] for m in members])
                console.print("\n[bold cyan]All User IDs (comma separated):[/bold cyan]\n")
                console.print(ids)
                console.print("\n[green]↑ You can now select and copy the IDs above[/green]")
            else:
                await self._save_members(members, selected_group, save_choice)

            questionary.press_any_key_to_continue().ask()
            return

        # ========== PAGINATION (more than 100 members) ==========
        page_size = 50
        total_pages = (total + page_size - 1) // page_size
        current_page = 0

        while True:
            self.banner()
            start = current_page * page_size
            end = min(start + page_size, total)
            page_members = members[start:end]

            table = Table(
                title=f"{selected_group['title']}  |  Page {current_page + 1}/{total_pages}  |  Total: {total}",
                box=box.ROUNDED
            )
            table.add_column("No", style="dim", width=6)
            table.add_column("Name", style="cyan")
            table.add_column("User ID", style="green")
            table.add_column("Username")
            table.add_column("Status")
            table.add_column("Type")

            for i, m in enumerate(page_members, start + 1):
                table.add_row(str(i), m["name"], m["id"], m["username"], m["status"], m["type"])

            console.print(table)
            console.print()

            nav_choices = []
            if current_page > 0:
                nav_choices.append("← Previous page")
            if current_page < total_pages - 1:
                nav_choices.append("→ Next page")
            nav_choices += [
                "Jump to page",
                "Save all members",
                "Copy all User IDs",
                "Back"
            ]

            choice = self.select_menu("Navigation", nav_choices)

            if choice is None or choice == "Back":
                break
            elif choice == "→ Next page":
                current_page += 1
            elif choice == "← Previous page":
                current_page -= 1
            elif choice == "Jump to page":
                page_input = questionary.text(
                    f"Enter page number (1-{total_pages}):",
                    style=custom_style
                ).ask()
                try:
                    page_num = int(page_input)
                    if 1 <= page_num <= total_pages:
                        current_page = page_num - 1
                    else:
                        console.print("[red]Invalid page number[/red]")
                        await asyncio.sleep(1)
                except:
                    console.print("[red]Invalid input[/red]")
                    await asyncio.sleep(1)
            elif choice == "Save all members":
                save_choice = self.select_menu(
                    f"Save all {total} members?",
                    [
                        "1. Save as .txt",
                        "2. Save as .csv",
                        "3. Cancel"
                    ]
                )
                if save_choice and not save_choice.startswith("3"):
                    await self._save_members(members, selected_group, save_choice)
                    questionary.press_any_key_to_continue().ask()
            elif choice == "Copy all User IDs":
                ids = ",".join([m["id"] for m in members])
                console.print("\n[bold cyan]All User IDs (comma separated):[/bold cyan]\n")
                console.print(ids)
                console.print("\n[green]↑ You can now select and copy the IDs above[/green]")
                questionary.press_any_key_to_continue().ask()


    async def _save_members(self, members, selected_group, save_choice):
        """Helper to save members list"""
        total = len(members)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in selected_group["title"] if c.isalnum() or c in (" ", "-", "_")).strip()
        safe_title = safe_title.replace(" ", "_")[:40]

        try:
            if save_choice.startswith("1"):
                filename = f"members_{safe_title}_{timestamp}.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"Group   : {selected_group['title']}\n")
                    f.write(f"Type    : {selected_group['type']}\n")
                    f.write(f"Total   : {total}\n")
                    f.write(f"Scraped : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n\n")
                    for m in members:
                        f.write(f"{m['name']} | {m['id']} | {m['username']} | {m['status']} | {m['type']}\n")
                console.print(f"\n[bold green]✓ Saved {total} members → {filename}[/bold green]")

            elif save_choice.startswith("2"):
                filename = f"members_{safe_title}_{timestamp}.csv"
                with open(filename, "w", encoding="utf-8-sig", newline="") as f:
                    f.write("Name,User ID,Username,Status,Type\n")
                    for m in members:
                        name = m['name'].replace('"', '""')
                        f.write(f'"{name}",{m["id"]},{m["username"]},{m["status"]},{m["type"]}\n')
                console.print(f"\n[bold green]✓ Saved {total} members → {filename}[/bold green]")

        except Exception as e:
            console.print(f"[red]Failed to save: {e}[/red]")


    # ==================== 4. INVITE & ADMIN ====================
    async def invite_admin_menu(self):
        while True:
            self.banner()
            choice = self.select_menu(
                "Invite Users & Make Admin",
                [
                    "1. Invite Users to Groups",
                    "2. Make User Admin",
                    "0. Back"
                ]
            )

            if choice is None or choice.startswith("0"):
                break
            elif choice.startswith("1"):
                await self.invite_users_bulk()
            elif choice.startswith("2"):
                await self.make_admin_bulk()

    async def invite_users_bulk(self):
        self.banner()
        console.print(Panel("[bold]Invite Users to Groups[/bold]", border_style="magenta"))

        users_raw = questionary.text("Users (@username or ID, comma separated):", style=custom_style).ask()
        users = [u.strip() for u in users_raw.split(",") if u.strip()]

        groups_raw = questionary.text("Group IDs (comma separated):", style=custom_style).ask()
        groups = [g.strip() for g in groups_raw.split(",") if g.strip()]
        groups = [int(g) if g.lstrip("-").isdigit() else g for g in groups]

        if not users or not groups:
            console.print("[red]Users or Groups cannot be empty.[/red]")
            questionary.press_any_key_to_continue().ask()
            return

        if not questionary.confirm(f"Invite {len(users)} user(s) to {len(groups)} group(s)?", style=custom_style).ask():
            return

        total = len(users) * len(groups)
        current = 0
        success = 0
        failed = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Inviting...", total=total)

            for group_id in groups:
                try:
                    group_entity = await self.client.get_entity(group_id)
                except Exception as e:
                    self.log(f"Cannot get group {group_id}: {e}", "red")
                    current += len(users)
                    progress.update(task, completed=current)
                    failed += len(users)
                    continue

                for user in users:
                    try:
                        user_entity = await self.client.get_input_entity(user)

                        if isinstance(group_entity, types.Channel):
                            await self.client(functions.channels.InviteToChannelRequest(
                                channel=group_entity,
                                users=[user_entity]
                            ))
                        else:
                            await self.client(functions.messages.AddChatUserRequest(
                                chat_id=group_entity.id,
                                user_id=user_entity,
                                fwd_limit=50
                            ))

                        self.log(f"Invited {user} → {group_id}", "green")
                        success += 1

                    except errors.FloodWaitError as e:
                        self.log(f"FloodWait {e.seconds}s — waiting...", "yellow")
                        await asyncio.sleep(e.seconds)
                    except errors.UserPrivacyRestrictedError:
                        self.log(f"Privacy restricted: {user}", "yellow")
                        failed += 1
                    except errors.UserNotMutualContactError:
                        self.log(f"Not mutual contact: {user}", "yellow")
                        failed += 1
                    except errors.UserAlreadyParticipantError:
                        self.log(f"Already in group: {user}", "cyan")
                        success += 1
                    except errors.ChatAdminRequiredError:
                        self.log(f"No admin rights in {group_id}", "red")
                        failed += 1
                    except Exception as e:
                        self.log(f"Failed {user} → {group_id}: {e}", "red")
                        failed += 1

                    current += 1
                    progress.update(task, completed=current)
                    await asyncio.sleep(1.2)

        console.print(f"\n[bold green]Invite finished![/bold green]")
        console.print(f"Success: {success} | Failed: {failed}")
        questionary.press_any_key_to_continue().ask()

    async def make_admin_bulk(self):
        self.banner()
        console.print(Panel("[bold]Make User Admin[/bold]", border_style="magenta"))

        user = questionary.text("User (@username or ID):", style=custom_style).ask()
        if not user:
            return

        groups_raw = questionary.text("Group IDs (comma separated):", style=custom_style).ask()
        groups = [g.strip() for g in groups_raw.split(",") if g.strip()]
        groups = [int(g) if g.lstrip("-").isdigit() else g for g in groups]

        if not groups:
            console.print("[red]No groups provided.[/red]")
            questionary.press_any_key_to_continue().ask()
            return

        admin_title = questionary.text("Admin title (optional):", default="Admin", style=custom_style).ask() or "Admin"

        if not questionary.confirm(f"Make {user} admin in {len(groups)} group(s)?", style=custom_style).ask():
            return

        user_entity = await self.safe_get_entity(user)
        if not user_entity:
            console.print("[red]User not found[/red]")
            questionary.press_any_key_to_continue().ask()
            return

        for gid in groups:
            try:
                group_entity = await self.client.get_entity(gid)
                await self.client.edit_admin(
                    group_entity,
                    user_entity,
                    is_admin=True,
                    title=admin_title
                )
                self.log(f"Made {user} admin in {gid}", "green")
            except errors.FloodWaitError as e:
                self.log(f"FloodWait {e.seconds}s on {gid}", "yellow")
                await asyncio.sleep(e.seconds)
            except errors.ChatAdminRequiredError:
                self.log(f"No permission to promote in {gid}", "red")
            except Exception as e:
                self.log(f"Failed on {gid}: {e}", "red")
            await asyncio.sleep(1.2)

        console.print("\n[bold green]Done![/bold green]")
        questionary.press_any_key_to_continue().ask()

    # ==================== 5. ID FINDER ====================
    async def id_finder_menu(self):
        while True:
            self.banner()
            choice = self.select_menu(
                "ID Finder",
                [
                    "1. Load & Search Users",
                    "2. Load & Search Groups",
                    "0. Back"
                ]
            )

            if choice is None or choice.startswith("0"):
                break
            elif choice.startswith("1"):
                await self.load_and_show_users()
            elif choice.startswith("2"):
                await self.load_and_show_groups()

    async def load_and_show_users(self):
        self.banner()
        console.print("[yellow]Loading users... please wait[/yellow]")

        self.full_users_data = []
        count = 0

        async for dialog in self.client.iter_dialogs():
            if dialog.is_user:
                user = dialog.entity
                name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
                name = name.strip() or "Deleted Account"
                username = f"@{user.username}" if user.username else ""
                user_id = str(user.id)
                phone = f"+{user.phone}" if user.phone else ""

                status = user.status
                if isinstance(status, UserStatusOnline):
                    last_active = "Online"
                elif isinstance(status, UserStatusOffline):
                    last_active = status.was_online.astimezone().strftime("%d/%m/%Y %H:%M")
                elif isinstance(status, UserStatusRecently):
                    last_active = "Last seen recently"
                elif isinstance(status, UserStatusLastWeek):
                    last_active = "Last seen within a week"
                elif isinstance(status, UserStatusLastMonth):
                    last_active = "Last seen within a month"
                else:
                    last_active = "Unknown"

                self.full_users_data.append((name, username, user_id, phone, last_active))
                count += 1

        console.print(f"[green]Loaded {count} users[/green]\n")

        while True:
            search = questionary.text("Search (name/username/id) or leave empty | type q to quit:", default="", style=custom_style).ask()
            if search and search.lower() == "q":
                break

            table = Table(title="Users", box=box.ROUNDED)
            table.add_column("Name", style="cyan")
            table.add_column("Username")
            table.add_column("ID", style="green")
            table.add_column("Phone")
            table.add_column("Last Active")

            filtered = 0
            for row in self.full_users_data:
                if not search or search.lower() in " ".join(row).lower():
                    table.add_row(*row)
                    filtered += 1

            console.print(table)
            console.print(f"\nShowing {filtered} / {count} users")
            questionary.press_any_key_to_continue("Press any key to search again...").ask()

    async def load_and_show_groups(self):
        self.banner()
        console.print("[yellow]Loading groups... please wait[/yellow]")

        self.full_groups_data = []
        count = 0

        async for dialog in self.client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                entity = dialog.entity
                title = dialog.name or "Unknown"
                chat_id = str(dialog.id)
                chat_type = "Supergroup" if getattr(entity, "megagroup", False) else ("Channel" if dialog.is_channel else "Basic Group")
                self.full_groups_data.append((title, chat_id, chat_type))
                count += 1

        console.print(f"[green]Loaded {count} groups[/green]\n")

        while True:
            search = questionary.text("Search (title/id) or leave empty | type q to quit:", default="", style=custom_style).ask()
            if search and search.lower() == "q":
                break

            table = Table(title="Groups", box=box.ROUNDED)
            table.add_column("Title", style="cyan")
            table.add_column("ID", style="green")
            table.add_column("Type")

            filtered = 0
            for row in self.full_groups_data:
                if not search or search.lower() in " ".join(row).lower():
                    table.add_row(*row)
                    filtered += 1

            console.print(table)
            console.print(f"\nShowing {filtered} / {count} groups")
            questionary.press_any_key_to_continue().ask()

    # ==================== 6. SETTINGS ====================
    async def settings_menu(self):
        while True:
            self.banner()
            choice = self.select_menu(
                "Settings",
                [
                    "1. Logout + Delete session + Config",
                    "2. Just Disconnect (keep session)",
                    "0. Back"
                ]
            )

            if choice is None or choice.startswith("0"):
                return True
            elif choice.startswith("1"):
                if questionary.confirm("Really logout and delete everything (session + config)?", style=custom_style).ask():
                    await self.client.log_out()

                    for ext in [".session", ".session-journal"]:
                        path = f"session_{self.phone}{ext}"
                        if os.path.exists(path):
                            os.remove(path)

                    if os.path.exists(CONFIG_FILE):
                        os.remove(CONFIG_FILE)

                    console.print("[green]Logged out and all data deleted[/green]")
                    await asyncio.sleep(1)
                    return False
            elif choice.startswith("2"):
                await self.client.disconnect()
                console.print("[green]Disconnected (session kept)[/green]")
                await asyncio.sleep(1)
                return False

    # ==================== EXIT ====================
    async def exit_app(self):
        self.banner()
        choice = self.select_menu(
            "Exit Options",
            [
                "1. Logout + Delete session + Config",
                "2. Just Exit (keep session)"
            ]
        )

        if choice and choice.startswith("1"):
            await self.client.log_out()

            for ext in [".session", ".session-journal"]:
                path = f"session_{self.phone}{ext}"
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

            if os.path.exists(CONFIG_FILE):
                try:
                    os.remove(CONFIG_FILE)
                    console.print("[green]Config file deleted[/green]")
                except:
                    pass

            console.print("[green]Logged out and all data deleted[/green]")
        else:
            await self.client.disconnect()
            console.print("[green]Session kept. Goodbye![/green]")

        await asyncio.sleep(1)

    # ==================== RUN ====================
    async def run(self):
        try:
            if await self.login():
                await self.main_menu()
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
        except Exception as e:
            console.print(f"[bold red]Fatal error:[/bold red] {e}")
        finally:
            if self.client and self.client.is_connected():
                await self.client.disconnect()


if __name__ == "__main__":
    app = TeleConsole()
    asyncio.run(app.run())