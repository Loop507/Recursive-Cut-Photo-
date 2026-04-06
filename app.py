import streamlit as st
import numpy as np
import cv2
from PIL import Image
from moviepy.editor import ImageSequenceClip, AudioFileClip
import tempfile
import random
import os

st.set_page_config(page_title="Recursive Cut Pro - Loop507", layout="wide")

def resize_to_format(img, format_type):
    h, w = img.shape[:2]
    if format_type == "16:9 (Orizzontale)": target_w, target_h = 1280, 720
    elif format_type == "9:16 (Verticale)": target_w, target_h = 720, 1280
    else: target_w, target_h = 1080, 1080
    aspect_target = target_w / target_h
    aspect_img = w / h
    if aspect_img > aspect_target:
        new_w = int(h * aspect_target)
        start_x = (w - new_w) // 2
        img_cropped = img[:, start_x:start_x+new_w]
    else:
        new_h = int(w / aspect_target)
        start_y = (h - new_h) // 2
        img_cropped = img[start_y:start_y+new_h, :]
    return cv2.resize(img_cropped, (target_w, target_h))

def generate_master(up_master, up_trit, up_aud, mode, orientation, strand_val, max_limit, k_p, o_p, format_type, inc_master, rand_lines):
    fps = 24
    total_f = int(max_limit * fps)
    
    # Gestione Immagini
    m_img = None
    if up_master:
        m_img = resize_to_format(np.array(Image.open(up_master).convert("RGB")), format_type)
    
    if up_trit:
        t_processed = [resize_to_format(np.array(Image.open(f).convert("RGB")), format_type) for f in up_trit[:30]]
    else:
        t_processed = [m_img] if m_img is not None else [np.zeros((720, 1280, 3), dtype=np.uint8)]

    # Pool di immagini (Il Calderone)
    pool_imgs = t_processed.copy()
    if m_img is not None and inc_master:
        pool_imgs.append(m_img)
    
    h, w = pool_imgs[0].shape[:2]
    
    # Calcolo Strisce
    dim_to_cut = h if orientation == "Orizzontale" else w
    boundaries = []
    curr = 0
    while curr < dim_to_cut:
        if rand_lines:
            s_w = random.randint(max(2, int(strand_val * 0.1)), int(strand_val * 2))
        else:
            s_w = random.randint(max(1, int(strand_val//2)), int(strand_val*2))
        if curr + s_w > dim_to_cut: s_w = dim_to_cut - curr
        boundaries.append((curr, int(curr + s_w)))
        curr += s_w

    kinetic_offsets = [random.uniform(0, len(pool_imgs)) for _ in range(len(boundaries))]
    final_frames = []

    for f in range(total_f):
        curr_s = f / fps
        mid = max_limit / 2
        val = (k_p['sv'] + (f/(total_f/2))*(k_p['pv']-k_p['sv']))/100 if curr_s <= mid else (k_p['pv'] + ((curr_s-mid)/mid)*(k_p['ev']-k_p['pv']))/100
        
        magnet_prob = 0.0
        dist_mult = 1.0 
        
        # Snap attivo solo se esiste la Master
        if m_img is not None and curr_s > o_p['start_fade']:
            t_fade = (curr_s - o_p['start_fade']) / (max_limit - o_p['start_fade'])
            magnet_prob = min(1.0, t_fade * (o_p['final_v'] / 100))
            if (max_limit - curr_s) < 0.5:
                magnet_prob = 1.0
                dist_mult = 0.0
            else:
                dist_mult = 1.0 - magnet_prob

        frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        for s, (start, end) in enumerate(boundaries):
            if random.random() < magnet_prob and m_img is not None:
                target_img = m_img
                if orientation == "Orizzontale": frame[start:end, :] = target_img[start:end, :]
                else: frame[:, start:end] = target_img[:, start:end]
            else:
                shift = int(random.uniform(-350, 350) * val * dist_mult)
                if mode == "Kinetic (Flusso)":
                    kinetic_offsets[s] += (0.04 + (val * 0.6))
                    idx, nxt, alpha = int(kinetic_offsets[s]%len(pool_imgs)), int((kinetic_offsets[s]+1)%len(pool_imgs)), kinetic_offsets[s]%1
                    img_a, img_b = pool_imgs[idx], pool_imgs[nxt]
                    if orientation == "Orizzontale":
                        s_a, s_b = np.roll(img_a[start:end, :], shift, axis=1), np.roll(img_b[start:end, :], shift, axis=1)
                        frame[start:end, :] = cv2.addWeighted(s_a, 1-alpha, s_b, alpha, 0)
                    else:
                        s_a, s_b = np.roll(img_a[:, start:end], shift, axis=0), np.roll(img_b[:, start:end], shift, axis=0)
                        frame[:, start:end] = cv2.addWeighted(s_a, 1-alpha, s_b, alpha, 0)
                else:
                    target_img = random.choice(pool_imgs)
                    if orientation == "Orizzontale": frame[start:end, :] = np.roll(target_img[start:end, :], shift, axis=1)
                    else: frame[:, start:end] = np.roll(target_img[:, start:end], shift, axis=0)
        final_frames.append(frame)

    clip = ImageSequenceClip(final_frames, fps=fps)
    if up_aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as t_aud:
            t_aud.write(up_aud.read()); aud_path = t_aud.name
        clip = clip.set_audio(AudioFileClip(aud_path).subclip(0, min(AudioFileClip(aud_path).duration, max_limit)))
    
    out = tempfile.mktemp(suffix=".mp4")
    clip.write_videofile(out, codec="libx264", audio_codec="aac" if up_aud else None, fps=fps, bitrate="6000k", logger=None)
    return out

# --- INTERFACCIA ---
st.title("Recursive Cut Pro - Loop507 Universal Studio 🚀")

col1, col2, col3 = st.columns([1, 1.2, 1])

with col1:
    st.subheader("🖼️ Assets")
    up_master = st.file_uploader("FOTO MASTER (Punto d'arrivo)", type=["jpg","png","jpeg"])
    up_trit = st.file_uploader("FOTO TRITATO (Calderone)", type=["jpg","png","jpeg"], accept_multiple_files=True)
    up_aud = st.file_uploader("AUDIO", type=["mp3","wav"])
    st.divider()
    inc_master = st.toggle("Master nel Calderone", value=True)
    mag_final = st.slider("Magnetismo Finale %", 0, 100, 100)
    mag_start = st.slider("Inizio Snap (sec)", 0.0, 10.0, 7.0)

with col2:
    st.subheader("✂️ Regia del Caos")
    st.write("Curve di Potenza (Start > Picco > End):")
    sv = st.slider("Start Power %", 0, 100, 5)
    pv = st.slider("Picco Power %", 0, 100, 100)
    ev = st.slider("End Power %", 0, 100, 10)
    st.divider()
    mode = st.radio("Seleziona Stile", ["Kinetic (Flusso)", "Recursive (Stutter)"])
    lines = st.slider("Spessore Linee (px)", 1, 500, 45)
    rand_lines = st.toggle("Dimensioni Random", value=False)
    direction = st.radio("Direzione Taglio", ["Orizzontale", "Verticale"])

with col3:
    st.subheader("🎬 Export")
    fmt = st.selectbox("Formato Social", ["16:9 (Orizzontale)", "9:16 (Verticale)", "1:1 (Quadrato)"])
    dur = st.number_input("Durata (sec)", 1, 60, 10)
    if st.button("🚀 GENERA VIDEO"):
        if up_master or up_trit:
            with st.spinner("Processing..."):
                path = generate_master(up_master, up_trit, up_aud, mode, direction, lines, dur, 
                                       {'sv':sv,'pv':pv,'ev':ev}, {'start_fade':mag_start,'final_v':mag_final}, fmt, inc_master, rand_lines)
                st.video(path)
                with open(path, "rb") as f: st.download_button("💾 DOWNLOAD", f, file_name="loop507_final.mp4")
        else:
            st.error("Carica almeno una foto!")
