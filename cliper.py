# cliper.py
import subprocess
import sys

def instalar(modulo, nome_pip=None):
    try:
        __import__(modulo)
    except ImportError:
        pacote = nome_pip or modulo
        print(f"[INFO] Instalando dependência: {pacote}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pacote])

DEPENDENCIAS = [
    ("requests",),
    ("watchdog",),
    ("PIL", "Pillow"),
    ("pystray",),
    ("win32api", "pywin32"),
    ("win32event", "pywin32"),
]

for lib in DEPENDENCIAS:
    instalar(*lib)

import debug_ui

import os
import time
import json
import logging
import threading
import tkinter as tk
import tkinter.ttk as ttk
import winreg
import uuid
import subprocess as sp
from tkinter import messagebox, filedialog, simpledialog
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem
import requests
import win32api
import win32event
import winerror

VERSAO_ATUAL     = "1.7"
MIN_SIZE_BYTES   = 5 * 1024 * 1024
EXTENSOES_VIDEOS = ['.mp4', '.mkv', '.avi', '.mov']
TELEGRAM_TOKEN   = ":P"
CLIPER_DIR       = os.path.join(os.getenv("APPDATA"), "Cliper")
CONFIG_PATH      = os.path.join(CLIPER_DIR, "config.json")
ID_PATH          = os.path.join(CLIPER_DIR, "id.json")
ICON_PATH        = os.path.join(os.path.dirname(__file__), "cliper.ico")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    EXEC_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)
    EXEC_DIR = BASE_DIR

CHAT_ID = None
PASTA_MONITORADA = None
CLIPER_ID = None

def gerar_id():
    return str(uuid.uuid4())[:8]

def carregar_id():
    global CLIPER_ID
    os.makedirs(CLIPER_DIR, exist_ok=True)
    try:
        if os.path.exists(ID_PATH):
            with open(ID_PATH, "r") as f:
                dados = json.load(f)
            CLIPER_ID = dados.get("id")
            logging.info("[INFO] ID carregado: %s", CLIPER_ID)
            return
    except Exception as e:
        logging.error("[ERRO] Falha ao carregar ID: %s", e)
    CLIPER_ID = gerar_id()
    with open(ID_PATH, "w") as f:
        json.dump({"id": CLIPER_ID}, f)
    logging.info("[INFO] Novo ID gerado: %s", CLIPER_ID)

def salvar_config_local(chat_id, pasta):
    os.makedirs(CLIPER_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"chat_id": chat_id, "pasta": pasta, "versao": VERSAO_ATUAL}, f)

def carregar_config_local():
    global CHAT_ID, PASTA_MONITORADA
    if not os.path.exists(CONFIG_PATH):
        return False
    try:
        with open(CONFIG_PATH, "r") as f:
            dados = json.load(f)
        if dados.get("versao") != VERSAO_ATUAL:
            os.remove(CONFIG_PATH)
            logging.warning("[WARN] Configuração antiga. Reconfigurando...")
            return False
        CHAT_ID = dados.get("chat_id")
        PASTA_MONITORADA = dados.get("pasta")
        logging.info("[INFO] Config carregada com sucesso.")
        return True
    except Exception as e:
        logging.error("[ERRO] Falha ao ler config.json: %s", e)
        return False

def configurar_primeira_vez():
    global CHAT_ID, PASTA_MONITORADA
    root = tk.Tk(); root.withdraw()
    messagebox.showinfo("Cliper", "Escolha a pasta para monitorar.")
    pasta = filedialog.askdirectory(title="Selecionar pasta")
    if not pasta:
        messagebox.showerror("Erro", "Nenhuma pasta selecionada.")
        sys.exit(1)
    PASTA_MONITORADA = pasta
    messagebox.showinfo("Telegram", "Envie uma mensagem para o bot no computador.")
    CHAT_ID = telegram_client.detectar_chat_id()
    salvar_config_local(CHAT_ID, PASTA_MONITORADA)

class TelegramClient:
    def __init__(self, token):
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()

    def detectar_chat_id(self):
        logging.info("[INFO] Aguardando mensagem no bot do Telegram…")
        ultimo = None
        url = f"{self.base_url}/getUpdates"
        while True:
            try:
                res = self.session.get(url, timeout=10).json()
                updates = res.get("result", [])
                if updates:
                    last = updates[-1]
                    if last["update_id"] != ultimo and "message" in last:
                        ultimo = last["update_id"]
                        cid = last["message"]["chat"]["id"]
                        nome = last["message"]["chat"].get("first_name", "Usuario")
                        logging.info("[INFO] Chat ID capturado: %s (%s)", cid, nome)
                        return cid
            except Exception as e:
                logging.error("[ERRO] Erro ao buscar chat_id: %s", e)
            time.sleep(1)

    def enviar_video(self, caminho, chat_id):
        size = os.path.getsize(caminho)
        if size < MIN_SIZE_BYTES:
            logging.warning("[WARN] Vídeo pulado (%.1f MB < 5 MB): %s", size/1024/1024, caminho)
            return
        url = f"{self.base_url}/sendVideo"
        nome = os.path.basename(caminho)
        try:
            with open(caminho, "rb") as f:
                files = {"video": (nome, f)}
                data = {"chat_id": chat_id, "caption": f"Novo vídeo: {nome}"}
                res = self.session.post(url, data=data, files=files)
            if res.status_code == 200:
                logging.info("[INFO] Vídeo enviado: %s", nome)
            else:
                logging.warning("[WARN] Falha ao enviar: %s", res.text)
        except Exception as e:
            logging.error("[ERRO] Erro ao enviar vídeo: %s", e)

telegram_client = TelegramClient(TELEGRAM_TOKEN)
executor = ThreadPoolExecutor(max_workers=4)

def enviar_video(caminho):
    executor.submit(telegram_client.enviar_video, caminho, CHAT_ID)

class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            _, ext = os.path.splitext(event.src_path)
            if ext.lower() in EXTENSOES_VIDEOS:
                time.sleep(2)
                logging.info("[INFO] Vídeo detectado: %s", event.src_path)
                enviar_video(event.src_path)

def iniciar_monitoramento():
    obs = Observer()
    obs.schedule(VideoHandler(), path=PASTA_MONITORADA, recursive=False)
    obs.start()
    logging.info("[INFO] Monitorando: %s", PASTA_MONITORADA)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()

def iniciar_monitoramento_em_thread():
    threading.Thread(target=iniciar_monitoramento, daemon=True).start()

def iniciar_debug():
    pw_root = tk.Tk(); pw_root.withdraw()
    senha = simpledialog.askstring("Modo Debug", "Digite a senha para entrar no modo debug:", parent=pw_root, show="*")
    pw_root.destroy()
    if senha != "2202":
        messagebox.showerror("Erro", "Senha incorreta.")
        return
    debug_ui.main()

def criar_icone_tray():
    try:
        img = Image.open(ICON_PATH)
    except:
        img = Image.new("RGB", (64,64), "black")
        draw = ImageDraw.Draw(img); draw.rectangle((16,16,48,48), fill="white")
    icon = Icon("Cliper", icon=img, title="Cliper - Rodando")
    icon.menu = Menu(MenuItem("Sair", lambda i,_: i.stop()))
    iniciar_monitoramento_em_thread()
    icon.run()

def adicionar_inicio_automatico():
    nome = "Cliper"
    caminho = sys.executable if getattr(sys,'frozen',False) else os.path.abspath(__file__)
    try:
        chave = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(chave, nome, 0, winreg.REG_SZ, f'"{caminho}" --no-menu')
        winreg.CloseKey(chave)
        logging.info("[INFO] Início automático configurado.")
    except Exception as e:
        logging.error("[ERRO] Ao configurar início automático: %s", e)

def exibir_tela_status():
    win = tk.Tk()
    win.title("Cliper - Executando")
    win.geometry("300x100")
    win.configure(bg="#2e2e2e")
    tk.Label(win, text="Cliper rodando...\nMonitorando vídeos.", fg="white", bg="#2e2e2e").pack(pady=20)
    win.mainloop()

def exibir_menu():
    root = tk.Tk()
    root.iconbitmap(ICON_PATH)
    root.title("Cliper - Modo de Execução")
    root.geometry("360x160")
    root.configure(bg="#1e1e1e")
    tk.Button(root, text="1 - Rodar com janela", command=lambda:[root.destroy(), iniciar_monitoramento_em_thread(), exibir_tela_status()], width=40).pack(pady=5)
    tk.Button(root, text="2 - Rodar minimizado", command=lambda:[root.destroy(), iniciar_monitoramento_em_thread()], width=40).pack(pady=5)
    tk.Button(root, text="3 - Rodar na bandeja", command=lambda:[root.destroy(), criar_icone_tray()], width=40).pack(pady=5)
    tk.Button(root, text="4 - Modo debug (senha)", command=iniciar_debug, width=40).pack(pady=5)
    root.mainloop()

if __name__ == "__main__":
    carregar_id()
    if getattr(sys, 'frozen', False):
        adicionar_inicio_automatico()
    if not os.path.exists(CLIPER_DIR) or not carregar_config_local():
        configurar_primeira_vez()
    if "--debug" in sys.argv:
        iniciar_debug()
    elif len(sys.argv) > 1 and sys.argv[1] == "--no-menu":
        criar_icone_tray()
    else:
        exibir_menu()
