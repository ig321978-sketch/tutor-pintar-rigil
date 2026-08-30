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

# Mengaktifkan jalur FFmpeg otomatis
mp_config.ffmpeg_binary = imageio_ffmpeg.get_ffmpeg_exe()

# --- KONFIGURASI API GEMINI (AMAN DENGAN STREAMLIT SECRETS) ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    GEMINI_API_KEY = "MASUKKAN_API_KEY_ANDA_DI_SINI"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3.5-flash-lite')

# --- FUNGSI PEMBUAT SLIDE VISUAL DINAMIS ---
def buat_slide_dinamis(judul, teks_cerita, nomor_scene, total_scene, nama_file):
    img = Image.new('RGB', (1280, 720), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Header / Panel Judul Atas
    d.rectangle([40, 40, 1240, 130], fill=(41, 128, 185))
    d.text((70, 70), f"🎓 {judul} — Adegan {nomor_scene} dari {total_scene}", fill=(255, 255, 255))
    
    # Format teks per baris agar rapi
    words = teks_cerita.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line + " " + word) < 70:
            current_line += " " + word if current_line else word
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    
    y_text = 180
    for line in lines[:12]: 
        d.text((70, y_text), line, fill=(44, 62, 80))
        y_text = y_text + 40
        
    # Footer slide penanda aktif
    d.rectangle([40, 640, 1240, 680], fill=(236, 240, 241))
    d.text((70, 650), "✨ Tutor Pintar AI — Visual Bergeser Otomatis", fill=(127, 140, 141))
    
    img.save(nama_file)
    return nama_file

# --- FUNGSI SUARA NARATOR REALISTIS ---
async def buat_suara_realistis(teks, nama_file):
    communicate = edge_tts.Communicate(teks, "id-ID-GadisNeural")
    await communicate.save(nama_file)

# --- ANTARMUKA APLIKASI ---
st.set_page_config(page_title="Tutor Pintar Profesional", page_icon="🎓", layout="centered")

st.title("🎓 Tutor Pintar AI - Video Dinamis Berganti Adegan")
st.write("Unggah foto buku, dan AI akan merender video presentasi dengan transisi adegan yang aktif!")

with st.form("user_form"):
    nama = st.text_input("Nama Siswa:", "Rigil Atriani")
    jenjang_kelas = st.selectbox("Jenjang & Kelas:", [
        "SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6",
        "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9",
        "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"
    ], index=2)
    mapel = st.text_input("Mata Pelajaran:", "Matematika")
    uploaded_file = st.file_uploader("Foto Halaman Buku Pelajaran:", type=["jpg", "jpeg", "png"])
    submit_button = st.form_submit_button(label="Render Video Dinamis! 🎬")

# --- PROSES UTAMA ---
if submit_button:
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(image, caption="Buku Pelajaran Asli", use_container_width=True)
        with col2:
            st.info(f"✨ **Halo {nama}!**\nTutor sedang memecah materi {mapel} menjadi banyak adegan dinamis.")
        
        with st.spinner("Menganalisis materi, merekam suara natural, dan merender adegan..."):
            try:
                if "SD" in jenjang_kelas:
                    gaya = "ramah, ceria, menggunakan analogi sehari-hari yang seru untuk anak-anak."
                elif "SMP" in jenjang_kelas:
                    gaya = "komunikatif, asik, dan relevan dengan dunia remaja."
                else:
                    gaya = "profesional, logis, terstruktur, dan akademis."

                prompt = f"""
                Kamu adalah tutor ahli untuk siswa bernama {nama} tingkat {jenjang_kelas} belajar {mapel}.
                1. Analisis materi di foto halaman buku tersebut secara akurat.
                2. Jelaskan materi dengan gaya bahasa yang {gaya}
                3. Buat penjelasan yang mendalam dan terstruktur dari awal hingga kuis interaktif.
                """
                
                response = model.generate_content([prompt, image])
                teks_jawaban = response.text
                
                st.markdown("---")
                st.markdown(f"### 📜 Naskah Materi ({mapel})")
                st.markdown(teks_jawaban)
                
                teks_bersih = re.sub(r'[*#_`>-]', '', teks_jawaban)
                
                # Render Audio
                file_suara = "suara_materi.mp3"
                asyncio.run(buat_suara_realistis(teks_bersih, file_suara))
                
                audio_clip = AudioFileClip(file_suara)
                total_duration = audio_clip.duration
                
                # PEMOTONGAN CERDAS MENJADI BANYAK ADEGAN
                kalimat_list = [k.strip() for k in re.split(r'(?<=[.!?])\s+', teks_bersih) if k.strip()]
                
                scene_list = []
                temp_chunk = ""
                for kalimat in kalimat_list:
                    if len(temp_chunk + " " + kalimat) < 250:
                        temp_chunk += " " + kalimat if temp_chunk else kalimat
                    else:
                        scene_list.append(temp_chunk)
                        temp_chunk = kalimat
                if temp_chunk:
                    scene_list.append(temp_chunk)
                
                if len(scene_list) < 4:
                    words_list = teks_bersih.split()
                    chunk_size = max(1, len(words_list) // 8)
                    scene_list = [" ".join(words_list[i:i+chunk_size]) for i in range(0, len(words_list), chunk_size)]

                jumlah_scene = len(scene_list)
                durasi_per_scene = total_duration / jumlah_scene
                
                # Render Klip Slide Multi-Scene Aktif (Menggunakan set_duration & set_audio untuk MoviePy v1.0.3)
                video_clips = []
                for i, scene_teks in enumerate(scene_list):
                    slide_path = buat_slide_dinamis(f"Materi {mapel} ({jenjang_kelas})", scene_teks, i+1, jumlah_scene, f"scene_{i+1}.jpg")
                    slide_clip = ImageClip(slide_path).set_duration(durasi_per_scene)
                    video_clips.append(slide_clip)
                
                final_visual_clip = concatenate_videoclips(video_clips)
                final_video = final_visual_clip.set_audio(audio_clip)
                
                file_video = "video_presentasi.mp4"
                final_video.write_videofile(file_video, fps=24, codec="libx264", audio_codec="aac", logger=None)
                
                st.markdown("---")
                st.markdown("### 🎬 Pemutar Video Presentasi Dinamis:")
                st.video(file_video)
                
            except Exception as e:
                st.error(f"Terjadi kendala saat merender video: {e}")
    else:
        st.warning("Jangan lupa unggah foto halaman bukunya dulu ya!")
