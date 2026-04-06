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

def generate_master(up_master, up_trit, up_aud, mode, orientation, strand_val, max_limit, k_p, o_p, format_type):
    fps = 24
    total_f = int(max_limit * fps)
    
    # Setup Immagini
    m_img = resize_to_format(np.array(Image.open(up_master).convert("RGB")), format_type)
    t_processed = [resize_to_format(np.array(Image.open(f).convert("RGB")), format_type) for f in up_trit[:30]]
    all_imgs = t_processed + [m_img] 
    h, w = m_img.shape[:2]
    
    # Setup Strisce
    dim_to_cut = h if orientation == "Orizzontale" else w
    boundaries = []
    curr = 0
    while curr < dim_to_cut:
        s_w = random.randint(max(1, int(strand_val//2)), int(strand_val*2))
        if curr + s_w > dim_to_cut: s_w = dim_to_cut - curr
        boundaries.append((curr, int(curr + s_w)))
        curr += s_w

    final_frames = []

    for f in range(total_f):
        curr_s = f / fps
        mid = max_limit / 2
        
        # Potenza del Tritato (Misure)
        val = (k_p['sv'] + (f/(total_f/2))*(k_p['pv']-k_p['sv']))/100 if curr_s <= mid else (k_p['pv'] + ((curr_s-mid)/mid)*(k_p['ev']-k_p['pv']))/100
        
        # Logica Magnetismo Potenziata
        magnet_prob = 0.0
        dist_mult = 1.0 
        
        if curr_s > o_p['start_fade']:
            # Calcolo progressione magnetica
            t_fade = (curr_s - o_p['start_fade']) / (max_limit - o_p['start_fade'])
            magnet_prob = min(1.0, t_fade * (o_p['final_v'] / 100))
            
            # --- IL TRUCCO DEL COLLASSO ---
            # Se mancano meno di 0.5 secondi alla fine, forza il magnetismo al 100%
            if (max_limit - curr_s) < 0.5:
                magnet_prob = 1.0
                dist_mult = 0.0
            else:
                dist_mult = 1.0 - magnet_prob

        frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        for s, (start, end) in enumerate(boundaries):
            # Scelta immagine con "bias" verso la master che aumenta
            if random.random() < magnet_prob:
                target_img = m_img
                shift = 0 
            else:
                # Nel calderone: la Master è mischiata e DISTORTA
                target_img = random.choice(all_imgs)
                # Spostamento pixel violento (fino a 300px)
                shift = int(random.uniform(-300, 300) * val * dist_mult)

            if orientation == "Orizzontale":
                strip = np.roll(target_img[start:end, :], shift, axis=1)
                frame[start:end, :] = strip
            else:
                strip = np.roll(target_img[:, start:end], shift, axis=0)
                frame[:, start:end] = strip

        final_frames.append(frame)

    clip = ImageSequenceClip(final_frames, fps=fps)
    if up_aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as t_aud:
            t_aud.write(up_aud.read()); aud_path = t_aud.name
        clip = clip.set_audio(AudioFileClip(aud_path).subclip(0, min(AudioFileClip(aud_path).duration, max_limit)))
    
    out = tempfile.mktemp(suffix=".mp4")
    clip.write_videofile(out, codec="libx264", audio_codec="aac" if up_aud else None, fps=fps, bitrate="5000k", logger=None)
    return out

# --- UI ---
st.title("Recursive Cut Pro - Loop507 (Magnetic Snap) 🚀")

c1, c2, c3 = st.columns([1, 1.2, 1])

with c1:
    st.subheader("🖼️ Master")
    up_master = st.file_uploader("FOTO MASTER", type=["jpg","png","jpeg"])
    mag_final = st.slider("Snap Finale %", 0, 100, 100)
    mag_start = st.slider("Inizio Snap (sec)", 0.0, 10.0, 7.0)
    
    st.divider()
    up_trit = st.file_uploader("ALTRE FOTO", type=["jpg","png","jpeg"], accept_multiple_files=True)
    up_aud = st.file_uploader("Audio", type=["mp3","wav"])

with c2:
    st.subheader("✂️ Regia")
    sv = st.slider("Start Power %", 0, 100, 10)
    pv = st.slider("Picco Power %", 0, 100, 100)
    ev = st.slider("End Power %", 0, 100, 5)
    
    st.divider()
    mode = st.radio("Stile", ["Kinetic (Flusso)", "Recursive (Stutter)"])
    lines = st.slider("Linee (px)", 1, 500, 50)
    direction = st.radio("Taglio", ["Orizzontale", "Verticale"])

with c3:
    st.subheader("🎬 Export")
    fmt = st.selectbox("Formato", ["16:9 (Orizzontale)", "9:16 (Verticale)", "1:1 (Quadrato)"])
    dur = st.number_input("Durata (sec)", 1, 60, 10)
    
    if st.button("🚀 GENERA MASTER FINALE"):
        if up_master and up_trit:
            with st.spinner("Tritando la Master..."):
                path = generate_master(up_master, up_trit, up_aud, mode, direction, lines, dur, 
                                       {'sv':sv,'pv':pv,'ev':ev}, {'start_fade':mag_start,'final_v':mag_final}, fmt)
                st.video(path)
                with open(path, "rb") as f: st.download_button("💾 DOWNLOAD", f, file_name="loop507_snap.mp4")
        else:
            st.error("Mancano i file!")
