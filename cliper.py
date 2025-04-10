import os
import sys
import time
import json
import requests
import threading
import tkinter as tk
import winreg
from tkinter import messagebox, filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

# === Configs fixas ===
TELEGRAM_TOKEN = ""
EXTENSOES_VIDEOS = ['.mp4', '.mkv', '.avi', '.mov']
CLIPER_DIR = os.path.join(os.getenv("APPDATA"), "CliperBot")
CONFIG_PATH = os.path.join(CLIPER_DIR, "config.json")

# === Variáveis globais ===
CHAT_ID = None
PASTA_MONITORADA = None

# === Icone e diretórios ===
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    EXEC_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)
    EXEC_DIR = BASE_DIR
ICON_PATH = os.path.join(BASE_DIR, "cliper.ico")

# === Salvar e carregar configuração local ===
def salvar_config_local(chat_id, pasta):
    os.makedirs(CLIPER_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({
            "chat_id": chat_id,
            "pasta": pasta
        }, f)

def carregar_config_local():
    global CHAT_ID, PASTA_MONITORADA
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            dados = json.load(f)
            CHAT_ID = dados.get("chat_id")
            PASTA_MONITORADA = dados.get("pasta")
            return True
    return False

# === Perguntar ao usuário e salvar ===
def configurar_primeira_vez():
    global CHAT_ID, PASTA_MONITORADA

    root = tk.Tk()
    root.withdraw()

    messagebox.showinfo("CliperBot", "Configuração inicial:\nEscolha a pasta a ser monitorada.")
    pasta = filedialog.askdirectory(title="Selecione a pasta")
    if not pasta:
        messagebox.showerror("Erro", "Pasta não selecionada.")
        sys.exit(1)
    PASTA_MONITORADA = pasta

    messagebox.showinfo("Telegram", "Envie uma mensagem para seu bot e clique em OK.")
    CHAT_ID = detectar_chat_id(TELEGRAM_TOKEN)

    salvar_config_local(CHAT_ID, PASTA_MONITORADA)

# === Detectar chat ID ===
def detectar_chat_id(bot_token):
    print("⏳ Aguardando mensagem no bot do Telegram...")
    ultimo_id = None
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    while True:
        try:
            res = requests.get(url, timeout=10)
            updates = res.json().get("result", [])
            if updates:
                ultimo = updates[-1]
                if "message" in ultimo and ultimo["update_id"] != ultimo_id:
                    ultimo_id = ultimo["update_id"]
                    chat_id = ultimo["message"]["chat"]["id"]
                    nome = ultimo["message"]["chat"].get("first_name", "Usuário")
                    print(f"✅ Chat ID capturado: {chat_id} ({nome})")
                    return chat_id
        except Exception as e:
            print("❌ Erro ao buscar chat_id:", e)
        time.sleep(1)

# === Enviar vídeo ===
def enviar_telegram(caminho):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
    nome = os.path.basename(caminho)
    try:
        with open(caminho, 'rb') as f:
            files = {'video': (nome, f)}
            data = {'chat_id': CHAT_ID, 'caption': f"📹 Novo vídeo: {nome}"}
            res = requests.post(url, data=data, files=files)
        if res.status_code == 200:
            print("✅ Enviado para o Telegram.")
        else:
            print("⚠️ Telegram:", res.text)
    except Exception as e:
        print("❌ Erro Telegram:", e)

def enviar_video(caminho):
    threading.Thread(target=enviar_telegram, args=(caminho,), daemon=True).start()

# === Monitoramento ===
class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            _, ext = os.path.splitext(event.src_path)
            if ext.lower() in EXTENSOES_VIDEOS:
                time.sleep(2)
                print(f"🎥 Vídeo detectado: {event.src_path}")
                enviar_video(event.src_path)

def iniciar_monitoramento():
    observer = Observer()
    observer.schedule(VideoHandler(), path=PASTA_MONITORADA, recursive=False)
    observer.start()
    print("🔍 Monitorando:", PASTA_MONITORADA)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def iniciar_monitoramento_em_thread():
    threading.Thread(target=iniciar_monitoramento, daemon=True).start()

# === Ícone bandeja ===
def criar_icone_tray():
    try:
        image = Image.open(ICON_PATH)
    except:
        image = Image.new("RGB", (64, 64), "black")
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill="white")
    icon = Icon("Cliper")
    icon.icon = image
    icon.title = "Cliper - Rodando"
    icon.menu = Menu(MenuItem("Sair", lambda icon, item: icon.stop()))
    iniciar_monitoramento_em_thread()
    icon.run()

# === Início automático ===
def adicionar_inicio_automatico():
    nome = "CliperBot"
    caminho = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
    try:
        chave = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(chave, nome, 0, winreg.REG_SZ, f'"{caminho}" --no-menu')
        winreg.CloseKey(chave)
        print("🔁 Início automático ativado.")
    except Exception as e:
        print("❌ Erro ao ativar início automático:", e)

# === Menu ===
def exibir_menu():
    root = tk.Tk()
    root.title("CliperBot - Modo de Execução")
    root.geometry("360x200")
    root.configure(bg="#1e1e1e")

    def modo1():
        root.destroy()
        iniciar_monitoramento_em_thread()
        exibir_tela_status()

    def modo2():
        root.destroy()
        iniciar_monitoramento_em_thread()

    def modo3():
        root.destroy()
        criar_icone_tray()

    label = tk.Label(root, text="CLIPERBOT - MODO DE EXECUÇÃO", fg="white", bg="#1e1e1e", font=("Segoe UI", 12, "bold"))
    label.pack(pady=15)

    tk.Button(root, text="1 - Rodar normalmente (com janela)", command=modo1, width=40).pack(pady=5)
    tk.Button(root, text="2 - Rodar minimizado", command=modo2, width=40).pack(pady=5)
    tk.Button(root, text="3 - Rodar em segundo plano (bandeja)", command=modo3, width=40).pack(pady=5)

    root.mainloop()

def exibir_tela_status():
    janela = tk.Tk()
    janela.title("CliperBot - Em execução")
    janela.geometry("300x100")
    janela.configure(bg="#2e2e2e")
    label = tk.Label(janela, text="✅ CliperBot rodando...\nMonitorando por vídeos.",
                     fg="white", bg="#2e2e2e")
    label.pack(pady=20)
    janela.mainloop()

# === Execução principal ===
if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        adicionar_inicio_automatico()

    if not os.path.exists(CLIPER_DIR) or not os.path.exists(CONFIG_PATH):
        configurar_primeira_vez()
    else:
        carregar_config_local()

    if len(sys.argv) > 1 and sys.argv[1] == "--no-menu":
        criar_icone_tray()
    else:
        exibir_menu()
