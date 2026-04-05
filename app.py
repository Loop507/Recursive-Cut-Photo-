import streamlit as st
import numpy as np
import cv2
from PIL import Image
import imageio
from moviepy.editor import ImageSequenceClip, AudioFileClip
import tempfile
import random
import os

# --- CONFIGURAZIONE IDENTITÀ ---
st.set_page_config(page_title="Recursive Cut Photo by Loop507", layout="wide")

# CSS per gestire le dimensioni del titolo come richiesto
st.markdown("""
    <style>
    .main-title { font-size: 42px; font-weight: bold; margin-bottom: -10px; }
    .sub-title { font-size: 18px; color: #888; margin-bottom: 30px; }
    </style>
    <div>
        <span class="main-title">Recursive Cut Photo</span><br>
        <span class="sub-title">by Loop507</span>
    </div>
    """, unsafe_allow_html=True)

# --- LOGICA DI SINCRONIZZAZIONE ---
def get_sync_data(audio_clip, fps, duration, intensity, mode):
    n_frames = int(duration * fps)
    if audio_clip:
        # Reattività Audio: picchi casuali basati sul volume (simulato)
        return [random.uniform(1.0, 1.0 + (intensity/40)) if random.random() > 0.94 else 1.0 for _ in range(n_frames)]
    else:
        # Flusso Silenzioso: ritmo costante o casuale
        if mode == "Kinetic (Flusso)":
            return [1.0 for _ in range(n_frames)]
        else:
            return [1.5 if random.random() > (1.0 - (intensity/250)) else 1.0 for _ in range(n_frames)]

# --- MOTORE VISIVO RECURSIVE ---
def visual_engine(images, n_frames, intensity, sync_data, strand_size, orientation, mode):
    h, w, _ = images[0].shape
    frames = []
    
    if mode == "Kinetic (Flusso)":
        dim = h if orientation == "Orizzontale" else w
        n_strands = max(4, dim // strand_size)
        s_size = dim // n_strands
        offsets = [random.uniform(0, len(images)) for _ in range(n_strands)]
        speeds = [random.uniform(0.008, 0.025) for _ in range(n_strands)]

        for f in range(n_frames):
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            boost = sync_data[f] if f < len(sync_data) else 1.0
            
            for s in range(n_strands):
                offsets[s] += speeds[s] * boost * (intensity / 20)
                idx = int(offsets[s] % len(images))
                nxt = (idx + 1) % len(images)
                alpha = offsets[s] % 1
                
                start, end = s*s_size, (s+1)*s_size if s < n_strands-1 else dim
                
                if orientation == "Orizzontale":
                    strip = cv2.addWeighted(images[idx][start:end, :], 1-alpha, images[nxt][start:end, :], alpha, 0)
                    frame[start:end, :] = strip
                else:
                    strip = cv2.addWeighted(images[idx][:, start:end], 1-alpha, images[nxt][:, start:end], alpha, 0)
                    frame[:, start:end] = strip
            frames.append(frame)
            
    else: # Mode: Recursive (Stutter/Cut)
        curr_i = 0
        for f in range(n_frames):
            if f < len(sync_data) and sync_data[f] > 1.25:
                curr_i = (curr_i + 1) % len(images)
            frames.append(images[curr_i])
            
    return frames

# --- INTERFACCIA ---
col_in, col_st = st.columns([1, 1])

with col_in:
    up_img = st.file_uploader("Carica Artefatti (Immagini)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    up_aud = st.file_uploader("Carica Guida Audio (Opzionale)", type=["mp3", "wav"])
    if up_aud:
        st.success("Audio Reactive Mode: ON")
    else:
        st.info("Silent Flow Mode: ON")

with col_st:
    mode = st.radio("Algoritmo di Taglio", ["Kinetic (Flusso)", "Recursive (Stutter)"])
    strand_h = st.slider("Densità Taglio (Pixel)", 2, 200, 35)
    intensity = st.slider("Intensità Collasso", 1, 100, 30)
    
    c_sub1, c_sub2 = st.columns(2)
    with c_sub1:
        orientation = st.radio("Direzione", ["Orizzontale", "Verticale"])
    with c_sub2:
        duration = st.slider("Durata (sec)", 1, 30, 10 if not up_aud else 0)

if st.button("🎬 GENERA ARTEFATTO") and up_img:
    with st.spinner("Calcolo delle matrici..."):
        fps = 24
        target_size = (1280, 720) # 720p per stabilità Streamlit
        
        # Caricamento e pre-processing
        imgs = [np.array(Image.open(f).convert("RGB").resize(target_size, Image.Resampling.NEAREST)) for f in up_img]
        
        audio_clip = None
        aud_path = None
        
        if up_aud:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as t_aud:
                t_aud.write(up_aud.read())
                aud_path = t_aud.name
            audio_clip = AudioFileClip(aud_path)
            f_duration = audio_clip.duration
        else:
            f_duration = duration

        sync_data = get_sync_data(audio_clip, fps, f_duration, intensity, mode)
        total_f = len(sync_data)

        # Rendering Frame
        video_frames = visual_engine(imgs, total_f, intensity, sync_data, strand_h, orientation, mode)

        # Export MoviePy
        v_clip = ImageSequenceClip(video_frames, fps=fps)
        if audio_clip:
            v_clip = v_clip.set_audio(audio_clip)
        
        out_v = tempfile.mktemp(suffix=".mp4")
        v_clip.write_videofile(out_v, codec="libx264", audio_codec="aac" if audio_clip else None, fps=fps, bitrate="2500k", logger=None)

        st.video(out_v)
        with open(out_v, "rb") as f:
            st.download_button("💾 SCARICA MASTER", f, file_name=f"RecursiveCut_{mode[0]}.mp4")

        # Cleanup
        if aud_path and os.path.exists(aud_path): os.remove(aud_path)
