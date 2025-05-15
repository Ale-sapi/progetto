import pyperclip
import keyboard
import google.generativeai as genai
import time
import re
import threading
import tkinter as tk
from tkinter import messagebox
from tkinter import scrolledtext
from keyboard import add_hotkey
from tkinter import PhotoImage, messagebox  # Import for handling images/icons and showing alerts
import os  # Import for file existence check
import sys  # Import for system-specific parameters and functions
import signal  # Import for signal handling
import subprocess  # Import for running subprocesses
from PIL import ImageGrab  # Per catturare screenshot

# Config e variabili globali
GOOGLE_API_KEY = 'AIzaSyBL59lBTfKPJaVw8s8IqwD6TyiXG0h0Dz0'
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')
chat = model.start_chat()

gui_instance = None    # Unica istanza Tk
gui_thread = None      # Thread dedicato alla GUI
screenshot_lock = threading.Lock()  # Lock per evitare chiamate multiple

def reset_memory():
    global chat
    chat = model.start_chat()  # Reinitialize the chat object
    print("[✓] Memoria della chat resettata. Ora puoi iniziare una nuova conversazione.")

def send_to_gemini(text, concise=True):
    # Ottimizzazione per richieste JSON/schema
    lowered = text.lower()
    if ("json" in lowered or "schema" in lowered):
        text = (
            "Rispondi solo con il codice JSON completo, senza commenti, spiegazioni o testo aggiuntivo. "
            "Se la richiesta è uno schema, fornisci solo lo schema JSON puro. "
            f"{text}"
        )
    elif concise:
        text = f"Please respond in Italian and answer briefly and concisely: {text}"
    else:
        text = f"Please respond in Italian: {text}"
    response = chat.send_message(text)
    return response.text

def remove_formatting(text):
    if '`' in text:
        return text
    text = re.sub(r'(\*\*|\*|_|`|~)', '', text)
    return text

def on_send(entry):
    txt = entry.get().strip()
    if not txt:
        return
    resp = send_to_gemini(txt)
    clean = remove_formatting(resp)
    w = gui_instance.output
    w.config(state=tk.NORMAL)
    w.delete('1.0', tk.END)
    w.insert(tk.END, clean)
    w.config(state=tk.DISABLED)

def setup_gui(root):
    """Costruisci l'interfaccia utente con look migliorato e focus automatico."""
    root.title("Gemini Search ✨")
    root.geometry("600x300")
    root.configure(bg="#2e2e2e")              # sfondo più scuro
    root.attributes('-alpha', 0.95, '-topmost', True)

    # Input
    frm = tk.Frame(root, bg="#2e2e2e")
    frm.pack(fill=tk.X, padx=12, pady=12)
    entry = tk.Entry(
        frm, 
        bg="#3e3e3e", fg="#ffffff", insertbackground="#ffffff",
        font=("Segoe UI", 12), relief="flat"
    )
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,6), ipady=6)
    entry.focus_set()                        # focus automatico
    entry.bind("<Return>", lambda event: on_send(entry))  # Invio con tasto Enter

    # Close button
    btn_close = tk.Button(
        frm, text="❌", 
        bg="#ff5c5c", fg="#ffffff", activebackground="#ff7d7d",
        font=("Segoe UI", 10), relief="flat",
        command=lambda: root.withdraw()
    )
    btn_close.pack(side=tk.RIGHT, padx=(6, 0))  # Posizionato a destra del pulsante "Invia"

    # Send button
    send = tk.Button(
        frm, text="Invia", 
        bg="#5c5cff", fg="#ffffff", activebackground="#7d7dff",
        font=("Segoe UI", 12, "bold"), relief="flat",
        command=lambda: on_send(entry)
    )
    send.pack(side=tk.RIGHT)  # Posizionato a sinistra del pulsante "❌"

    # Output
    txt = scrolledtext.ScrolledText(
        root, 
        bg="#3e3e3e", fg="#ffffff", font=("Segoe UI", 12),
        wrap=tk.WORD, relief="flat", bd=0
    )
    txt.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,12))
    txt.config(highlightthickness=1, highlightbackground="#5c5cff")

    # Copy button in overlay (top-right of output box)
    btn_copy = tk.Button(
        root, text="Copia", 
        bg="#5c5cff", fg="#ffffff", activebackground="#7d7dff",
        font=("Segoe UI", 12, "bold"), relief="flat",
        command=lambda: pyperclip.copy(root.output.get("1.0", tk.END).strip())
    )
    # Place the button in overlay (bottom-right corner of the output box)
    def place_copy_btn(event=None):
        txt.update_idletasks()
        x = txt.winfo_x() + (txt.winfo_width() // 2) - 40  # 40 è metà larghezza bottone
        y = txt.winfo_y() + txt.winfo_height()  # 40px dal basso
        btn_copy.place(x=x, y=y, width=80, height=32)
    txt.bind('<Configure>', place_copy_btn)
    root.after(100, place_copy_btn)

    root.protocol("WM_DELETE_WINDOW", root.withdraw)

    # store refs
    root.entry = entry
    root.output = txt

def gui_thread_target():
    global gui_instance
    gui_instance = tk.Tk()
    setup_gui(gui_instance)
    gui_instance.mainloop()
    gui_instance = None  # quando chiude

def toggle_gui():
    global gui_instance, gui_thread
    if gui_instance is None:
        gui_thread = threading.Thread(target=gui_thread_target, daemon=True)
        gui_thread.start()
    else:
        try:
            if gui_instance.state() == 'withdrawn':
                gui_instance.deiconify()
                gui_instance.lift()
                gui_instance.entry.focus_set()  # Imposta il focus sul campo di input
            else:
                gui_instance.withdraw()
        except:
            pass

# Funzione per catturare screenshot e inviarlo
def send_screenshot_to_gemini():
    if not screenshot_lock.acquire(blocking=False):
        print("[!] Screenshot già in corso, attendi...")
        return
    try:
        print("[→] Cattura screenshot dell'intero schermo...")
        screenshot = ImageGrab.grab()
        # Prompt ottimizzato: rispondi solo con schema JSON se richiesto, altrimenti rispondi in italiano in modo conciso
        last_user_message = ""
        if hasattr(chat, 'history') and chat.history:
            last = chat.history[-1]
            # Prova ad accedere al testo, gestendo diversi possibili attributi
            if hasattr(last, 'parts') and last.parts:
                last_user_message = str(last.parts[0])
            elif hasattr(last, 'text'):
                last_user_message = str(last.text)
            else:
                last_user_message = str(last)
        if 'json' in last_user_message.lower() or 'schema' in last_user_message.lower():
            prompt = (
                "Rispondi solo con il codice JSON completo, senza commenti, spiegazioni o testo aggiuntivo. "
                "Se la richiesta è uno schema, fornisci solo lo schema JSON puro. "
                "Ecco l'immagine:"
            )
        else:
            prompt = "Rispondi in italiano in modo conciso a ciò che vedi in questa immagine:"
        response = chat.send_message([prompt, screenshot])
        clean = remove_formatting(response.text)
        pyperclip.copy(clean)
        print("[✓] Risposta copiata negli appunti!")
    except Exception as e:
        print(f"[!] Errore durante l'invio dello screenshot: {e}")
    finally:
        screenshot_lock.release()

def show_help():
    help_text = (
        "Comandi disponibili:\n"
        "Ctrl+Shift+J: Riavvia lo script\n"
        "Alt+Q: Mostra/nascondi la GUI\n"
        "Ctrl+Shift+H: Invia appunti\n"
        "Ctrl+Shift+0: Resetta memoria\n"
        "Ctrl+Shift+Alt+F: Copia la risposta\n"
        "Ctrl+Shift+X: Invia screenshot\n"
        "Ctrl+Shift+?: Mostra questa guida\n"
        "ESC: Esci"
    )
    try:
        pyperclip.copy(help_text)
        print("[✓] Guida copiata negli appunti!")
    except Exception:
        pass

def main():
    # Hotkeys
    keyboard.add_hotkey('ctrl+shift+j', lambda: os.execl(sys.executable, '"' + sys.executable + '"', os.path.abspath(__file__)))
    keyboard.add_hotkey('alt+q', toggle_gui)
    keyboard.add_hotkey('ctrl+shift+h', send_clipboard := lambda: pyperclip.copy(remove_formatting(send_to_gemini(pyperclip.paste()))))
    keyboard.add_hotkey('ctrl+shift+0', reset_memory := lambda: print("[✓] Memoria resettata") or model.start_chat())
    keyboard.add_hotkey('ctrl+shift+alt+f', copy := lambda: pyperclip.copy(gui_instance.output.get("1.0", tk.END)) if gui_instance else None)
    keyboard.add_hotkey('ctrl+shift+x', send_screenshot_to_gemini)
    keyboard.add_hotkey('ctrl+shift+?', show_help)

    print("<--> Premi Ctrl+Shift+J per riavviare lo script")
    print("<--> Premi Alt+Q per mostrare/nascondere la GUI")
    print("<--> Premi Ctrl+Shift+H per inviare appunti")
    print("<--> Premi Ctrl+Shift+0 per resettare memoria")
    print("<--> Premi Ctrl+Shift+Alt+F per copiare la risposta")
    print("<--> Premi Ctrl+Shift+X per inviare uno screenshot")
    print("<--> Premi Ctrl+Shift+? per mostrare la guida dei comandi")

    keyboard.wait('esc')

if __name__ == "__main__":
    main()
