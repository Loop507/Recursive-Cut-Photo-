import streamlit as st
import numpy as np
import cv2
from PIL import Image
import tempfile
import random
import os
import gc

# --- BRANDING ---
st.set_page_config(page_title="Recursive Cut Photo by Loop507", layout="wide")
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: white; }
    .sub-title { font-size: 14px; color: #888; }
    </style>
    <div><span class="main-title">Recursive Cut Photo</span><br><span class="sub-title">by Loop507</span></div>
    """, unsafe_allow_html=True)

# --- ENGINE DI RENDERING FRAME-BY-FRAME ---
def process_video():
    # Pulizia preventiva
    gc.collect()
    
    # 1. Setup Parametri
    w, h = 1280, 720
    fps = 24
    total_f = int(max_limit * fps)
    
    # 2. Caricamento Immagini (max 30 per sicurezza RAM)
    imgs = []
    for f in up_img[:30]:
        img = Image.open(f).convert("RGB").resize((w, h), Image.Resampling.NEAREST)
        imgs.append(np.array(img))
        del img
    
    # 3. Preparazione File Scrittura
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    # Usiamo 'avc1' o 'mp4v' per massima compatibilità
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(tmp.name, fourcc, fps, (w, h))

    # 4. Logica di Taglio
    dim_to_cut = h if orientation == "Orizzontale" else w
    boundaries = []
    curr = 0
    while curr < dim_to_cut:
        s_w = random.randint(max(1, strand_val//2), strand_val*2) if is_random else strand_val
        if curr + s_w > dim_to_cut: s_w = dim_to_cut - curr
        boundaries.append((curr, curr + s_w))
        curr += s_w

    offsets = [random.uniform(0, len(imgs)) for _ in range(len(boundaries))]
    
    prog = st.progress(0)
    for f in range(total_f):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        if mode == "Kinetic (Flusso)":
            for s, (start, end) in enumerate(boundaries):
                # Velocità basata sull'intensità
                offsets[s] += 0.01 + (intensity / 500)
                idx = int(offsets[s] % len(imgs))
                nxt = (idx + 1) % len(imgs)
                alpha = offsets[s] % 1
                
                if orientation == "Orizzontale":
                    # Tagli orizzontali (strisce che scorrono lungo l'altezza)
                    strip = cv2.addWeighted(imgs[idx][start:end, :], 1-alpha, imgs[nxt][start:end, :], alpha, 0)
                    frame[start:end, :] = strip
                else:
                    # Tagli verticali (strisce che scorrono lungo la larghezza)
                    strip = cv2.addWeighted(imgs[idx][:, start:end], 1-alpha, imgs[nxt][:, start:end], alpha, 0)
                    frame[:, start:end] = strip
        else:
            # Recursive Stutter classico
            idx = int((f * intensity / 20) % len(imgs))
            frame = imgs[idx]

        # Scrittura Frame (RGB -> BGR per OpenCV)
        out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        
        if f % 12 == 0: prog.progress(f / total_f)

    out.release()
    return tmp.name

# --- INTERFACCIA UTENTE ---
col_in, col_set = st.columns([1, 1])

with col_in:
    up_img = st.file_uploader("Carica Immagini", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    mode = st.radio("Motore Visivo", ["Kinetic (Flusso)", "Recursive (Stutter)"])
    orientation = st.radio("Orientamento Taglio", ["Orizzontale", "Verticale"])

with col_set:
    strand_val = st.slider("Grandezza Linee (px)", 1, 500, 40)
    intensity = st.slider("Intensità Movimento", 1, 100, 40)
    is_random = st.checkbox("Chaos Mode (Strisce Random)")
    max_limit = st.number_input("Durata Video (sec)", 1, 60, 10)

if st.button("🎬 GENERA ARTEFATTO") and up_img:
    if len(up_img) < 2:
        st.error("Carica almeno 2 immagini!")
    else:
        with st.spinner("Rendering..."):
            path = process_video()
            st.success("Generazione Completata!")
            
            # Anteprima piccola (colonna centrale)
            _, mid, _ = st.columns([1, 2, 1])
            with mid:
                st.video(path) # Streamlit gestisce il ridimensionamento automatico
            
            with open(path, "rb") as f:
                st.download_button("💾 SCARICA MASTER", f, file_name="loop507_output.mp4")
            
            # Cleanup
            gc.collect()
