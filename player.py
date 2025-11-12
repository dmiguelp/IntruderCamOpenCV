# player.py
# Reproductor de imágenes y videos independiente (usando Tkinter y PIL)
import os
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2

class MediaPlayer:
    """
    MediaPlayer independiente.
    Uso:
        player = MediaPlayer(parent_tk_root, evid_dir, files_list, start_index)
    """
    def __init__(self, parent, evid_dir, files, index=0, max_size=(800,600)):
        self.parent = parent
        self.evid_dir = evid_dir
        self.files = list(files)
        self.index = int(index)
        self.max_w, self.max_h = max_size

        self.top = tk.Toplevel(parent)
        self.top.title(f"Reproductor - {self._filename}")
        self.top.protocol("WM_DELETE_WINDOW", self.on_close)

        # UI: etiqueta de imagen + controles
        self.lbl = ttk.Label(self.top)
        self.lbl.pack()

        ctrl = ttk.Frame(self.top)
        ctrl.pack(fill="x", pady=4)

        self.btn_prev = ttk.Button(ctrl, text="<< Prev", command=self.prev_file)
        self.btn_prev.pack(side="left", padx=2)
        self.btn_play = ttk.Button(ctrl, text="Play", command=self.toggle_play)
        self.btn_play.pack(side="left", padx=2)
        self.btn_next = ttk.Button(ctrl, text="Next >>", command=self.next_file)
        self.btn_next.pack(side="left", padx=2)
        self.btn_close = ttk.Button(ctrl, text="Cerrar", command=self.on_close)
        self.btn_close.pack(side="right", padx=2)

        # barra de progreso
        self.scale = ttk.Scale(self.top, from_=0, to=1, orient="horizontal", command=self.on_scale_move)
        self.scale.pack(fill="x", padx=6, pady=6)
        self.scale_enabled = False
        self.user_seek = False
        self.playing = False

        # etiqueta de tiempo
        self.time_label = ttk.Label(self.top, text="")
        self.time_label.pack()

        # estado de captura de video
        self.cap = None
        self.total_frames = 0
        self.cur_frame = 0
        self.cur_fps = 25  # fallback
        self._open_current()

    @property
    def _filename(self):
        return self.files[self.index] if (0 <= self.index < len(self.files)) else ""

    def _open_current(self):
        filename = self._filename
        if not filename:
            messagebox.showinfo("Reproductor", "No hay archivos en la lista")
            self.top.destroy()
            return
        path = os.path.join(self.evid_dir, filename)
        self.top.title(f"Reproductor - {filename}")
        ext = os.path.splitext(filename)[1].lower()

        if ext in ('.jpg', '.jpeg', '.png'):
            self._open_image(path)
        else:
            self._open_video(path)

    def _open_image(self, path):
        # imagen estática; desactivar barra
        try:
            img = cv2.imread(path)
            if img is None:
                raise RuntimeError("No se pudo leer la imagen")
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) # convertir a RGB para Pillow
            h, w = img_rgb.shape[:2]
            scale = min(self.max_w / w, self.max_h / h, 1.0)
            new_w, new_h = int(w*scale), int(h*scale)
            img_pil = Image.fromarray(img_rgb).resize((new_w, new_h))
            self.photo = ImageTk.PhotoImage(img_pil)
            self.lbl.config(image=self.photo)
            self.scale.state(['disabled'])
            self.scale_enabled = False
            self.playing = False
            self.btn_play.config(text="Play")
            self.time_label.config(text=f"Imagen {self.index+1}/{len(self.files)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se puede abrir la imagen:\n{e}")

    def _open_video(self, path):
        # abrir video con cv2.VideoCapture
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "No se puede abrir el vídeo seleccionado")
            return
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        self.cur_fps = (self.cap.get(cv2.CAP_PROP_FPS) or 25)
        if self.total_frames <= 0:
            self.total_frames = 1
        self.scale.config(from_=0, to=max(1, self.total_frames-1))
        self.scale.set(0)
        self.cur_frame = 0
        self.playing = True
        self.btn_play.config(text="Pause")
        self._play_loop()

    def _play_loop(self):
        if not self.cap or not self.playing:
            return
        ret, frame = self.cap.read()
        if not ret:
            # fin de video
            self.playing = False
            self.btn_play.config(text="Play")
            return
        self.cur_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(frame_rgb)
        # ajuste tamaño
        w, h = img_pil.size
        scale = min(self.max_w / w, self.max_h / h, 1.0)
        img_pil = img_pil.resize((int(w*scale), int(h*scale)))
        self.photo = ImageTk.PhotoImage(img_pil)
        self.lbl.config(image=self.photo)

        # actualizar slider sin disparar callback usuario
        self.user_seek = True
        try:
            self.scale.set(self.cur_frame)
        finally:
            self.top.after(10, lambda: setattr(self, 'user_seek', False))

        # actualizar time label
        total_s = int(self.total_frames / max(1, self.cur_fps))
        cur_s = int(self.cur_frame / max(1, self.cur_fps))
        self.time_label.config(text=f"{time.strftime('%M:%S', time.gmtime(cur_s))} / {time.strftime('%M:%S', time.gmtime(total_s))}")

        delay = int(1000 / max(1, self.cur_fps))
        self.top.after(delay, self._play_loop)

    def toggle_play(self):
        if not self.cap:
            return
        if self.playing:
            self.playing = False
            self.btn_play.config(text="Play")
        else:
            # si estamos al final, retrocedemos un frame para reanudar
            pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            if pos >= self.total_frames - 1:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.cur_frame = 0
            self.playing = True
            self.btn_play.config(text="Pause")
            self._play_loop()

    def on_scale_move(self, val):
        if not self.scale_enabled or self.user_seek:
            return
        pos = int(float(val))
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            self.cur_frame = pos
            ret, frame = self.cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(frame_rgb)
                w, h = img_pil.size
                scale = min(self.max_w / w, self.max_h / h, 1.0)
                img_pil = img_pil.resize((int(w*scale), int(h*scale)))
                self.photo = ImageTk.PhotoImage(img_pil)
                self.lbl.config(image=self.photo)
            total_s = int(self.total_frames / max(1, self.cur_fps))
            cur_s = int(self.cur_frame / max(1, self.cur_fps))
            self.time_label.config(text=f"{time.strftime('%M:%S', time.gmtime(cur_s))} / {time.strftime('%M:%S', time.gmtime(total_s))}")

    def prev_file(self):
        if self.index > 0:
            self.index -= 1
            self._restart_current()

    def next_file(self):
        if self.index < len(self.files) - 1:
            self.index += 1
            self._restart_current()

    def _restart_current(self):
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
        self.user_seek = False
        self.playing = False
        self._open_current()

    def on_close(self):
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
        try:
            self.top.destroy()
        except:
            pass
