import streamlit as st
import numpy as np
import cv2
from PIL import Image
from moviepy.editor import ImageSequenceClip, AudioFileClip
import tempfile
import random
import os

# --- IDENTITÀ VISIVA Loop507 ---
st.set_page_config(page_title="Recursive Cut Photo by Loop507", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 42px; font-weight: bold; margin-bottom: -5px; color: #ffffff; }
    .sub-title { font-size: 16px; color: #888; margin-bottom: 30px; letter-spacing: 1px; }
    </style>
    <div>
        <span class="main-title">Recursive Cut Photo</span><br>
        <span class="sub-title">by Loop507</span>
    </div>
    """, unsafe_allow_html=True)

# --- ANALISI AUDIO REALE (PEAK DETECTION) ---
def get_real_audio_sync(audio_path, fps, max_dur):
    audio = AudioFileClip(audio_path)
    duration = min(audio.duration, max_dur)
    audio = audio.subclip(0, duration)
    n_frames = int(duration * fps)
    
    sync_data = []
    for i in range(n_frames):
        t = i / fps
        try:
            # Analisi volume picco in una finestra di 0.04s
            chunk = audio.subclip(t, min(t + 0.04, duration))
            vol = chunk.max_volume()
            sync_data.append(vol)
        except:
            sync_data.append(0)
    
    max_v = max(sync_data) if sync_data and max(sync_data) > 0 else 1
    return [v / max_v for v in sync_data], duration, audio

# --- MOTORE VISIVO RECURSIVE / KINETIC CON RANDOM STRANDS ---
def visual_engine(images, n_frames, intensity, sync_data, strand_size, orientation, mode, is_random):
    h, w, _ = images[0].shape
    frames = []
    dim = h if orientation == "Orizzontale" else w
    
    # --- LOGICA GRANDEZZA LINEE ---
    strand_boundaries = []
    curr = 0
    if is_random:
        # Chaos Mode: larghezza strisce imprevedibile
        while curr < dim:
            s_w = random.randint(max(1, strand_size // 2), strand_size * 2)
            if curr + s_w > dim: s_w = dim - curr
            strand_boundaries.append((curr, curr + s_w))
            curr += s_w
    else:
        # Larghezza fissa classica
        n_strands = max(1, dim // strand_size)
        actual_s_size = dim // n_strands
        for s in range(n_strands):
            start = s * actual_s_size
            end = (s + 1) * actual_s_size if s < n_strands - 1 else dim
            strand_boundaries.append((start, end))

    if mode == "Kinetic (Flusso)":
        n_strands = len(strand_boundaries)
        offsets = [random.uniform(0, len(images)) for _ in range(n_strands)]
        base_speeds = [random.uniform(0.005, 0.02) for _ in range(n_strands)]

        for f in range(n_frames):
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            vol_boost = sync_data[f] if f < len(sync_data) else 0
            
            for s, (start, end) in enumerate(strand_boundaries):
                # Il volume dell'audio spinge la velocità di scorrimento
                offsets[s] += base_speeds[s] + (vol_boost * (intensity / 80))
                idx = int(offsets[s] % len(images))
                nxt = (idx + 1) % len(images)
                alpha = offsets[s] % 1
                
                if orientation == "Orizzontale":
                    strip = cv2.addWeighted(images[idx][start:end, :], 1-alpha, images[nxt][start:end, :], alpha, 0)
                    frame[start:end, :] = strip
                else:
                    strip = cv2.addWeighted(images[idx][:, start:end], 1-alpha, images[nxt][:, start:end], alpha, 0)
                    frame[:, start:end] = strip
            frames.append(frame)
            
    else: # Mode: Recursive (Stutter/Cut)
        curr_i = 0
        threshold = max(0.05, 1.0 - (intensity / 100)) 
        for f in range(n_frames):
            # Cambia immagine solo se il picco audio supera la soglia di intensità
            if f < len(sync_data) and sync_data[f] > threshold:
                curr_i = (curr_i + 1) % len(images)
            frames.append(images[curr_i])
            
    return frames

# --- INTERFACCIA ---
col_files, col_cfg = st.columns([1, 1])

with col_files:
    st.subheader("📁 Input")
    up_img = st.file_uploader("Carica Immagini (Artefatti)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    up_aud = st.file_uploader("Carica Audio (Guida)", type=["mp3", "wav"])
    format_out = st.selectbox("Formato Output", ["16:9 (Orizzontale)", "9:16 (Verticale)", "1:1 (Quadrato)"])

with col_cfg:
    st.subheader("⚙️ Parametri")
    mode = st.radio("Motore Algoritmo", ["Kinetic (Flusso)", "Recursive (Stutter)"])
    strand_val = st.slider("Grandezza Linee Base (Pixel)", 1, 500, 40)
    is_random = st.checkbox("Chaos Mode (Linee Random)", value=False)
    intensity = st.slider("Intensità Glitch / Sensibilità Beat", 1, 100, 40)
    
    c1, c2 = st.columns(2)
    with c1:
        orientation = st.radio("Direzione Strisce", ["Orizzontale", "Verticale"])
    with c2:
        max_limit = st.number_input("Limite Max Durata (sec)", 1, 600, 60)

# --- GENERAZIONE ---
if st.button("🎬 GENERA MASTER 720p") and up_img:
    if len(up_img) < 2:
        st.error("Servono almeno 2 immagini.")
    else:
        with st.spinner("Masticando i dati per Loop507..."):
            fps = 24
            res_map = {"16:9 (Orizzontale)": (1280, 720), "9:16 (Verticale)": (720, 1280), "1:1 (Quadrato)": (720, 720)}
            target_res = res_map[format_out]
            
            imgs = [np.array(Image.open(f).convert("RGB").resize(target_res, Image.Resampling.NEAREST)) for f in up_img]
            
            audio_clip = None
            aud_path = None
            if up_aud:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as t_aud:
                    t_aud.write(up_aud.read())
                    aud_path = t_aud.name
                sync_data, final_dur, audio_clip = get_real_audio_sync(aud_path, fps, max_limit)
            else:
                final_dur = max_limit
                # Senza audio simuliamo un battito casuale basato sull'intensità
                sync_data = [1.0 if random.random() > (1.0 - intensity/100) else 0.2 for _ in range(int(final_dur * fps))]

            video_frames = visual_engine(imgs, int(final_dur * fps), intensity, sync_data, strand_val, orientation, mode, is_random)
            
            v_clip = ImageSequenceClip(video_frames, fps=fps)
            if audio_clip:
                v_clip = v_clip.set_audio(audio_clip)
            
            out_file = tempfile.mktemp(suffix=".mp4")
            v_clip.write_videofile(out_file, codec="libx264", audio_codec="aac" if audio_clip else None, fps=fps, bitrate="3500k", logger=None)

            st.video(out_file)
            with open(out_file, "rb") as f:
                st.download_button("💾 SCARICA ARTEFATTO", f, file_name="RecursiveCut_Loop507.mp4")

            if up_aud:
                os.remove(aud_path)
