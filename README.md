
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
   ```
2. Enter the password **2202** when prompted.
3. The window shows:
   - ⏺ **Console**: logs of  
     - `[Monitor] Iniciando monitoramento em: …`  
     - `[Monitor] Arquivo novo detectado: …`  
     - `[Monitor] Enviando vídeo detectado: …`  
     - `[Envio] Sucesso / Falha → filename`  
     - `[Manual] Envio OK / FAIL → filename`  
   - ▶️ **Select & Send**: manually pick a video and upload it.
   - 📂 **Open folder**, **View config**, **Clear console** buttons.

---

## Configuration

Stored in  
```
%APPDATA%\Cliper\config.json
```
```json
{
  "chat_id": "YOUR_TELEGRAM_CHAT_ID",
  "pasta": "C:/Your/Monitored/Folder",
  "versao": "latest"
}
```

CliperBot also keeps its UUID in  
```
%APPDATA%\Cliper\id.json
```

---

## Reset setup

1. Press **Win + R**, type `%appdata%`, Enter.
2. Open the `Cliper` folder.
3. Delete `config.json`.
4. Run `cliper.exe` again to reconfigure.

---

## Features

- **Folder monitoring** via `watchdog`, filtered by `.mp4` / `.mkv` / `.avi` / `.mov`.
- **Minimum size filter**: files under **5 MB** are skipped.
- **Telegram integration**:  
  - First-run grabs your chat ID via `getUpdates`.  
  - Uploads videos with `sendVideo` using `requests`.
- **Debug UI**: interactive console + manual upload.
- **Tray & GUI modes**: windowed, minimized, or tray-only.
- **Auto-start on Windows**: adds itself to  
  `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`.

---

> If you’re thinking about decompiling to swipe the bot token…  
> there are better ways to spend your time. 😉
