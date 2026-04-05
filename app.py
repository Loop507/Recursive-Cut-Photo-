import streamlit as st
import numpy as np
import cv2
from PIL import Image
import tempfile
import random
import os
import gc

st.set_page_config(page_title="Recursive Cut Photo by Loop507", layout="wide")

# --- INTERFACCIA ---
st.title("Recursive Cut Photo")
st.caption("by Loop507 | Optimized Iron Version")

up_img = st.file_uploader("Carica Immagini", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
up_aud = st.file_uploader("Carica Audio (opzionale)", type=["mp3", "wav"])

col1, col2 = st.columns(2)
with col1:
    mode = st.radio("Motore", ["Kinetic (Flusso)", "Recursive (Stutter)"])
    strand_val = st.slider("Grandezza Linee", 1, 500, 40)
    is_random = st.checkbox("Chaos Mode (Random Lines)")
with col2:
    intensity = st.slider("Intensità", 1, 100, 40)
    max_limit = st.number_input("Durata Max (sec)", 1, 60, 15)

if st.button("🎬 GENERA VIDEO") and up_img:
    if len(up_img) < 2:
        st.error("Carica almeno 2 immagini.")
    else:
        with st.spinner("Rendering a basso consumo di RAM..."):
            # 1. Setup Dimensioni (720p per sicurezza)
            w, h = 1280, 720
            fps = 24
            total_frames = int(max_limit * fps)
            
            # 2. Caricamento Immagini (Ridimensionate subito per risparmiare RAM)
            imgs = []
            for f in up_img[:40]: # Limite a 40 immagini
                img = Image.open(f).convert("RGB").resize((w, h), Image.Resampling.NEAREST)
                imgs.append(np.array(img))
                del img
            gc.collect()

            # 3. Preparazione File Video (Scrittura diretta su disco)
            tmp_video = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Codec standard
            out_video = cv2.VideoWriter(tmp_video.name, fourcc, fps, (w, h))

            # 4. Engine di Rendering (Frame per Frame)
            # Creiamo una finta sync se non c'è audio per non appesantire
            sync_data = [random.random() for _ in range(total_frames)]
            
            # Grid Logic
            boundaries = []
            curr = 0
            while curr < (h if mode == "Kinetic (Flusso)" else h):
                s_w = random.randint(max(1, strand_val//2), strand_val*2) if is_random else strand_val
                if curr + s_w > h: s_w = h - curr
                boundaries.append((curr, curr + s_w))
                curr += s_w

            offsets = [random.uniform(0, len(imgs)) for _ in range(len(boundaries))]
            
            # Loop di rendering
            prog_bar = st.progress(0)
            for f in range(total_frames):
                if mode == "Kinetic (Flusso)":
                    frame = np.zeros((h, w, 3), dtype=np.uint8)
                    for s, (start, end) in enumerate(boundaries):
                        offsets[s] += 0.01 + (sync_data[f] * (intensity/100))
                        idx = int(offsets[s] % len(imgs))
                        nxt = (idx + 1) % len(imgs)
                        alpha = offsets[s] % 1
                        # Mixing
                        strip = cv2.addWeighted(imgs[idx][start:end, :], 1-alpha, imgs[nxt][start:end, :], alpha, 0)
                        frame[start:end, :] = strip
                else: # Recursive
                    idx = int((f * intensity / 10) % len(imgs))
                    frame = imgs[idx]

                # Converti RGB in BGR per OpenCV e scrivi su disco
                out_video.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                
                if f % 24 == 0: # Aggiorna progresso ogni secondo di video
                    prog_bar.progress(f / total_frames)
            
            out_video.release()
            
            # 5. Output
            st.success("Video generato!")
            with open(tmp_video.name, "rb") as v_file:
                st.download_button("💾 SCARICA VIDEO", v_file, file_name="loop507_artefatto.mp4")
            
            # Pulizia
            os.unlink(tmp_video.name)
            del imgs
            gc.collect()
