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

# --- FUNZIONI DI SUPPORTO ---
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
def generate_master(up_master, up_trit, up_aud, mode, orientation, strand_val, speed_rec, intens_rec, max_limit, use_base, k_p, o_p, format_type):
    fps = 24
    total_f = int(max_limit * fps)
    
    # 1. Preparazione Immagini
    m_pil = Image.open(up_master).convert("RGB")
    m_img = resize_to_format(np.array(m_pil), format_type)
    
    t_imgs_raw = [np.array(Image.open(f).convert("RGB")) for f in up_trit[:30]]
    # Fondamentale: AGGIUNGIAMO LA MASTER alla lista delle foto tritate
    t_imgs_raw.append(m_img) 
    
    t_processed = [resize_to_format(img, format_type) for img in t_imgs_raw]
    h, w = m_img.shape[:2]
    
    # 2. Setup Griglia
    dim_to_cut = h if orientation == "Orizzontale" else w
    boundaries = []
    curr = 0
    while curr < dim_to_cut:
        s_w = random.randint(max(1, int(strand_val//2)), int(strand_val*2))
        if curr + s_w > dim_to_cut: s_w = dim_to_cut - curr
        boundaries.append((curr, int(curr + s_w)))
        curr += s_w

    offsets = [random.uniform(0, len(t_processed)) if not use_base else len(t_processed)-1 for _ in range(len(boundaries))]
    final_frames = []

    for f in range(total_f):
        curr_s = f / fps
        # Curva intensità semplice 3 punti
        mid = max_limit / 2
        val = (k_p['sv'] + (f/(total_f/2))*(k_p['pv']-k_p['sv']))/100 if curr_s <= mid else (k_p['pv'] + ((curr_s-mid)/mid)*(k_p['ev']-k_p['pv']))/100
        
        # 3. Magnetismo (Ricomposizione Organica)
        # Invece dell'opacità globale, calcoliamo una probabilità magnetica per ogni striscia
        magnet_prob = 0.0
        if curr_s > o_p['start_fade']:
            t_fade = (curr_s - o_p['start_fade']) / (max_limit - o_p['start_fade'])
            magnet_prob = min(1.0, t_fade * (o_p['final_v'] / 100))

        frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 4. Rendering Frame-by-Frame
        if mode == "Kinetic (Flusso)":
            for s, (start, end) in enumerate(boundaries):
                # Se il magnetismo vince, la striscia si blocca sulla Master
                if random.random() < magnet_prob:
                    if orientation=="Orizzontale": frame[start:end, :] = m_img[start:end, :]
                    else: frame[:, start:end] = m_img[:, start:end]
                else:
                    # Altrimenti continua il tritato
                    offsets[s] += (0.02 + (val * 0.4))
                    idx, nxt, alpha = int(offsets[s]%len(t_processed)), int((offsets[s]+1)%len(t_processed)), offsets[s]%1
                    if orientation=="Orizzontale":
                        frame[start:end, :] = cv2.addWeighted(t_processed[idx][start:end, :], 1-alpha, t_processed[nxt][start:end, :], alpha, 0)
                    else:
                        frame[:, start:end] = cv2.addWeighted(t_processed[idx][:, start:end], 1-alpha, t_processed[nxt][:, start:end], alpha, 0)
        else:
            # Recursive (Stutter) Magnetico
            idx_base = (f * intens_rec * 0.1 * speed_rec)
            for s, (start, end) in enumerate(boundaries):
                if random.random() < magnet_prob:
                    # Magnetismo: striscia nitida della Master
                    if orientation=="Orizzontale": frame[start:end, :] = m_img[start:end, :]
                    else: frame[:, start:end] = m_img[:, start:end]
                else:
                    # Tritato Recursive nervoso
                    l_idx = int((idx_base + s) % len(t_processed))
                    if orientation=="Orizzontale": frame[start:end, :] = t_processed[l_idx][start:end, :]
                    else: frame[:, start:end] = t_processed[l_idx][:, start:end]

        final_frames.append(frame)

    # 5. Export Video
    clip = ImageSequenceClip(final_frames, fps=fps)
    if up_aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as t_aud:
            t_aud.write(up_aud.read()); aud_path = t_aud.name
        clip = clip.set_audio(AudioFileClip(aud_path).subclip(0, min(AudioFileClip(aud_path).duration, max_limit)))
    
    out = tempfile.mktemp(suffix=".mp4")
    clip.write_videofile(out, codec="libx264", audio_codec="aac" if up_aud else None, fps=fps, logger=None)
    return out

# --- UI ---
st.title("Recursive Cut Pro - Loop507")

c_assets, c_regia, c_out = st.columns([1, 1.2, 1])

with c_assets:
    st.subheader("🖼️ Assets Master")
    up_master = st.file_uploader("FOTO MASTER (Obbligatoria)", type=["jpg","png","jpeg"])
    # Il controllo dell'opacità ora controlla il magnetismo finale
    final_op = st.slider("Magnetismo Finale %", 0, 100, 100, help="100% = Foto finale pulita e ricomposta. 0% = Resta tutto tritato.")
    fade_start = st.slider("Inizio Ricomposizione (sec)", 0.0, 10.0, 5.0, help="Da che secondo le strisce iniziano a 'tornare al loro posto' sulla Master?")
    use_base = st.checkbox("Usa come Sfondo Fisso", value=False)
    
    st.divider()
    up_trit = st.file_uploader("FOTO TRITATO (Multiple)", type=["jpg","png","jpeg"], accept_multiple_files=True)
    up_aud = st.file_uploader("Audio", type=["mp3","wav"])

with c_regia:
    st.subheader("✂️ Regia Tritato")
    st.write("Curve di Potenza (3 Slide):")
    s_v = st.slider("Start %", 0, 100, 5)
    p_v = st.slider("Picco %", 0, 100, 100)
    e_v = st.slider("End %", 0, 100, 10)
    
    st.divider()
    mode = st.radio("Modalità", ["Kinetic (Flusso)", "Recursive (Stutter)"])
    if mode == "Recursive (Stutter)":
        st.write("Parametri Recursive (Stutter):")
        speed_rec = st.slider("Velocità Recursive", 0.1, 5.0, 1.0)
        intens_rec = st.slider("Intensità Recursive", 1, 100, 50)
    else: speed_rec, intens_rec = 1.0, 1.0
        
    strand_val = st.slider("Grandezza Linee (px)", 1, 500, 60)
    orientation = st.radio("Taglio", ["Orizzontale", "Verticale"])

with c_out:
    st.subheader("🎬 Output")
    format_type = st.selectbox("Formato Video", ["16:9 (Orizzontale)", "9:16 (Verticale)", "1:1 (Quadrato)"])
    max_limit = st.number_input("Durata Totale (sec)", 1, 60, 10)
    
    st.write("---")
    if st.button("🚀 GENERA MASTER FINALE LOOP507"):
        if not up_master or not up_trit:
            st.error("Carica sia la Foto Master che le foto per il tritato!")
        else:
            with st.spinner("Rendering Evolution..."):
                path = generate_master(up_master, up_trit, up_aud, mode, orientation, strand_val, speed_rec, intens_rec, max_limit, use_base, {'sv':s_v,'pv':p_v,'ev':e_v}, {'start_fade':fade_start,'final_v':final_op}, format_type)
                st.video(path)
                with open(path, "rb") as f: st.download_button("💾 SCARICA VIDEO MASTER", f, file_name="loop507.mp4")
