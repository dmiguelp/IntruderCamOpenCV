# main.py
# Archivo que arranca todo y lanza la GUI
# Aquí también está el loop que usa root.after para iterar y llamar a DetectorGUI.loop_iteration()
import cv2
import tkinter as tk
from collections import deque
import threading
import time
import os

import config as cfg
from utils import list_evid_files
from gui import DetectorGUI

def main():
    # inicializar cámara y detectores
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("No se puede abrir la cámara")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = cfg.FPS_FALLBACK

    haar = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(haar)
    backSub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=True)

    # buffers y lock
    frame_buffer = deque(maxlen=cfg.FRAME_BUFFER_SIZE)
    record_queue = deque()
    lock = threading.Lock()

    # lanzar GUI
    root = tk.Tk()
    app = DetectorGUI(root, cap, backSub, face_cascade, cfg, frame_buffer, record_queue, lock)

    # preparar el bucle
    def loop():
        app.loop_iteration()
        root.after(int(1000 / max(1, fps)), loop)

    root.after(0, loop)
    root.protocol("WM_DELETE_WINDOW", app.shutdown)
    root.mainloop()

    # limpieza
    with lock:
        # parar grabación manual
        try:
            app.recorder.stop_manual_recording()
        except Exception:
            pass
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
