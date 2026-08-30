import streamlit as st
import time
import asyncio
import re
import os
from PIL import Image

# Gunakan library google-genai terbaru untuk akses Video Generation (Veo)
from google import genai
from google.genai import types

import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip
import moviepy.video.fx.all as vfx
import imageio_ffmpeg
import moviepy.config as mp_config

mp_config.ffmpeg_binary = imageio_ffmpeg.get_ffmpeg_exe()

# --- KONFIGURASI KUNCI API ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "MASUKKAN_API_KEY_ANDA_DI_SINI"

# Inisialisasi klien SDK baru Google GenAI
client = genai.Client(api_key=API_KEY)

# --- FUNGSI SUARA NARATOR ---
async def buat_suara_realistis(teks, nama_file):
    communicate = edge_tts.Communicate(teks, "id-ID-GadisNeural")
    await communicate.save(nama_file)

st.set_page_config(page_title="Tutor Pintar AI - Animasi AI", page_icon="🎓", layout="centered")

st.title("🎓 Tutor Pintar AI - Video Animasi Realistis")
st.write("Sistem akan menganalisis buku, menulis prompt di balik layar, dan merender video animasi bergerak murni menggunakan model AI Text-to-Video!")

with st.form("user_form"):
    nama = st.text_input("Nama Siswa:", "Rigil Atriani")
    jenjang_kelas = st.selectbox("Jenjang & Kelas:", [
        "SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6",
        "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9",
        "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"
    ], index=2)
    mapel = st.text_input("Mata Pelajaran:", "Matematika")
    uploaded_file = st.file_uploader("Foto Halaman Buku Pelajaran:", type=["jpg", "jpeg", "png"])
    submit_button = st.form_submit_button(label="Generate Video Animasi AI! 🎬")

# --- PROSES UTAMA BACKEND ---
if submit_button:
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(image, caption="Buku Pelajaran Asli", use_container_width=True)
        with col2:
            st.info(f"✨ **Halo {nama}!** AI sedang menganalisis buku untuk menciptakan dunia animasi dari nol.")
        
        # 1. BACA MATERI DAN BUAT PROMPT UNTUK GENERATOR VIDEO
        with st.spinner("1. Menganalisis buku & menyusun Prompt Video Animasi (Backend)..."):
            try:
                # Meminta AI membuatkan "Prompt Video" berbahasa Inggris khusus untuk model video generator
                master_prompt = f"""
                Kamu adalah Sutradara Video Edukasi AI.
                Analisis materi di gambar buku pelajaran ini (untuk siswa {jenjang_kelas} belajar {mapel}).
                Keluarkan persis 3 bagian berikut:
                
                ===RINGKASAN===
                (Rangkuman materi bahasa Indonesia yang mudah dimengerti)
                
                ===NASKAH_SUARA===
                (Kalimat narasi guru bahasa Indonesia yang ramah, untuk disuarakan oleh AI Voice. Minimal 3 paragraf panjang.)
                
                ===PROMPT_VIDEO_AI===
                (Tulis SATU prompt sangat spesifik dalam BAHASA INGGRIS untuk mesin AI Text-to-Video. 
                Prompt ini harus mendeskripsikan animasi visual 2D doodle / motion graphics yang sedang menjelaskan materi tersebut. 
                Contoh: "A high quality 2D educational doodle animation of a colorful math concept, playful and moving graphic blocks, clean white background, smooth motion.")
                """
                
                # Memanggil Model Teks (Gemini 2.5)
                response = client.models.generate_content(
                    model='gemini-3.5-flash-lite',
                    contents=[master_prompt, image]
                )
                full_text = response.text
                
                # Mengekstrak output backend
                ringkasan = full_text.split("===RINGKASAN===")[1].split("===NASKAH_SUARA===")[0].strip() if "===RINGKASAN===" in full_text else "Materi siap."
                naskah = full_text.split("===NASKAH_SUARA===")[1].split("===PROMPT_VIDEO_AI===")[0].strip() if "===NASKAH_SUARA===" in full_text else "Selamat belajar!"
                video_prompt_en = full_text.split("===PROMPT_VIDEO_AI===")[1].strip() if "===PROMPT_VIDEO_AI===" in full_text else "2D educational animation doodle, high quality."
                
                st.markdown("---")
                st.markdown(f"### 📚 Rangkuman Materi")
                st.markdown(ringkasan)

            except Exception as e:
                st.error(f"Gagal saat menganalisis buku: {e}")
                st.stop()
                
        # 2. GENERATE VIDEO MENGGUNAKAN AI GOOGLE VEO
        with st.spinner(f"2. Mesin AI Text-to-Video (Veo 3.1) sedang merender gambar bergerak dari prompt... (Bisa memakan waktu 1-3 menit)"):
            try:
                # Mengirimkan prompt bahasa Inggris tersebut ke Mesin Pembuat Video
                operation = client.models.generate_videos(
                    model="veo-3.1-fast-generate-preview",
                    prompt=video_prompt_en,
                    config=types.GenerateVideosConfig(
                        resolution="720p"
                    )
                )
                
                # Menunggu video selesai dirender oleh cloud
                while not operation.done:
                    time.sleep(5)
                    operation = client.operations.get(operation)
                
                # Mengunduh dan menyimpan video mentah tanpa suara
                vid_result = operation.result.generated_videos[0]
                temp_video_path = "video_tanpa_suara.mp4"
                client.files.download(file=vid_result.video)
                vid_result.video.save(temp_video_path)
                
            except Exception as e:
                st.error(f"Terjadi kendala pada Video Generator AI: {e}")
                st.stop()

        # 3. GENERATE SUARA DAN GABUNGKAN
        with st.spinner("3. Menyinkronkan Suara Guru dengan Video Animasi..."):
            try:
                bersih_naskah = re.sub(r'[*#_`>-]', '', naskah)
                file_suara = "suara_narator.mp3"
                asyncio.run(buat_suara_realistis(bersih_naskah, file_suara))
                
                # Membuka Video Mentah dan Suara Narasi
                ai_video_clip = VideoFileClip(temp_video_path)
                ai_audio_clip = AudioFileClip(file_suara)
                
                # Karena durasi video AI biasanya pendek (sekitar 4-8 detik), 
                # kita melambatkan videonya atau meloopingnya agar sesuai dengan panjang durasi narasi suara guru
                if ai_video_clip.duration < ai_audio_clip.duration:
                    faktor_perlambat = ai_video_clip.duration / ai_audio_clip.duration
                    ai_video_clip = ai_video_clip.fx(vfx.speedx, faktor_perlambat)
                
                # Menyatukan audio ke dalam video
                final_video = ai_video_clip.set_audio(ai_audio_clip)
                file_video_final = "hasil_animasi_ai_veo.mp4"
                final_video.write_videofile(file_video_final, fps=24, codec="libx264", audio_codec="aac", logger=None)
                
                st.markdown("---")
                st.markdown("### 🎬 Video Animasi AI Anda Sudah Jadi!")
                st.video(file_video_final)
                
            except Exception as e:
                st.error(f"Gagal saat menggabungkan suara dan video: {e}")
                
    else:
        st.warning("Silakan unggah foto bukunya dulu.")
