# CliperBot
**Your automatic video uploader for Telegram.**  
Monitor a folder for new video clips and send them straight to your Telegram chat — no hassle, no manual uploads.



## How to use 
1. **Download and extract the `.exe`.**

2. Place the `.exe` wherever you want (Desktop, Documents, or even Startup folder).

3. Run it.

On first run:
- You'll be asked to **choose a folder** (the one CliperBot will monitor for new video files).
- Then it will **wait for you to send a message** to the Telegram bot.
- Once you do, the bot will link your chat and begin monitoring the folder.
- All new `.mp4`, `.mkv`, `.avi`, or `.mov` files will be sent automatically to your Telegram.

> From now on, CliperBot runs quietly in the background and **starts automatically with Windows**.

## After install
Start by talking to the bot:

👉 [https://t.me/Cliperrbot](https://t.me/Cliperrbot)

Send **any message** to the bot so it can detect your chat ID during the first-time setup.
## Configuration

Your configuration is stored here:

    %appdata%\CliperBot\config.json

This file contains:
```json
{
  "chat_id": "YOUR_TELEGRAM_CHAT_ID",
  "pasta": "C:/Your/Monitored/Folder"
}
```
## 🔁 Want to reset setup?
Press Win + R, type %appdata%, and hit Enter.

Go to the CliperBot folder.

Delete the file config.json.

Launch the .exe again — and the setup will restart.
## How it Works

### 🗂️ Folder Monitoring

Uses watchdog to detect new files in the selected folder.

Filters by video extensions: .mp4, .mkv, .avi, .mov.

### 📤 Telegram Integration

On first setup, the bot fetches the latest chat that sent a message using getUpdates.

Once the chat ID is known, videos are sent via sendVideo using requests.

### 💾 Persistent Config

Configurations are saved in %appdata%\CliperBot\config.json.

Ensures the bot remembers everything even after reboot.

### 🪟 Tray and GUI

Offers a simple mode selector when launched:

Normal mode (windowed).

Minimized mode.

System tray (background).

Also includes a Tkinter status window if running in normal mode.

### 🛠️ Auto-start on Windows

Adds itself to the Windows Registry key:

    HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run

So it launches with Windows (can be disabled manually).
## One last thing...

If you're thinking of decompiling this app just to steal the Telegram bot token...

### Go fuck yourself.
There are better ways to use your time.
