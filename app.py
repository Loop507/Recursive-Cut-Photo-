import streamlit as st
import numpy as np
import cv2
from PIL import Image
from moviepy.editor import ImageSequenceClip, AudioFileClip
import tempfile
import random
import os
import gc

st.set_page_config(page_title="Recursive Cut Pro - Loop507", layout="wide")

# --- LOGICA KEYFRAMES ---
def get_dynamic_val(current_f, total_f, fps, start_t, start_v, peak_t, peak_v, end_v):
    curr_sec = current_f / fps
    total_sec = total_f / fps
    
    if curr_sec <= start_t:
        return start_v / 100
    elif curr_sec <= peak_t:
        t = (curr_sec - start_t) / (peak_t - start_t)
        return (start_v + t * (peak_v - start_v)) / 100
    else:
        t = (curr_sec - peak_t) / (total_sec - peak_t)
        return (peak_v + t * (end_v - peak_v)) / 100

# --- ENGINE DI RENDERING ---
def generate_master(imgs, up_aud, orientation, strand_val, is_random, max_limit, use_base, k_params, final_opacity):
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

    # Inizializzazione offset (se use_base è False, mixiamo subito)
    offsets = [random.uniform(0, len(imgs)) if not use_base else 0.0 for _ in range(len(boundaries))]
    final_frames = []

    for f in range(total_f):
        # 1. Calcolo Intensità e Opacità dinamica
        val = get_dynamic_val(f, total_f, fps, k_params['st'], k_params['sv'], k_params['pt'], k_params['pv'], k_params['ev'])
        
        # L'opacità della foto base "Top" sale linearmente verso la fine (solo dopo il picco)
        curr_sec = f / fps
        top_alpha = 0.0
        if curr_sec > k_params['pt']:
            t_fade = (curr_sec - k_params['pt']) / (max_limit - k_params['pt'])
            top_alpha = t_fade * (final_opacity / 100)

        # 2. Creazione Tritato
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        for s, (start, end) in enumerate(boundaries):
            offsets[s] += 0.01 + (val * 0.6)
            idx = int(offsets[s] % len(imgs))
            nxt = (idx + 1) % len(imgs)
            alpha = offsets[s] % 1
            
            if orientation == "Orizzontale":
                strip = cv2.addWeighted(imgs[idx][start:end, :], 1-alpha, imgs[nxt][start:end, :], alpha, 0)
                frame[start:end, :] = strip
            else:
                strip = cv2.addWeighted(imgs[idx][:, start:end], 1-alpha, imgs[nxt][:, start:end], alpha, 0)
                frame[:, start:end] = strip
        
        # 3. Applicazione Foto Top (Ricomposizione Finale)
        if top_alpha > 0:
            frame = cv2.addWeighted(frame, 1 - top_alpha, imgs[0], top_alpha, 0)
            
        final_frames.append(frame)

    # 4. Export Video
    video_clip = ImageSequenceClip(final_frames, fps=fps)
    if up_aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as t_aud:
            t_aud.write(up_aud.read())
            aud_path = t_aud.name
        audio = AudioFileClip(aud_path).subclip(0, min(AudioFileClip(aud_path).duration, max_limit))
        video_clip = video_clip.set_audio(audio)
    
    out_path = tempfile.mktemp(suffix=".mp4")
    video_clip.write_videofile(out_path, codec="libx264", audio_codec="aac" if up_aud else None, fps=fps, bitrate="2500k", logger=None)
    if up_aud: os.remove(aud_path)
    return out_path

# --- INTERFACCIA ---
st.title("Recursive Cut Photo Pro 🚀")
st.write("by Loop507")

with st.expander("📏 MISURE & KEYFRAMES (Timeline AE Style)", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        s_t = st.number_input("Start Tempo (sec)", 0.0, 60.0, 3.0)
        s_v = st.slider("Start Potenza %", 0, 100, 5)
    with c2:
        p_t = st.number_input("Picco Tempo (sec)", 0.0, 60.0, 5.0)
        p_v = st.slider("Picco Potenza %", 0, 100, 100)
    with c3:
        e_v = st.slider("End Potenza %", 0, 100, 3)
        final_op = st.slider("Ricomposizione Finale (Opacità %)", 0, 100, 100)

col_left, col_right = st.columns(2)
with col_left:
    up_img = st.file_uploader("Immagini", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    up_aud = st.file_uploader("Audio", type=["mp3", "wav"])
    orientation = st.radio("Direzione Taglio", ["Orizzontale", "Verticale"])

with col_right:
    strand_val = st.slider("Grandezza Linee (px)", 1, 400, 60)
    max_limit = st.number_input("Durata Video (sec)", 1, 60, 10)
    is_random = st.checkbox("Chaos Mode (Strisce Random)", value=True)
    use_base = st.checkbox("Usa Sfondo Fisso all'Inizio", value=False)

if st.button("🎬 GENERA MASTER") and up_img:
    if len(up_img) < 2:
        st.error("Carica almeno 2 immagini!")
    else:
        k_params = {'st': s_t, 'sv': s_v, 'pt': p_t, 'pv': p_v, 'ev': e_v}
        with st.spinner("Rendering Evolution..."):
            imgs_array = [np.array(Image.open(f).convert("RGB").resize((1280, 720), Image.Resampling.NEAREST)) for f in up_img[:20]]
            path = generate_master(imgs_array, up_aud, orientation, strand_val, is_random, max_limit, use_base, k_params, final_op)
            st.video(path)
            with open(path, "rb") as f:
                st.download_button("💾 SCARICA MASTER", f, file_name="loop507_master.mp4")
            gc.collect()
