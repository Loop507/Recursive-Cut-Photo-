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
def get_val(f, fps, total_s, s_v, p_v, e_v):
    curr = f / fps
    # Dividiamo il tempo in due metà per la curva delle 3 misure
    mid = total_s / 2
    if curr <= mid:
        t = curr / mid
        return (s_v + t * (p_v - s_v)) / 100
    else:
        t = (curr - mid) / (total_s - mid)
        return (p_v + t * (e_v - p_v)) / 100

def resize_to_format(img, format_type):
    h, w = img.shape[:2]
    if format_type == "16:9 (Orizzontale)": target_w, target_h = 1280, 720
    elif format_type == "9:16 (Verticale)": target_w, target_h = 720, 1280
    else: target_w, target_h = 1080, 1080
    
    # Ritaglio centrale (Center Crop)
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
def generate_master(master_img, trit_imgs, up_aud, mode, orientation, strand_val, speed_recursive, intensity_recursive, max_limit, use_base, k_params, op_params, format_type):
    fps = 24
    total_f = int(max_limit * fps)
    
    # Pre-elaborazione immagini
    m_img = resize_to_format(master_img, format_type)
    t_imgs = [resize_to_format(img, format_type) for img in trit_imgs]
    h, w = m_img.shape[:2]
    
    dim_to_cut = h if orientation == "Orizzontale" else w
    boundaries = []
    curr = 0
    while curr < dim_to_cut:
        s_w = random.randint(max(1, strand_val//2), strand_val*2)
        if curr + s_w > dim_to_cut: s_w = dim_to_cut - curr
        boundaries.append((curr, curr + s_w))
        curr += s_w

    offsets = [random.uniform(0, len(t_imgs)) if not use_base else 0.0 for _ in range(len(boundaries))]
    final_frames = []

    for f in range(total_f):
        curr_s = f / fps
        # Valore dai 3 slide (Start, Picco, End)
        val = get_val(f, fps, max_limit, k_params['sv'], k_params['pv'], k_params['ev'])
        
        # Opacità Foto Master (Ricomposizione)
        top_alpha = 0.0
        if curr_s > op_params['start_fade']:
            t_fade = (curr_s - op_params['start_fade']) / (max_limit - op_params['start_fade'])
            top_alpha = min(1.0, t_fade * (op_params['final_v'] / 100))

        frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        if mode == "Kinetic (Flusso)":
            for s, (start, end) in enumerate(boundaries):
                offsets[s] += 0.02 + (val * 0.4)
                idx, nxt, alpha = int(offsets[s]%len(t_imgs)), int((offsets[s]+1)%len(t_imgs)), offsets[s]%1
                if orientation=="Orizzontale":
                    frame[start:end, :] = cv2.addWeighted(t_imgs[idx][start:end, :], 1-alpha, t_imgs[nxt][start:end, :], alpha, 0)
                else:
                    frame[:, start:end] = cv2.addWeighted(t_imgs[idx][:, start:end], 1-alpha, t_imgs[nxt][:, start:end], alpha, 0)
        else:
            # Recursive (Stutter) con slide dedicati
            idx_base = (f * intensity_recursive * 0.1 * speed_recursive)
            for s, (start, end) in enumerate(boundaries):
                l_idx = int((idx_base + s) % len(t_imgs))
                if orientation=="Orizzontale": frame[start:end, :] = t_imgs[l_idx][start:end, :]
                else: frame[:, start:end] = t_imgs[l_idx][:, start:end]

        if top_alpha > 0:
            frame = cv2.addWeighted(frame, 1 - top_alpha, m_img, top_alpha, 0)
        elif use_base:
            # Se non c'è ancora la dissolvenza sopra, ma vogliamo la base sotto
            mask = (frame == [0,0,0]).all(axis=2)
            frame[mask] = m_img[mask]
            
        final_frames.append(frame)

    video_clip = ImageSequenceClip(final_frames, fps=fps)
    if up_aud:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as t_aud:
            t_aud.write(up_aud.read()); aud_path = t_aud.name
        video_clip = video_clip.set_audio(AudioFileClip(aud_path).subclip(0, min(AudioFileClip(aud_path).duration, max_limit)))
    
    out_path = tempfile.mktemp(suffix=".mp4")
    video_clip.write_videofile(out_path, codec="libx264", audio_codec="aac" if up_aud else None, fps=fps, bitrate="3000k", logger=None)
    return out_path

# --- INTERFACCIA ---
st.title("Recursive Cut Pro - Loop507")

col_assets, col_regia, col_output = st.columns([1, 1.2, 1])

with col_assets:
    st.subheader("🖼️ Assets Master")
    up_master = st.file_uploader("FOTO MASTER (Base/Top)", type=["jpg","png","jpeg"])
    final_op = st.slider("Opacità Finale Master %", 0, 100, 100)
    fade_start = st.slider("Inizio Dissolvenza (sec)", 0.0, 30.0, 5.0)
    use_base = st.checkbox("Usa come Sfondo Fisso", value=False)
    
    st.divider()
    up_trit = st.file_uploader("FOTO TRITATO (Multiple)", type=["jpg","png","jpeg"], accept_multiple_files=True)
    up_aud = st.file_uploader("Audio", type=["mp3","wav"])

with col_regia:
    st.subheader("✂️ Regia Tritato")
    st.write("Curve di Potenza (3 Slide):")
    s_v = st.slider("Start %", 0, 100, 5)
    p_v = st.slider("Picco %", 0, 100, 100)
    e_v = st.slider("End %", 0, 100, 10)
    
    st.divider()
    mode = st.radio("Modalità", ["Kinetic (Flusso)", "Recursive (Stutter)"])
    
    if mode == "Recursive (Stutter)":
        st.write("Parametri Recursive:")
        speed_rec = st.slider("Velocità Recursive", 0.1, 5.0, 1.0)
        intens_rec = st.slider("Intensità Recursive", 1, 100, 50)
    else:
        speed_rec, intens_rec = 1.0, 1.0
        
    strand_val = st.slider("Grandezza Linee (px)", 1, 500, 60)
    orientation = st.radio("Taglio", ["Orizzontale", "Verticale"])

with col_output:
    st.subheader("🎬 Output")
    format_type = st.selectbox("Formato Video", ["16:9 (Orizzontale)", "9:16 (Verticale)", "1:1 (Quadrato)"])
    max_limit = st.number_input("Durata Totale (sec)", 1, 60, 10)
    
    if st.button("🚀 GENERA MASTER FINALE") and up_master and up_trit:
        k_p = {'sv':s_v, 'pv':p_v, 'ev':e_v}
        o_p = {'start_fade':fade_start, 'final_v':final_op}
        with st.spinner("Rendering Master..."):
            m_img = np.array(Image.open(up_master).convert("RGB"))
            t_imgs = [np.array(Image.open(f).convert("RGB")) for f in up_trit[:30]]
            path = generate_master(m_img, t_imgs, up_aud, mode, orientation, strand_val, speed_rec, intens_rec, max_limit, use_base, k_p, o_p, format_type)
            st.video(path)
            with open(path, "rb") as f: st.download_button("💾 SCARICA VIDEO", f, file_name="loop507_master.mp4")
