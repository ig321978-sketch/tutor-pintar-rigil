import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw
import edge_tts
import asyncio
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import imageio_ffmpeg
import moviepy.config as mp_config
import os
import re

mp_config.ffmpeg_binary = imageio_ffmpeg.get_ffmpeg_exe()

# --- KONFIGURASI API GEMINI ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    GEMINI_API_KEY = "MASUKKAN_API_KEY_ANDA_DI_SINI"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3.5-flash-lite')

# --- FUNGSI PEMBUAT SLIDE ILUSTRASI & DOODLE OTOMATIS ---
def buat_slide_storyboard(judul, visual_desc, teks_narasi, nomor_scene, total_scene, nama_file):
    # Kanvas latar belakang ceria gaya papan tulis digital / doodle
    img = Image.new('RGB', (1280, 720), color=(245, 247, 250))
    d = ImageDraw.Draw(img)
    
    # Header Kartu Animasi
    d.rectangle([50, 40, 1230, 130], fill=(41, 128, 185))
    d.text((80, 75), f"🎨 {judul} — Adegan {nomor_scene} dari {total_scene}", fill=(255, 255, 255))
    
    # Kotak Panel Ilustrasi / Konsep Doodle AI
    d.rectangle([50, 150, 1230, 320], fill=(235, 247, 248), outline=(52, 152, 219), width=2)
    d.text((80, 170), "💡 Konsep Ilustrasi / Animasi Doodle:", fill=(41, 128, 185))
    
    # Format teks ilustrasi visual
    vis_words = visual_desc.split()
    vis_lines, current_v_line = [], ""
    for w in vis_words:
        if len(current_v_line + " " + w) < 75:
            current_v_line += " " + w if current_v_line else w
        else:
            vis_lines.append(current_v_line)
            current_v_line = w
    vis_lines.append(current_v_line)
    
    y_v = 210
    for line in vis_lines[:3]:
        d.text((80, y_v), line, fill=(44, 62, 80))
        y_v += 32

    # Kotak Panel Naskah Narasi
    d.rectangle([50, 340, 1230, 610], fill=(255, 255, 255), outline=(189, 195, 199), width=2)
    d.text((80, 360), "🎙️ Naskah Narasi Suara Guru:", fill=(39, 174, 96))
    
    # Format teks narasi
    nar_words = teks_narasi.split()
    nar_lines, current_n_line = [], ""
    for w in nar_words:
        if len(current_n_line + " " + w) < 75:
            current_n_line += " " + w if current_n_line else w
        else:
            nar_lines.append(current_n_line)
            current_n_line = w
    nar_lines.append(current_n_line)
    
    y_n = 405
    for line in nar_lines[:6]:
        d.text((80, y_n), line, fill=(44, 62, 80))
        y_n += 32
        
    # Footer
    d.rectangle([50, 620, 1230, 670], fill=(236, 240, 241))
    d.text((80, 636), "✨ Tutor Pintar AI — Terjemahan Otomatis Materi ke Video Animasi", fill=(127, 140, 141))
    
    img.save(nama_file)
    return nama_file

# --- FUNGSI SUARA NARATOR ---
async def buat_suara_realistis(teks, nama_file):
    communicate = edge_tts.Communicate(teks, "id-ID-GadisNeural")
    await communicate.save(nama_file)

# --- ANTARMUKA APLIKASI ---
st.set_page_config(page_title="Tutor Pintar Profesional", page_icon="🎓", layout="centered")

st.title("🎓 Tutor Pintar AI - Otomasi Storyboard ke Video Animasi")
st.write("Unggah foto buku, AI akan membaca materi, membuat skrip animasi doodle, dan merender videonya secara otomatis!")

with st.form("user_form"):
    nama = st.text_input("Nama Siswa:", "Rigil Atriani")
    jenjang_kelas = st.selectbox("Jenjang & Kelas:", [
        "SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6",
        "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9",
        "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"
    ], index=2)
    mapel = st.text_input("Mata Pelajaran:", "Matematika")
    uploaded_file = st.file_uploader("Foto Halaman Buku Pelajaran:", type=["jpg", "jpeg", "png"])
    submit_button = st.form_submit_button(label="Ubah Buku Jadi Video Animasi! 🎬")

# --- PROSES UTAMA ---
if submit_button:
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(image, caption="Buku Pelajaran Asli", use_container_width=True)
        with col2:
            st.info(f"✨ **Halo {nama}!**\nAI sedang menganalisis materi dan menyusun storyboard animasi doodle untuk {mapel}.")
        
        with st.spinner("Menganalisis materi, merancang skrip animasi, merekam suara, dan merender video..."):
            try:
                if "SD" in jenjang_kelas:
                    gaya = "ramah, ceria, menggunakan analogi sehari-hari yang seru untuk anak-anak."
                elif "SMP" in jenjang_kelas:
                    gaya = "komunikatif, asik, dan relevan dengan dunia remaja."
                else:
                    gaya = "profesional, logis, terstruktur, dan akademis."

                # Master Prompt Otomatis di dalam Sistem AI
                prompt = f"""
                Kamu adalah AI Education Director dan Master Storyboarder untuk siswa bernama {nama} tingkat {jenjang_kelas} belajar {mapel}.
                1. Analisis materi di foto halaman buku tersebut secara mendalam.
                2. Pecah materi menjadi 4 sampai 5 adegan (scene) berurutan untuk video animasi doodle/ilustrasi interaktif.
                3. Gunakan gaya bahasa narasi yang {gaya}
                4. Format wajib untuk setiap adegan harus persis seperti ini:
                [VISUAL]: (Deskripsi ilustrasi visual doodle atau animasi 2D ceria yang relevan dengan materi)
                [NARASI]: (Teks kalimat penjelasan suara guru yang natural dan mendalam)
                ---SCENE---
                (Ulangi format di atas untuk setiap adegan berikutnya)
                """
                
                response = model.generate_content([prompt, image])
                teks_jawaban = response.text
                
                st.markdown("---")
                st.markdown(f"### 📜 Storyboard & Naskah Animasi ({mapel})")
                st.markdown(teks_jawaban)
                
                # Parsing Scene Berdasarkan Pemisah ---SCENE---
                raw_scenes = [s.strip() for s in teks_jawaban.split('---SCENE---') if s.strip()]
                if not raw_scenes:
                    raw_scenes = [teks_jawaban]
                
                scene_data = []
                full_narration_list = []
                
                for s in raw_scenes:
                    vis_match = re.search(r'\[VISUAL\]:(.*?)(?=\[NARASI\]|$)', s, re.DOTALL)
                    nar_match = re.search(r'\[NARASI\]:(.*)', s, re.DOTALL)
                    
                    visual_desc = vis_match.group(1).strip() if vis_match else "Ilustrasi konsep materi pelajaran yang edukatif."
                    narration_text = nar_match.group(1).strip() if nar_match else s
                    
                    clean_narration = re.sub(r'[*#_`>-]', '', narration_text)
                    full_narration_list.append(clean_narration)
                    
                    scene_data.append({
                        "visual": re.sub(r'[*#_`>-]', '', visual_desc),
                        "narration": clean_narration
                    })
                
                combined_audio_script = " ".join(full_narration_list)
                
                # Render Audio Keseluruhan
                file_suara = "suara_materi.mp3"
                asyncio.run(buat_suara_realistis(combined_audio_script, file_suara))
                
                audio_clip = AudioFileClip(file_suara)
                total_duration = audio_clip.duration
                durasi_per_scene = total_duration / len(scene_data)
                
                # Render Klip Animasi Video dengan Efek Zoom Dinamis
                video_clips = []
                for i, scene in enumerate(scene_data):
                    slide_path = buat_slide_storyboard(
                        f"Materi {mapel} ({jenjang_kelas})", 
                        scene["visual"], 
                        scene["narration"], 
                        i+1, 
                        len(scene_data), 
                        f"scene_{i+1}.jpg"
                    )
                    
                    slide_clip = ImageClip(slide_path).set_duration(durasi_per_scene)
                    # Efek animasi perbesaran dinamis (Ken Burns effect)
                    animated_clip = slide_clip.resize(lambda t: 1.0 + 0.03 * (t / durasi_per_scene))
                    video_clips.append(animated_clip)
                
                final_visual_clip = concatenate_videoclips(video_clips)
                final_video = final_visual_clip.set_audio(audio_clip)
                
                file_video = "video_presentasi.mp4"
                final_video.write_videofile(file_video, fps=24, codec="libx264", audio_codec="aac", logger=None)
                
                st.markdown("---")
                st.markdown("### 🎬 Pemutar Video Animasi Doodle & Storyboard:")
                st.video(file_video)
                
            except Exception as e:
                st.error(f"Terjadi kendala saat merender video: {e}")
    else:
        st.warning("Jangan lupa unggah foto halaman bukunya dulu ya!")
