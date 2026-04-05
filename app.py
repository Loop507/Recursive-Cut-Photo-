import streamlit as st
import numpy as np
import cv2
from PIL import Image
from moviepy.editor import ImageSequenceClip, AudioFileClip
import tempfile
import random
import os
import gc

# --- BRANDING Loop507 ---
st.set_page_config(page_title="Recursive Cut Photo by Loop507", layout="wide")
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: white; }
    .sub-title { font-size: 14px; color: #888; margin-bottom: 20px; }
    </style>
    <div><span class="main-title">Recursive Cut Photo</span><br><span class="sub-title">by Loop507</span></div>
    """, unsafe_allow_html=True)

# --- ENGINE ---
def generate_art(imgs, up_aud, mode, orientation, strand_val, intensity, is_random, max_limit):
    w, h = 1280, 720
    fps = 24
    total_f = int(max_limit * fps)
    
    dim_to_cut = h if orientation == "Orizzontale" else w
    boundaries = []
    curr = 0
    while curr < dim_to_cut:
        s_w = random.randint(max(1, strand_val//2), strand_val*2) if is_random else strand_val
        if curr + s_w > dim_to_cut: s_w = dim_to_cut - curr
        boundaries.append((curr, curr + s_w))
        curr += s_w

    offsets = [random.uniform(0, len(imgs)) for _ in range(len(boundaries))]
    final_frames = []

    for f in range(total_f):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        if mode == "Kinetic (Flusso)":
            for s, (start, end) in enumerate(boundaries):
                offsets[s] += 0.02 + (intensity / 400)
                idx = int(offsets[s] % len(imgs))
                nxt = (idx + 1) % len(imgs)
                alpha = offsets[s] % 1
                if orientation == "Orizzontale":
                    frame[start:end, :] = cv2.addWeighted(imgs[idx][start:end, :], 1-alpha, imgs[nxt][start:end, :], alpha, 0)
                else:
                    frame[:, start:end] = cv2.addWeighted(imgs[idx][:, start:end], 1-alpha, imgs[nxt][:, start:end], alpha, 0)
        else:
            idx = int((f * intensity / 20) % len(imgs))
            frame = imgs[idx]
        final_frames.append(frame)

    video_clip = ImageSequenceClip(final_frames, fps=fps)
    
    aud_path = None
    if up_aud is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as t_aud:
            t_aud.write(up_aud.read())
            aud_path = t_aud.name
        audio = AudioFileClip(aud_path)
        audio = audio.subclip(0, min(audio.duration, max_limit))
        video_clip = video_clip.set_audio(audio)
    
    out_path = tempfile.mktemp(suffix=".mp4")
    video_clip.write_videofile(out_path, codec="libx264", audio_codec="aac" if up_aud else None, fps=fps, bitrate="2500k", logger=None)
    
    if aud_path:
        os.remove(aud_path)
    return out_path

# --- INTERFACCIA ---
col1, col2 = st.columns([1, 1])

with col1:
    st.write("### 1. CARICA FILE")
    uploaded_images = st.file_uploader("Immagini (Artefatti)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    uploaded_audio = st.file_uploader("Audio (MP3/WAV)", type=["mp3", "wav"])
    st.write("---")
    orientation = st.radio("Direzione Taglio", ["Orizzontale", "Verticale"])

with col2:
    st.write("### 2. PARAMETRI")
    mode = st.radio("Motore Visivo", ["Kinetic (Flusso)", "Recursive (Stutter)"])
    strand_val = st.slider("Grandezza Linee (px)", 1, 300, 50)
    intensity = st.slider("Intensità / Velocità", 1, 100, 30)
    max_limit = st.number_input("Durata Video (sec)", 1, 30, 10)
    is_random = st.checkbox("Chaos Mode (Strisce Random)")

if st.button("🎬 GENERA MASTER") and uploaded_images:
    if len(uploaded_images) < 2:
        st.error("Carica almeno 2 immagini!")
    else:
        with st.spinner("Creando l'artefatto..."):
            # Caricamento
            imgs_array = []
            for f in uploaded_images[:20]:
                img = Image.open(f).convert("RGB").resize((1280, 720), Image.Resampling.NEAREST)
                imgs_array.append(np.array(img))
            
            # Generazione
            result_path = generate_art(imgs_array, uploaded_audio, mode, orientation, strand_val, intensity, is_random, max_limit)
            
            # Risultato e Anteprima
            st.success("Rendering completato!")
            
            # Anteprima centrata e più piccola per non pesare sulla RAM
            st.video(result_path, format="video/mp4", start_time=0)
            
            with open(result_path, "rb") as v_file:
                st.download_button("💾 SCARICA VIDEO", v_file, file_name="recursive_cut_loop507.mp4")
            
            gc.collect()
