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

def get_val(f, fps, total_s, s_t, s_v, p_t, p_v, e_v):
    curr = f / fps
    if curr <= s_t: return s_v / 100
    elif curr <= p_t:
        t = (curr - s_t) / (p_t - s_t)
        return (s_v + t * (p_v - s_v)) / 100
    else:
        t = (curr - p_t) / (total_s - p_t)
        return (p_v + t * (e_v - p_v)) / 100

def generate_master(imgs, up_aud, mode, orientation, strand_val, speed_mult, is_random, max_limit, use_base, k_params, op_params):
    w, h = 1280, 720
    fps = 24
    total_f = int(max_limit * fps)
    dim_to_cut = h if orientation == "Orizzontale" else w
    
    boundaries = []
    curr = 0
    while curr < dim_to_cut:
        s_w = random.randint(max(1, int(strand_val//2)), int(strand_val*2)) if is_random else strand_val
        if curr + s_w > dim_to_cut: s_w = dim_to_cut - curr
        boundaries.append((curr, int(curr + s_w)))
        curr += s_w

    offsets = [random.uniform(0, len(imgs)) if not use_base else 0.0 for _ in range(len(boundaries))]
    final_frames = []

    for f in range(total_f):
        curr_s = f / fps
        val = get_val(f, fps, max_limit, k_params['st'], k_params['sv'], k_params['pt'], k_params['pv'], k_params['ev'])
        
        top_alpha = 0.0
        if curr_s > op_params['start_fade']:
            t_fade = (curr_s - op_params['start_fade']) / (max_limit - op_params['start_fade'])
            top_alpha = min(1.0, t_fade * (op_params['final_v'] / 100))

        frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        if mode == "Kinetic (Flusso)":
            for s, (start, end) in enumerate(boundaries):
                offsets[s] += (0.01 + (val * 0.5)) * speed_mult
                idx, nxt, alpha = int(offsets[s]%len(imgs)), int((offsets[s]+1)%len(imgs)), offsets[s]%1
                if orientation=="Orizzontale":
                    strip = cv2.addWeighted(imgs[idx][start:end, :], 1-alpha, imgs[nxt][start:end, :], alpha, 0)
                    frame[start:end, :] = strip
                else:
                    strip = cv2.addWeighted(imgs[idx][:, start:end], 1-alpha, imgs[nxt][:, start:end], alpha, 0)
                    frame[:, start:end] = strip
        else:
            idx_base = (f * val * 10 * speed_mult)
            for s, (start, end) in enumerate(boundaries):
                l_idx = int((idx_base + (s if is_random else 0)) % len(imgs))
                if orientation=="Orizzontale": frame[start:end, :] = imgs[l_idx][start:end, :]
                else: frame[:, start:end] = imgs[l_idx][:, start:end]

        if top_alpha > 0:
            frame = cv2.addWeighted(frame, 1 - top_alpha, imgs[0], top_alpha, 0)
        final_frames.append(frame)

    video_clip = ImageSequenceClip(final_frames, fps=fps)
    if up_aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as t_aud:
            t_aud.write(up_aud.read()); aud_path = t_aud.name
        video_clip = video_clip.set_audio(AudioFileClip(aud_path).subclip(0, min(AudioFileClip(aud_path).duration, max_limit)))
    
    out_path = tempfile.mktemp(suffix=".mp4")
    video_clip.write_videofile(out_path, codec="libx264", audio_codec="aac" if up_aud else None, fps=fps, bitrate="3000k", logger=None)
    return out_path

# --- UI ---
st.title("Recursive Cut Pro - Loop507")

# SEZIONE 1: ASSETS
with st.container():
    st.subheader("📁 1. Caricamento Risorse")
    c1, c2 = st.columns(2)
    with c1: up_img = st.file_uploader("Immagini", type=["jpg","png","jpeg"], accept_multiple_files=True)
    with c2: up_aud = st.file_uploader("Audio", type=["mp3","wav"])

st.divider()

# SEZIONE 2: MISURE & MOVIMENTO
st.subheader("✂️ 2. Misure & Evoluzione Tritato")
ck1, ck2, ck3 = st.columns(3)
with ck1:
    s_t = st.number_input("Start Tempo (sec)", 0.0, 60.0, 3.0)
    s_v = st.slider("Potenza Start %", 0, 100, 5)
with ck2:
    p_t = st.number_input("Picco Tempo (sec)", 0.0, 60.0, 5.0)
    p_v = st.slider("Potenza Picco %", 0, 100, 100)
with ck3:
    e_v = st.slider("Potenza End %", 0, 100, 3)
    speed_mult = st.slider("Moltiplicatore Velocità", 0.1, 5.0, 1.0)

st.divider()

# SEZIONE 3: RICOMPOSIZIONE
st.subheader("👁️ 3. Ricomposizione (Opacità)")
co1, co2 = st.columns(2)
with co1: fade_start = st.number_input("Inizio Dissolvenza (sec)", 0.0, 60.0, 5.5)
with co2: fade_end_v = st.slider("Opacità Finale %", 0, 100, 100)

st.divider()

# SEZIONE 4: STILE & OUTPUT
st.subheader("⚙️ 4. Configurazione & Rendering")
cs1, cs2, cs3 = st.columns(3)
with cs1:
    mode = st.radio("Effetto", ["Kinetic (Flusso)", "Recursive (Stutter)"])
    orientation = st.radio("Taglio", ["Orizzontale", "Verticale"])
with cs2:
    strand_val = st.slider("Grandezza Linee (px)", 1, 500, 60)
    max_limit = st.number_input("Durata Totale (sec)", 1, 60, 10)
with cs3:
    is_random = st.checkbox("Chaos Mode", value=True)
    use_base = st.checkbox("Sfondo Fisso Iniziale", value=False)

st.write("---")

if st.button("🎬 GENERA OUTPUT FINALE") and up_img:
    k_p = {'st':s_t, 'sv':s_v, 'pt':p_t, 'pv':p_v, 'ev':e_v}
    o_p = {'start_fade':fade_start, 'final_v':fade_end_v}
    with st.spinner("Rendering in corso..."):
        imgs = [np.array(Image.open(f).convert("RGB").resize((1280, 720))) for f in up_img[:25]]
        path = generate_master(imgs, up_aud, mode, orientation, strand_val, speed_mult, is_random, max_limit, use_base, k_p, o_p)
        
        st.subheader("✅ Output Finale")
        st.video(path)
        with open(path, "rb") as f:
            st.download_button("💾 SCARICA IL VIDEO MASTER", f, file_name="loop507_final.mp4")
