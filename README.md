# CliperBot

**Automatic video uploader for Telegram**  
Monitors a folder for new video files (≥ 5 MB) and sends them straight to your Telegram chat — no manual uploads.

---

## How to use

1. **Download and extract** `cliper.exe`.
2. Place it anywhere (Desktop, Documents, Startup folder…).
3. Run it.

On first run:

- You’ll be prompted to **select a folder** to monitor.
- Then you’ll be asked to **send any message** to the Telegram bot so it can detect your chat ID.
- Once linked, CliperBot will silently watch for new `.mp4` / `.mkv` / `.avi` / `.mov` files **of at least 5 MB** and upload them automatically.

> CliperBot will continue running in the background and **start automatically with Windows**.

---

## Command-line options

- **`--no-menu`**  
  Start minimized in the system tray (no console or window).

- **`--debug`**  
  Launch the **Debug UI**:  
  - A console shows every step (folder startup, file detection, upload attempts and results).  
  - A “Select & Send” button lets you test uploads manually without dropping files into the folder.

---

## Debug UI

1. Run:  
   ```bash
   cliper.exe --debug
