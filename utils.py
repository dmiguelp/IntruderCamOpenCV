# utils.py
# Funciones utilitarias (sonido, timestamp, listado de evidencias) no bloqueantes
import time
import threading
import pygame
import os

# Inicializar mixer globalmente cuando se importe utils
try:
    pygame.mixer.init()
except Exception:
    # Si falla, algunas funciones de sonido no estarán disponibles, pero el resto sigue.
    pass

def play_sound_nonblocking(path):
    """Reproduce un WAV (no bloqueante). No lanza excepción si falla."""
    def _play(p):
        try:
            pygame.mixer.music.load(p)
            pygame.mixer.music.play()
        except Exception as e:
            print("[utils.play_sound] Error:", e)
    if os.path.exists(path):
        threading.Thread(target=_play, args=(path,), daemon=True).start()
    else:
        # archivo no existe: no hacer nada (evita crash)
        # print("[utils.play_sound] fichero no encontrado:", path)
        pass

def timestamp():
    return time.strftime("%d%m%Y_%H%M%S")

def list_evid_files(evid_dir):
    exts = ('.avi', '.mp4', '.mov', '.jpg', '.jpeg', '.png')
    files = [f for f in os.listdir(evid_dir) if f.lower().endswith(exts)]
    files = sorted(files, reverse=True)
    return files
