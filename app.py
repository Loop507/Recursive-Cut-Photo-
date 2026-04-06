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

# --- UTILS ---
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

# --- ENGINE ---
def generate_master(up_master, up_trit, up_aud, mode, orientation, strand_val, speed_rec, intens_rec, max_limit, k_p, o_p, format_type):
    fps = 24
    total_f = int(max_limit * fps)
    
    # 1. Preparazione Immagini
    m_img = resize_to_format(np.array(Image.open(up_master).convert("RGB")), format_type)
    t_processed = [resize_to_format(np.array(Image.open(f).convert("RGB")), format_type) for f in up_trit[:30]]
    
    # MIX TOTALE: La master è una delle tante nel mazzo del caos
    all_imgs = t_processed + [m_img]
    h, w = m_img.shape[:2]
    
    # 2. Setup Griglia (Strisce)
    dim_to_cut = h if orientation == "Orizzontale" else w
    boundaries = []
    curr = 0
    while curr < dim_to_cut:
        s_w = random.randint(max(1, int(strand_val//2)), int(strand_val*2))
        if curr + s_w > dim_to_cut: s_w = dim_to_cut - curr
        boundaries.append((curr, int(curr + s_w)))
        curr += s_w

    offsets = [random.uniform(0, len(all_imgs)) for _ in range(len(boundaries))]
    final_frames = []

    for f in range(total_f):
        curr_s = f / fps
        mid = max_limit / 2
        # Curva intensità (Le 3 Misure: Start, Picco, End)
        val = (k_p['sv'] + (f/(total_f/2))*(k_p['pv']-k_p['sv']))/100 if curr_s <= mid else (k_p['pv'] + ((curr_s-mid)/mid)*(k_p['ev']-k_p['pv']))/100
        
        # Calcolo Magnetismo (Ricomposizione)
        magnet_prob = 0.0
        dist_mult = 1.0 # Moltiplicatore distorsione (va a 0 quando si ricompone)
        if curr_s > o_p['start_fade']:
            t_fade = (curr_s - o_p['start_fade']) / (max_limit - o_p['start_fade'])
            magnet_prob = min(1.0, t_fade * (o_p['final_v'] / 100))
            dist_mult = 1.0 - magnet_prob

        frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 3. Rendering Striscia per Striscia
        for s, (start, end) in enumerate(boundaries):
            # A. Decidiamo se la striscia è "Magnetizzata" alla Master o nel Caos
            if random.random() < magnet_prob:
                target_img = m_img
                shift = 0 # Posizione perfetta
            else:
                # CAOS: Scelta casuale e slittamento violento
                target_img = random.choice(all_imgs)
                shift = int(random.uniform(-200, 200) * val * dist_mult)

            # B. Applicazione Effetto
            if mode == "Kinetic (Flusso)":
                # Nel Kinetic usiamo gli offset per un movimento fluido delle immagini caricate
                offsets[s] += (0.02 + (val * 0.4))
                if random.random() > magnet_prob: # Se non è ancora magnetizzata, usa il flusso
                    idx = int(offsets[s] % len(all_imgs))
                    target_img = all_imgs[idx]
                
            if orientation == "Orizzontale":
                strip = np.roll(target_img[start:end, :], shift, axis=1)
                frame[start:end, :] = strip
            else:
                strip = np.roll(target_img[:, start:end], shift, axis=0)
                frame[:, start:end] = strip

        final_frames.append(frame)

    # 4. Salvataggio e Audio
    clip = ImageSequenceClip(final_frames, fps=fps)
    if up_aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as t_aud:
            t_aud.write(up_aud.read()); aud_path = t_aud.name
        clip = clip.set_audio(AudioFileClip(aud_path).subclip(0, min(AudioFileClip(aud_path).duration, max_limit)))
    
    out = tempfile.mktemp(suffix=".mp4")
    clip.write_videofile(out, codec="libx264", audio_codec="aac" if up_aud else None, fps=fps, bitrate="4000k", logger=None)
    return out

# --- INTERFACCIA ---
st.title("Recursive Cut Pro - Loop507 🚀")

c_assets, c_regia, c_out = st.columns([1, 1.2, 1])

with c_assets:
    st.subheader("🖼️ Master Layer")
    up_master = st.file_uploader("FOTO MASTER (Target Finale)", type=["jpg","png","jpeg"])
    final_op = st.slider("Magnetismo Finale %", 0, 100, 100)
    fade_start = st.slider("Inizio Ricomposizione (sec)", 0.0, 10.0, 5.0)
    
    st.divider()
    up_trit = st.file_uploader("FOTO TRITATO (Multiple)", type=["jpg","png","jpeg"], accept_multiple_files=True)
    up_aud = st.file_uploader("Audio", type=["mp3","wav"])

with c_regia:
    st.subheader("✂️ Regia del Caos")
    st.write("Curve di Potenza (Start -> Picco -> End):")
    s_v = st.slider("Start %", 0, 100, 5)
    p_v = st.slider("Picco %", 0, 100, 100)
    e_v = st.slider("End %", 0, 100, 10)
    
    st.divider()
    mode = st.radio("Effetto", ["Kinetic (Flusso)", "Recursive (Stutter)"])
    strand_val = st.slider("Grandezza Linee (px)", 1, 500, 60)
    orientation = st.radio("Direzione Taglio", ["Orizzontale", "Verticale"])

with c_out:
    st.subheader("🎬 Output")
    format_type = st.selectbox("Formato", ["16:9 (Orizzontale)", "9:16 (Verticale)", "1:1 (Quadrato)"])
    max_limit = st.number_input("Durata (sec)", 1, 60, 10)
    
    if st.button("🚀 GENERA MASTER FINALE"):
        if not up_master or not up_trit:
            st.error("Carica sia la Master che il Tritato!")
        else:
            with st.spinner("Distruggendo tutto..."):
                path = generate_master(up_master, up_trit, up_aud, mode, orientation, strand_val, 1.0, 1.0, max_limit, 
                                       {'sv':s_v,'pv':p_v,'ev':e_v}, {'start_fade':fade_start,'final_v':final_op}, format_type)
                st.video(path)
                with open(path, "rb") as f: st.download_button("💾 SCARICA MASTER", f, file_name="loop507_evolution.mp4")
