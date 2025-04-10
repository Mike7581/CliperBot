import os
import sys
import time
import json
import logging
import threading
import tkinter as tk
import winreg
from tkinter import messagebox, filedialog
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem
import requests

# === Configurações e constantes ===
TELEGRAM_TOKEN = ""  # Token do bot Telegram
EXTENSOES_VIDEOS = ['.mp4', '.mkv', '.avi', '.mov']
CLIPER_DIR = os.path.join(os.getenv("APPDATA"), "CliperBot")
CONFIG_PATH = os.path.join(CLIPER_DIR, "config.json")
ICON_PATH = os.path.join(os.path.dirname(__file__), "cliper.ico")  # Ajuste se necessário

# === Logging ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === Configuração do ambiente ===
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    EXEC_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)
    EXEC_DIR = BASE_DIR

# === Variáveis de configuração global ===
CHAT_ID = None
PASTA_MONITORADA = None

# === Funções para salvar e carregar configuração local ===
def salvar_config_local(chat_id, pasta):
    os.makedirs(CLIPER_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"chat_id": chat_id, "pasta": pasta}, f)
    logging.info("Configuração salva localmente.")

def carregar_config_local():
    global CHAT_ID, PASTA_MONITORADA
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            dados = json.load(f)
            CHAT_ID = dados.get("chat_id")
            PASTA_MONITORADA = dados.get("pasta")
            logging.info("Configuração carregada.")
            return True
    return False

# === Função de configuração inicial ===
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

# === Classe para comunicação com o Telegram ===
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
                logging.info("Vídeo enviado para o Telegram com sucesso.")
            else:
                logging.warning("Telegram respondeu: %s", res.text)
        except Exception as e:
            logging.error("Erro ao enviar vídeo: %s", e)

# Inicializa o cliente do Telegram
telegram_client = TelegramClient(TELEGRAM_TOKEN)

# Executor para envio de vídeos (limita o número de threads simultâneas)
executor = ThreadPoolExecutor(max_workers=4)

def enviar_video(caminho):
    # Envia o vídeo utilizando o pool de threads
    executor.submit(telegram_client.enviar_video, caminho, CHAT_ID)

# === Monitoramento de Vídeos com Watchdog ===
class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            _, ext = os.path.splitext(event.src_path)
            if ext.lower() in EXTENSOES_VIDEOS:
                # Pequena espera para garantir que o arquivo esteja pronto
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

# === Funções para manipulação do Ícone na Bandeja ===
def criar_icone_tray():
    try:
        image = Image.open(ICON_PATH)
    except Exception as e:
        logging.error("Erro ao carregar ícone, utilizando placeholder: %s", e)
        image = Image.new("RGB", (64, 64), "black")
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill="white")
    icon = Icon("Cliper", icon=image, title="Cliper - Rodando")
    # Menu para encerrar o aplicativo
    icon.menu = Menu(MenuItem("Sair", lambda icon, item: icon.stop()))
    iniciar_monitoramento_em_thread()
    icon.run()

# === Configuração de Inicialização Automática no Windows ===
def adicionar_inicio_automatico():
    nome = "CliperBot"
    caminho = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
    try:
        chave = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(chave, nome, 0, winreg.REG_SZ, f'"{caminho}" --no-menu')
        winreg.CloseKey(chave)
        logging.info("Início automático ativado.")
    except Exception as e:
        logging.error("Erro ao ativar início automático: %s", e)

# === Interface Gráfica (Tkinter) ===
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

# === Execução Principal ===
if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        adicionar_inicio_automatico()

    if not os.path.exists(CLIPER_DIR) or not os.path.exists(CONFIG_PATH):
        configurar_primeira_vez()
    else:
        carregar_config_local()

    # Se o argumento for "--no-menu", iniciar sem GUI e com bandeja
    if len(sys.argv) > 1 and sys.argv[1] == "--no-menu":
        criar_icone_tray()
    else:
        exibir_menu()
