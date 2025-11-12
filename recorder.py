# recorder.py 
# Grabación de video (auto y manual) con buffer previo
import time
import threading
import os
import cv2
from collections import deque

class RecorderManager:
    def __init__(self, evid_dir, fps, frame_buffer: deque, record_queue: deque, lock: threading.Lock):
        self.evid_dir = evid_dir
        self.fps = fps
        self.frame_buffer = frame_buffer
        self.record_queue = record_queue
        self.lock = lock

        self.auto_thread = None
        self.auto_stop_event = None
        self.manual_thread = None
        self.manual_stop_event = None

        self.recording_flag = False
        self.manual_recording_flag = False

    def _make_writer(self, path, frame_shape):
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        h, w = frame_shape[:2]
        # nota: OpenCV quiere (width, height)
        return cv2.VideoWriter(path, fourcc, max(1, int(self.fps)), (w, h))

    # ---------- AUTO recording ----------
    def start_auto_recording_with_buffer(self, duration=6):
        """Inicia grabación automática: buffer previo + duration segundos posteriores."""
        if self.auto_thread and self.auto_thread.is_alive():
            return  # ya grabando auto

        buf_copy = [f.copy() for f in list(self.frame_buffer)]
        stop_event = threading.Event()
        self.auto_stop_event = stop_event
        t = threading.Thread(target=self._auto_rec_thread, args=(buf_copy, duration, stop_event))
        t.start()
        self.auto_thread = t

    def _auto_rec_thread(self, buf_copy, duration_sec, stop_event: threading.Event):
        self.recording_flag = True
        timestamp = time.strftime("%d%m%Y_%H%M%S")
        filename = os.path.join(self.evid_dir, f"intruso_{timestamp}.avi")
        if len(buf_copy) > 0:
            frame_shape = buf_copy[0].shape
        else:
            # no buffer -> intentar sacar tamaño de la cámara (si no disponible, abandona)
            raise RuntimeError("Auto-record buffer vacío.")
        writer = self._make_writer(filename, frame_shape)

        try:
            # escribir buffer previo
            for f in buf_copy:
                writer.write(f)

            end_time = time.time() + duration_sec
            while time.time() < end_time and (not stop_event.is_set()):
                frame_to_write = None
                try:
                    frame_to_write = self.record_queue.popleft()
                except IndexError:
                    # sin frames, esperar un poco y volver a intentar
                    time.sleep(0.01)
                    continue
                if frame_to_write is not None:
                    writer.write(frame_to_write)
        finally:
            writer.release()
            self.recording_flag = False
            print("[recorder] Auto-record guardado:", filename)

    # ---------- MANUAL recording (toggle) ----------
    def start_manual_recording(self):
        """Inicia grabación manual (se detiene con stop_manual_recording o stop_all)."""
        if self.manual_thread and self.manual_thread.is_alive():
            return  # ya está grabando manual
        buf_copy = [f.copy() for f in list(self.frame_buffer)]
        stop_event = threading.Event()
        self.manual_stop_event = stop_event
        t = threading.Thread(target=self._manual_rec_thread, args=(buf_copy, stop_event))
        t.start()
        self.manual_thread = t

    def _manual_rec_thread(self, buf_copy, stop_event: threading.Event):
        self.manual_recording_flag = True
        timestamp = time.strftime("%d%m%Y_%H%M%S")
        filename = os.path.join(self.evid_dir, f"intruso_manual_{timestamp}.avi")
        if len(buf_copy) > 0:
            frame_shape = buf_copy[0].shape
        else:
            raise RuntimeError("Manual-record buffer vacío.")
        writer = self._make_writer(filename, frame_shape)

        try:
            for f in buf_copy:
                writer.write(f)

            print("[recorder] Grabando manual:", filename)
            # continuar hasta que stop_event se ponga a True
            while (not stop_event.is_set()) or len(self.record_queue) > 0:
                frame_to_write = None
                try:
                    frame_to_write = self.record_queue.popleft()
                except IndexError:
                    time.sleep(0.01)
                    continue
                if frame_to_write is not None:
                    writer.write(frame_to_write)
        finally:
            writer.release()
            self.manual_recording_flag = False
            print("[recorder] Finalizada grabación manual:", filename)

    def stop_manual_recording(self):
        if self.manual_stop_event:
            self.manual_stop_event.set()

    # ---------- STOP / JOIN ----------
    def stop_all_and_wait(self, timeout=5.0):
        """Señala a ambos hilos que paren y espera hasta `timeout` segundos en total."""
        start = time.time()
        # señalizar auto
        if self.auto_stop_event:
            self.auto_stop_event.set()
        if self.manual_stop_event:
            self.manual_stop_event.set()

        # luego hacer join con timeout restante
        # join auto
        if self.auto_thread:
            remaining = max(0.0, timeout - (time.time() - start))
            self.auto_thread.join(remaining)

        # join manual
        if self.manual_thread:
            remaining = max(0.0, timeout - (time.time() - start))
            self.manual_thread.join(remaining)

        # por seguridad resetar flags
        self.recording_flag = False
        self.manual_recording_flag = False
        # limpiar events
        self.auto_stop_event = None
        self.manual_stop_event = None

    def is_recording(self) -> bool:
        """Devuelve True si hay alguna grabación (auto o manual) en curso."""
        # hilos vivos o flags
        auto_alive = self.auto_thread is not None and self.auto_thread.is_alive()
        manual_alive = self.manual_thread is not None and self.manual_thread.is_alive()
        return bool(auto_alive or manual_alive or self.recording_flag or self.manual_recording_flag)

