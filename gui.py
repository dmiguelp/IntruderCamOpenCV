# gui.py 
# GUI modular: crea la ventana, sliders, botones, lista de evidencias, el reproductor con barra de progreso y el reproductor de Media
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import time
import os

from utils import list_evid_files, play_sound_nonblocking, timestamp
from processor import apply_hsv_adjust, aplicar_vision_nocturna_verde, aplicar_vision_termica, calcular_luminosidad, detect_motion_and_update
from recorder import RecorderManager
from player import MediaPlayer   

class DetectorGUI:
    def __init__(self, root, cap, backSub, face_cascade, cfg, frame_buffer, record_queue, lock):
        self.root = root
        self.cap = cap
        self.backSub = backSub
        self.face_cascade = face_cascade
        self.cfg = cfg

        self.frame_buffer = frame_buffer
        self.record_queue = record_queue
        self.lock = lock

        # recorder manager
        self.recorder = RecorderManager(cfg.EVID_DIR, int(max(1, cap.get(cv2.CAP_PROP_FPS) or cfg.FPS_FALLBACK)),
                                        frame_buffer, record_queue, lock)

        # UI state
        self.hue_shift = 0; self.sat_shift = 0; self.val_shift = 0
        self.night_mode = False; self.thermal_mode = False; self.alarm_enabled = True
        self.auto_record_enabled = True

        # trayectoria
        self.tray_w, self.tray_h = 320, 240
        import numpy as np
        self.trayectoria_img = np.zeros((self.tray_h, self.tray_w, 3), dtype=np.uint8)
        self.puntos = []

        self._build_ui()
        self.prev_frame = None
        self.last_saved_time = 0
        self.last_list_refresh = 0

    def _build_ui(self):
        root = self.root
        root.title("Detector modularizado")

        video_frame = ttk.Frame(root); controls_frame = ttk.Frame(root)
        video_frame.grid(row=0, column=0, padx=5, pady=5)
        controls_frame.grid(row=0, column=1, padx=5, pady=5, sticky="n")

        # etiquetas de video
        self.label_video = ttk.Label(video_frame); self.label_video.pack()
        self.label_tray = ttk.Label(video_frame); self.label_tray.pack(pady=6)

        # scrollbars
        ttk.Label(controls_frame, text="Hue shift (-90..90)").pack(anchor="w")
        self.hue_scale = ttk.Scale(controls_frame, from_=-90, to=90, orient="horizontal"); self.hue_scale.set(0); self.hue_scale.pack(fill="x")
        ttk.Label(controls_frame, text="Sat shift (-100..100)").pack(anchor="w")
        self.sat_scale = ttk.Scale(controls_frame, from_=-100, to=100, orient="horizontal"); self.sat_scale.set(0); self.sat_scale.pack(fill="x")
        ttk.Label(controls_frame, text="Val shift (-100..100)").pack(anchor="w")
        self.val_scale = ttk.Scale(controls_frame, from_=-100, to=100, orient="horizontal"); self.val_scale.set(0); self.val_scale.pack(fill="x")

        # botones principales
        self.btn_night = ttk.Button(controls_frame, text="Toggle Nocturna (N)", command=self.toggle_night); self.btn_night.pack(fill="x", pady=4)
        self.btn_thermal = ttk.Button(controls_frame, text="Toggle Termica (T)", command=self.toggle_thermal); self.btn_thermal.pack(fill="x", pady=4)
        self.btn_record = ttk.Button(controls_frame, text="Iniciar Grabación Manual", command=self.manual_toggle); self.btn_record.pack(fill="x", pady=4)
        self.btn_clear = ttk.Button(controls_frame, text="Limpiar Trayectoria", command=self.clear_tray); self.btn_clear.pack(fill="x", pady=4)
        self.btn_toggle_alarm = ttk.Button(controls_frame, text="Toggle Alarma (S)", command=self.toggle_alarm); self.btn_toggle_alarm.pack(fill="x", pady=4)

        # lista
        ttk.Label(controls_frame, text="Evidencias:").pack(anchor="w", pady=(8,0))
        self.listbox = tk.Listbox(controls_frame, height=10, width=40); self.listbox.pack(side="left", fill="both")
        self.scroll = ttk.Scrollbar(controls_frame, orient="vertical", command=self.listbox.yview); self.scroll.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=self.scroll.set)
        # botones reproductor
        self.btn_play = ttk.Button(controls_frame, text="Abrir", command=self.play_selected); self.btn_play.pack(fill="x", pady=2)
        self.btn_refresh = ttk.Button(controls_frame, text="Refresh", command=self.refresh_list); self.btn_refresh.pack(fill="x", pady=2)
        self.btn_delete = ttk.Button(controls_frame, text="Borrar", command=self.delete_selected); self.btn_delete.pack(fill="x", pady=2)
        self.btn_delete_all = ttk.Button(controls_frame, text="Borrar todo (Evidencias)", command=lambda: self.delete_all_evidences())
        self.btn_delete_all.pack(fill="x", pady=2)


        # estados
        self.status_motion = ttk.Label(controls_frame, text="Movimiento: NO"); self.status_motion.pack(pady=(8,2))
        self.status_record = ttk.Label(controls_frame, text="Grabando: NO"); self.status_record.pack(pady=2)
        self.status_modes = ttk.Label(controls_frame, text="Nocturna: OFF  Termica: OFF"); self.status_modes.pack(pady=2)

        # key bindings
        self.root.bind_all("<Key>", self._on_key)

        # listar evidencias al inicio
        self.refresh_list()

    # --- control botones ---
    def toggle_night(self):
        self.night_mode = not self.night_mode
        if self.night_mode and self.thermal_mode:
            self.thermal_mode = False
        self._update_status_modes()

    def toggle_thermal(self):
        self.thermal_mode = not self.thermal_mode
        if self.thermal_mode and self.night_mode:
            self.night_mode = False
        self._update_status_modes()

    def toggle_alarm(self):
        self.alarm_enabled = not self.alarm_enabled

    def manual_toggle(self):
        if not self.recorder.is_recording() and not self.recorder.manual_recording_flag:
            # iniciar manual
            self.recorder.start_manual_recording()
            self.btn_record.config(text="Detener Grabación Manual")
        else:
            # parar manual (si hay manual_recording)
            self.recorder.stop_manual_recording()
            self.btn_record.config(text="Iniciar Grabación Manual")

    def clear_tray(self):
        import numpy as np
        self.trayectoria_img = np.zeros((self.tray_h, self.tray_w, 3), dtype=np.uint8)
        self.puntos = []

    def _update_status_modes(self):
        self.status_modes.config(text=f"Nocturna: {'ON' if self.night_mode else 'OFF'}  Termica: {'ON' if self.thermal_mode else 'OFF'}")

    def _on_key(self, event):
        k = event.keysym.lower()
        if k == 'n':
            self.toggle_night()
        elif k == 't':
            self.toggle_thermal()
        elif k == 's':
            self.toggle_alarm()
        elif k == 'q':
            # cierre seguro
            self.shutdown()


    # --- lista evidencias ---
    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        files = list_evid_files(self.cfg.EVID_DIR)
        for f in files:
            self.listbox.insert(tk.END, f)

    def delete_selected(self):
        sel = self.listbox.curselection()
        if not sel: return
        filename = self.listbox.get(sel[0])
        path = os.path.join(self.cfg.EVID_DIR, filename)
        if messagebox.askyesno("Borrar", f"Borrar {filename}?"):
            try:
                os.remove(path)
                self.refresh_list()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def delete_all_evidences(self):
        """Borra todos los archivos de la carpeta de evidencias (confirmación)."""
        files = list(self.listbox.get(0, tk.END))
        if not files:
            messagebox.showinfo("Borrar todo", "No hay archivos para borrar.")
            return
        if not messagebox.askyesno("Borrar todo", f"¿Borrar {len(files)} archivos en '{self.cfg.EVID_DIR}'?"):
            return
        errors = []
        for fname in files:
            path = os.path.join(self.cfg.EVID_DIR, fname)
            try:
                os.remove(path)
            except Exception as e:
                errors.append(f"{fname}: {e}")
        self.refresh_list()
        if errors:
            messagebox.showwarning("Borrar todo", "Algunos archivos no pudieron eliminarse:\n" + "\n".join(errors))


    def play_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Play", "Selecciona un archivo")
            return
        files = list(self.listbox.get(0, tk.END))
        idx = sel[0]
        # Aquí usamos MediaPlayer del módulo player.py (importado arriba)
        MediaPlayer(self.root, self.cfg.EVID_DIR, files, idx)

    # --- main loop (llamado desde main) ---
    def loop_iteration(self):
        # lee frame
        ret, frame = self.cap.read()
        if not ret:
            return None
        # HSV scrollbars
        self.hue_shift = int(self.hue_scale.get())
        self.sat_shift = int(self.sat_scale.get())
        self.val_shift = int(self.val_scale.get())
        frame = apply_hsv_adjust(frame, self.hue_shift, self.sat_shift, self.val_shift)

        # buffer
        self.frame_buffer.append(frame.copy())

        # procesar movimiento y trayectoria
        info = detect_motion_and_update(frame, self.prev_frame, self.backSub, self.cfg.MIN_AREA,
                                        trayectoria_img=self.trayectoria_img, puntos=self.puntos,
                                        tray_w=self.tray_w, tray_h=self.tray_h)
        vis_frame = info['frame_out']
        mov = info['mov']

        # caras
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        caras = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30,30))
        for (fx,fy,fw,fh) in caras:
            cv2.rectangle(vis_frame, (fx,fy), (fx+fw, fy+fh), (255,0,0), 2)
            # guardar recorte de cara
            ts = timestamp()
            cv2.imwrite(os.path.join(self.cfg.EVID_DIR, f"cara_{ts}.jpg"), frame[fy:fy+fh, fx:fx+fw])

        # movimiento confirmado -> guardar y grabar
        if mov:
            nowt = time.time()
            if nowt - self.last_saved_time >= self.cfg.TIMELAPSE:
                cv2.imwrite(os.path.join(self.cfg.EVID_DIR, f"intruso_{timestamp()}.jpg"), frame)
                self.last_saved_time = nowt
                if self.alarm_enabled and os.path.exists(self.cfg.SONIDO_ALARMA):
                    play_sound_nonblocking(self.cfg.SONIDO_ALARMA)
            if self.auto_record_enabled and not self.recorder.is_recording():
                self.recorder.start_auto_recording_with_buffer(duration=self.cfg.VIDEO_DURATION)

        # aplicar modos noche/térmico 
        lum = calcular_luminosidad(frame)
        if self.thermal_mode:
            vis = aplicar_vision_termica(vis_frame)
        elif self.night_mode or lum < self.cfg.UMBRAL_LUZ:
            vis = aplicar_vision_nocturna_verde(vis_frame)
        else:
            vis = vis_frame

        # añadir a la cola de grabación si está grabando
        if self.recorder.is_recording():
            if len(self.record_queue) < 500:
                self.record_queue.append(vis.copy())

        # actualizar displays
        self.status_motion.config(text=f"Movimiento: {'SI' if mov else 'NO'}")
        self.status_record.config(text=f"Grabando: {'SI' if self.recorder.is_recording() else 'NO'}")
        self._update_status_modes()

        # preparar imagen para Tkinter
        vis_rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)
        imgtk = ImageTk.PhotoImage(Image.fromarray(vis_rgb))
        self.label_video.imgtk = imgtk
        self.label_video.config(image=imgtk)

        # trayectoria
        tray_rgb = cv2.cvtColor(self.trayectoria_img, cv2.COLOR_BGR2RGB)
        tray_pil = Image.fromarray(tray_rgb).resize((320,240))
        traytk = ImageTk.PhotoImage(tray_pil)
        self.label_tray.imgtk = traytk
        self.label_tray.config(image=traytk)

        # actualizar prev
        self.prev_frame = frame.copy()

    def shutdown(self):
        """Apagado seguro: señalizamos a recorders, esperamos, liberamos cámara y cerramos GUI."""
        # deshabilitar botones para evitar interacciones
        try:
            self.btn_record.config(state='disabled')
            self.btn_night.config(state='disabled')
            self.btn_thermal.config(state='disabled')
            self.btn_delete.config(state='disabled')
            if hasattr(self, 'btn_delete_all'):
                self.btn_delete_all.config(state='disabled')
        except Exception:
            pass

        # lanzar hilo que hace la parada para no bloquear la GUI
        threading.Thread(target=self._shutdown_thread, daemon=True).start()

    def _shutdown_thread(self):
        # 1) desactivar acciones
        self.auto_record_enabled = False
        self.alarm_enabled = False

        # 2) pedir al recorder que pare y esperar hasta 6s
        try:
            self.recorder.stop_all_and_wait(timeout=6.0)
        except Exception as e:
            print("Error al detener recorder:", e)

        # 3) vaciar cola para evitar bloqueos posteriores
        try:
            with self.lock:
                self.record_queue.clear()
        except Exception:
            pass

        # 4) detener audio
        try:
            import pygame
            pygame.mixer.stop()
        except Exception:
            pass

        # 5) liberar cámara 
        try:
            if hasattr(self, 'cap') and self.cap is not None:
                self.cap.release()
                self.cap = None
        except Exception as e:
            print("Error liberando cámara:", e)

        # 6) destruir ventanas OpenCV
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

        # 7) cerrar ventana Tkinter desde hilo principal
        try:
            self.root.after(0, lambda: (self.root.quit(), self.root.destroy()))
        except Exception:
            pass
