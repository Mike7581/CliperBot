import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import threading
import time
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

VERSAO_ATUAL     = "1.7"
CLIPER_DIR       = os.path.join(os.getenv("APPDATA"), "Cliper")
CONFIG_PATH      = os.path.join(CLIPER_DIR, "config.json")
ID_PATH          = os.path.join(CLIPER_DIR, "id.json")
TELEGRAM_TOKEN   = ""
EXTENSOES_VIDEOS = ['.mp4', '.mkv', '.avi', '.mov']

class TelegramClient:
    def __init__(self, token):
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()

    def enviar_video(self, caminho, chat_id):
        nome = os.path.basename(caminho)
        try:
            with open(caminho, 'rb') as f:
                files = {'video': (nome, f)}
                data  = {'chat_id': chat_id, 'caption': f"[DEBUG] Teste de envio: {nome}"}
                res   = self.session.post(self.base_url + "/sendVideo", data=data, files=files)
            return res.status_code == 200
        except:
            return False

class DebugVideoHandler(FileSystemEventHandler):
    def __init__(self, console, client, chat_id):
        self.console = console
        self.client  = client
        self.chat_id = chat_id

    def on_created(self, event):
        if event.is_directory:
            return
        path = event.src_path
        ext  = os.path.splitext(path)[1].lower()
        if ext in EXTENSOES_VIDEOS:
            self.console.insert(tk.END, f"[Monitor] Arquivo novo detectado: {path}\n")
            self.console.see(tk.END)
            time.sleep(2)
            self.console.insert(tk.END, f"[Monitor] Enviando vídeo detectado: {path}\n")
            self.console.see(tk.END)
            ok = self.client.enviar_video(path, self.chat_id)
            self.console.insert(tk.END, f"[Envio] {'Sucesso' if ok else 'Falha'} -> {os.path.basename(path)}\n")
            self.console.see(tk.END)

def main():
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        pasta      = cfg["pasta"]
        chat_id    = cfg["chat_id"]
    except:
        messagebox.showerror("Erro", "Não foi possível ler config.json")
        return
    try:
        with open(ID_PATH, "r") as f:
            cliper_id = json.load(f).get("id", "")
    except:
        cliper_id = ""

    client = TelegramClient(TELEGRAM_TOKEN)

    root = tk.Tk()
    root.title("Debug Log")
    root.geometry("900x450")
    root.configure(bg="#777777")
    try:
        root.iconbitmap(os.path.join(os.path.dirname(__file__), "cliper.ico"))
    except:
        pass
    root.resizable(False, True)

    console_frame = tk.Frame(root, bg="black")
    console_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
    console_text  = tk.Text(console_frame, bg="black", fg="white", font=("Consolas",10))
    console_text.pack(fill=tk.BOTH, expand=True)
    scroll = tk.Scrollbar(console_text)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    console_text.config(yscrollcommand=scroll.set)
    scroll.config(command=console_text.yview)

    painel = tk.Frame(root, bg="#777777")
    painel.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

    status_var = tk.StringVar(value="(Status do envio)")
    tk.Label(painel, text="Testar envio de vídeo", font=("Segoe UI",12), bg="#777777", fg="white").pack(fill=tk.X, pady=(0,4))
    tk.Label(painel, textvariable=status_var, bg="gray", fg="white").pack(fill=tk.X)
    progress = ttk.Progressbar(painel, orient="horizontal", length=200, mode='determinate')
    progress.pack(pady=5)

    def enviar_teste():
        arquivo = filedialog.askopenfilename(title="Selecione um vídeo", filetypes=[("Vídeos","*.mp4 *.mkv *.avi *.mov")])
        if not arquivo:
            return
        status_var.set("Enviando...")
        progress['value'] = 0
        root.after(300, lambda: progress.step(30))
        root.after(600, lambda: progress.step(30))
        root.after(900, lambda: progress.step(40))

        def tarefa():
            ok = client.enviar_video(arquivo, chat_id)
            status_var.set("✅ Enviado!" if ok else "❌ Erro")
            console_text.insert(tk.END, f"[Manual] Envio {'OK' if ok else 'FAIL'} -> {os.path.basename(arquivo)}\n")
            console_text.see(tk.END)

        threading.Thread(target=tarefa, daemon=True).start()

    tk.Button(painel, text="Selecionar e Enviar", command=enviar_teste, bg="#00cc66", fg="white", width=25).pack(pady=8)
    tk.Button(painel, text="Abrir pasta monitorada", command=lambda: os.startfile(pasta), width=30).pack(pady=3)
    tk.Button(painel, text="Visualizar config/ID", command=lambda: messagebox.showinfo("Configuração", f"Pasta: {pasta}\nChat ID: {chat_id}\nVersão: {VERSAO_ATUAL}\nID: {cliper_id}"), width=30).pack(pady=3)
    tk.Button(painel, text="Limpar console", command=lambda: console_text.delete('1.0', tk.END), width=30).pack(pady=3)

    handler  = DebugVideoHandler(console_text, client, chat_id)
    observer = Observer()
    observer.schedule(handler, path=pasta, recursive=False)
    observer.start()
    console_text.insert(tk.END, f"[Monitor] Iniciando monitoramento em: {pasta}\n")
    console_text.see(tk.END)

    root.protocol("WM_DELETE_WINDOW", lambda: (observer.stop(), observer.join(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()
