import subprocess
import sys

VERSAO_ATUAL = "1.6"

# Instalação automática de dependências

def instalar(modulo, nome_pip=None):
    try:
        __import__(modulo)
    except ImportError:
        print(f"📦 Instalando dependência: {modulo}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", nome_pip or modulo])

for lib in [
    ("requests",),
    ("win32api", "pywin32"),
    ("win32event", "pywin32"),
    ("watchdog",),
    ("PIL", "Pillow"),
    ("pystray",),
]:
    instalar(*lib)

import os
import time
import json
import logging
import threading
import tkinter as tk
import winreg
import win32event
import win32api
import winerror
import uuid
from tkinter import messagebox, filedialog
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem
import requests

mutex_name = "CliperInstance"
mutex = win32event.CreateMutex(None, False, mutex_name)
if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
    print("⚠️ Cliper já está em execução.")
    sys.exit()

TELEGRAM_TOKEN = ""
EXTENSOES_VIDEOS = ['.mp4', '.mkv', '.avi', '.mov']
CLIPER_DIR = os.path.join(os.getenv("APPDATA"), "Cliper")
CONFIG_PATH = os.path.join(CLIPER_DIR, "config.json")
ICON_PATH = os.path.join(os.path.dirname(__file__), "cliper.ico")
ID_ARQUIVO = os.path.join(CLIPER_DIR, "id.json")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CHAT_ID = None
PASTA_MONITORADA = None
INSTANCIA_ID = str(uuid.uuid4())

# Proteção contra cópia de config.json

def validar_instancia():
    if os.path.exists(ID_ARQUIVO):
        with open(ID_ARQUIVO, "r") as f:
            antigo = json.load(f).get("id")
            if antigo != INSTANCIA_ID:
                print("❌ Configuração copiada de outra máquina. Reconfigurando...")
                os.remove(CONFIG_PATH)
                os.remove(ID_ARQUIVO)
                return False
    else:
        with open(ID_ARQUIVO, "w") as f:
            json.dump({"id": INSTANCIA_ID}, f)
    return True

# Salvar e carregar configuração

def salvar_config_local(chat_id, pasta):
    os.makedirs(CLIPER_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"chat_id": chat_id, "pasta": pasta, "versao": VERSAO_ATUAL}, f)
    with open(ID_ARQUIVO, "w") as f:
        json.dump({"id": INSTANCIA_ID}, f)
    logging.info("Configuração salva localmente.")

def carregar_config_local():
    global CHAT_ID, PASTA_MONITORADA
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            dados = json.load(f)
            if dados.get("versao") != VERSAO_ATUAL:
                os.remove(CONFIG_PATH)
                logging.warning("Versão antiga detectada. Reconfigurando...")
                return False
            CHAT_ID = dados.get("chat_id")
            PASTA_MONITORADA = dados.get("pasta")
            logging.info("Configuração carregada.")
            return validar_instancia()
    return False

# Configuração inicial

def configurar_primeira_vez():
    global CHAT_ID, PASTA_MONITORADA
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Cliper", "Configuração inicial:\nEscolha a pasta a ser monitorada.")
    pasta = filedialog.askdirectory(title="Selecione a pasta")
    if not pasta:
        messagebox.showerror("Erro", "Pasta não selecionada.")
        sys.exit(1)
    PASTA_MONITORADA = pasta
    messagebox.showinfo("Telegram", "Envie uma mensagem para seu bot e clique em OK.")
    CHAT_ID = telegram_client.detectar_chat_id()
    salvar_config_local(CHAT_ID, PASTA_MONITORADA)

class TelegramClient:
    def __init__(self, token):
        self.token = token
        self.session = requests.Session()
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def detectar_chat_id(self):
        logging.info("Aguardando mensagem no bot do Telegram...")
        ultimo_id = None
        url = f"{self.base_url}/getUpdates"
        while True:
            try:
                res = self.session.get(url, timeout=10)
                updates = res.json().get("result", [])
                if updates:
                    ultimo = updates[-1]
                    if "message" in ultimo and ultimo["update_id"] != ultimo_id:
                        ultimo_id = ultimo["update_id"]
                        chat_id = ultimo["message"]["chat"]["id"]
                        nome = ultimo["message"]["chat"].get("first_name", "Usuário")
                        logging.info(f"Chat ID capturado: {chat_id} ({nome})")
                        return chat_id
            except Exception as e:
                logging.error("Erro ao buscar chat_id: %s", e)
            time.sleep(1)

    def enviar_video(self, caminho, chat_id):
        url = f"{self.base_url}/sendVideo"
        nome = os.path.basename(caminho)
        try:
            with open(caminho, 'rb') as f:
                files = {'video': (nome, f)}
                data = {'chat_id': chat_id, 'caption': f"📹 Novo vídeo: {nome}"}
                res = self.session.post(url, data=data, files=files)
            if res.status_code == 200:
                logging.info("Vídeo enviado com sucesso.")
            else:
                logging.warning("Erro do Telegram: %s", res.text)
        except Exception as e:
            logging.error("Erro ao enviar vídeo: %s", e)

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
                logging.info("Vídeo detectado: %s", event.src_path)
                enviar_video(event.src_path)

def iniciar_monitoramento():
    observer = Observer()
    observer.schedule(VideoHandler(), path=PASTA_MONITORADA, recursive=False)
    observer.start()
    logging.info("Monitorando: %s", PASTA_MONITORADA)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def iniciar_monitoramento_em_thread():
    threading.Thread(target=iniciar_monitoramento, daemon=True).start()

def criar_icone_tray():
    try:
        image = Image.open(ICON_PATH)
    except:
        image = Image.new("RGB", (64, 64), "black")
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill="white")
    icon = Icon("Cliper", icon=image, title="Cliper - Rodando")
    icon.menu = Menu(MenuItem("Sair", lambda icon, item: icon.stop()))
    iniciar_monitoramento_em_thread()
    icon.run()

def adicionar_inicio_automatico():
    nome = "Cliper"
    caminho = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
    try:
        chave = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(chave, nome, 0, winreg.REG_SZ, f'"{caminho}" --no-menu')
        winreg.CloseKey(chave)
        logging.info("Início automático ativado.")
    except Exception as e:
        logging.error("Erro ao ativar início automático: %s", e)

def exibir_menu():
    root = tk.Tk()
    root.iconbitmap(ICON_PATH)
    root.title("Cliper - Modo de Execução")
    root.geometry("360x250")
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

    def modo_debug():
        from tkinter.simpledialog import askstring
        senha = askstring("Senha", "Digite a senha:", show="*")
        if senha == "2202":
            path = os.path.abspath(__file__)
            os.system(f'start cmd /k ""{sys.executable}" "{path}" --debug"')
        else:
            messagebox.showerror("Erro", "Senha incorreta")

    tk.Label(root, text="CLIPER - MODO DE EXECUÇÃO", fg="white", bg="#1e1e1e", font=("Segoe UI", 12, "bold")).pack(pady=15)
    tk.Button(root, text="1 - Rodar normalmente (com janela)", command=modo1, width=40).pack(pady=5)
    tk.Button(root, text="2 - Rodar minimizado", command=modo2, width=40).pack(pady=5)
    tk.Button(root, text="3 - Rodar em segundo plano (bandeja)", command=modo3, width=40).pack(pady=5)
    tk.Button(root, text="4 - Acessar modo DEBUG (senha)", command=modo_debug, width=40).pack(pady=5)

    root.mainloop()

def exibir_tela_status():
    janela = tk.Tk()
    janela.title("Cliper - Em execução")
    janela.geometry("300x100")
    janela.configure(bg="#2e2e2e")
    tk.Label(janela, text="✅ Cliper rodando...\nMonitorando por vídeos.", fg="white", bg="#2e2e2e").pack(pady=20)
    janela.mainloop()

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        adicionar_inicio_automatico()

    if "--debug" in sys.argv:
        logging.getLogger().setLevel(logging.DEBUG)
        if not os.path.exists(CLIPER_DIR) or not os.path.exists(CONFIG_PATH) or not carregar_config_local():
            configurar_primeira_vez()
        iniciar_monitoramento()
        sys.exit()

    if not os.path.exists(CLIPER_DIR) or not os.path.exists(CONFIG_PATH) or not carregar_config_local():
        configurar_primeira_vez()

    if len(sys.argv) > 1 and sys.argv[1] == "--no-menu":
        criar_icone_tray()
    else:
        exibir_menu()
