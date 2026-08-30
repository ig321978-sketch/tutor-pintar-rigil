import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw

# Penambal kompatibilitas Pillow terbaru
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

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

# --- FUNGSI PEMBUAT SLIDE VISUAL ELEGAN ---
def buat_slide_elegan(judul, teks_scene, nomor_scene, total_scene, nama_file):
    img = Image.new('RGB', (1280, 720), color=(245, 247, 250))
    d = ImageDraw.Draw(img)
    
    # Header Kartu
    d.rectangle([50, 40, 1230, 130], fill=(41, 128, 185))
    d.text((80, 75), f"🎓 {judul} — Adegan {nomor_scene} dari {total_scene}", fill=(255, 255, 255))
    
    # Kotak Konten Slide
    d.rectangle([50, 150, 1230, 600], fill=(255, 255, 255), outline=(189, 195, 199), width=2)
    d.text((80, 180), "💡 Penjelasan Materi:", fill=(41, 128, 185))
    
    words = teks_scene.split()
    lines, current_line = [], ""
    for w in words:
        if len(current_line + " " + w) < 70:
            current_line += " " + w if current_line else w
        else:
            lines.append(current_line)
            current_line = w
    lines.append(current_line)
    
    y_text = 230
    for line in lines[:10]:
        d.text((80, y_text), line, fill=(44, 62, 80))
        y_text += 38
        
    # Footer
    d.rectangle([50, 610, 1230, 670], fill=(236, 240, 241))
    d.text((80, 630), "✨ Tutor Pintar AI — Belajar Interaktif & Menyenangkan", fill=(127, 140, 141))
    
    img.save(nama_file)
    return nama_file

# --- FUNGSI SUARA NARATOR ---
async def buat_suara_realistis(teks, nama_file):
    communicate = edge_tts.Communicate(teks, "id-ID-GadisNeural")
    await communicate.save(nama_file)

# --- ANTARMUKA APLIKASI ---
st.set_page_config(page_title="Tutor Pintar AI", page_icon="🎓", layout="centered")

st.title("🎓 Tutor Pintar AI - Belajar Interaktif")
st.write("Unggah foto halaman buku, dan AI akan menyajikan rangkuman materi, kuis interaktif, serta video animasi pembelajarannya secara otomatis!")

with st.form("user_form"):
    nama = st.text_input("Nama Siswa:", "Rigil Atriani")
    jenjang_kelas = st.selectbox("Jenjang & Kelas:", [
        "SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6",
        "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9",
        "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"
    ], index=2)
    mapel = st.text_input("Mata Pelajaran:", "Matematika")
    uploaded_file = st.file_uploader("Foto Halaman Buku Pelajaran:", type=["jpg", "jpeg", "png"])
    submit_button = st.form_submit_button(label="Mulai Belajar & Buat Video! 🎬")

# --- PROSES UTAMA ---
if submit_button:
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(image, caption="Buku Pelajaran Asli", use_container_width=True)
        with col2:
            st.info(f"✨ **Halo {nama}!**\nTutor sedang memproses materi {mapel} menjadi rangkuman, kuis, dan video animasi.")
        
        with st.spinner("Menganalisis materi, menyusun rangkuman, kuis, dan merender video animasi..."):
            try:
                if "SD" in jenjang_kelas:
                    gaya = "ramah, ceria, menggunakan analogi sehari-hari yang seru untuk anak-anak."
                elif "SMP" in jenjang_kelas:
                    gaya = "komunikatif, asik, dan relevan dengan dunia remaja."
                else:
                    gaya = "profesional, logis, terstruktur, dan akademis."

                # Master Prompt Terstruktur di Backend
                prompt = f"""
                Kamu adalah guru les privat profesional untuk siswa bernama {nama} tingkat {jenjang_kelas} belajar {mapel}.
                Analisis foto halaman buku ini dengan cermat dan berikan output dalam 3 bagian terpisah dengan judul persis seperti ini:

                ===RINGKASAN_MATERI===
                (Tulis penjelasan rangkuman materi yang mendalam, edukatif, dan mudah dipahami dengan gaya bahasa {gaya})

                ===KUIS_INTERAKTIF===
                (Berikan soal kuis latihan interaktif atau tantangan seru beserta opsi atau instruksi pengerjaannya untuk siswa)

                ===NASKAH_VIDEO===
                Scene 1: (Teks narasi suara guru untuk pengantar konsep dasar)
                Scene 2: (Teks narasi suara guru untuk penjelasan inti materi)
                Scene 3: (Teks narasi suara guru untuk contoh penerapan atau analogi)
                Scene 4: (Teks narasi suara guru untuk kuis penutup dan penyemangat)
                """
                
                response = model.generate_content([prompt, image])
                full_text = response.text
                
                # Parsing bagian respons AI agar bersih dari prompt mentah
                materi_part = ""
                kuis_part = ""
                naskah_part = ""
                
                if "===RINGKASAN_MATERI===" in full_text and "===KUIS_INTERAKTIF===" in full_text:
                    parts = full_text.split("===KUIS_INTERAKTIF===")
                    materi_part = parts[0].replace("===RINGKASAN_MATERI===", "").strip()
                    remaining = parts[1]
                    if "===NASKAH_VIDEO===" in remaining:
                        subparts = remaining.split("===NASKAH_VIDEO===")
                        kuis_part = subparts[0].strip()
                        naskah_part = subparts[1].strip()
                    else:
                        kuis_part = remaining.strip()
                else:
                    materi_part = full_text
                    kuis_part = "Ayo kerjakan latihan soal pada halaman buku di atas!"
                    naskah_part = full_text

                # 1. Tampilkan Rangkuman Materi Pelajaran di UI secara bersih
                st.markdown("---")
                st.markdown(f"## 📚 Rangkuman Materi ({mapel})")
                st.markdown(materi_part)
                
                # 2. Tampilkan Kuis Interaktif di UI secara bersih
                st.markdown("---")
                st.markdown(f"## 🏆 Kuis Interaktif untuk {nama}!")
                st.markdown(kuis_part)
                
                # Ekstrak scene dari naskah video untuk backend rendering
                scene_matches = re.findall(r'Scene\s*\d+\s*:\s*(.*?)(?=(?:Scene\s*\d+\s*:)|$)', naskah_part, re.DOTALL | re.IGNORECASE)
                if not scene_matches:
                    scene_matches = [s.strip() for s in naskah_part.split('\n') if s.strip()]
                
                scene_texts = [re.sub(r'[*#_`>-]', '', s).strip() for s in scene_matches if s.strip()]
                if not scene_texts:
                    scene_texts = [re.sub(r'[*#_`>-]', '', materi_part)]
                
                combined_narration = " ".join(scene_texts)
                
                # Render Audio Narasi di Backend
                file_suara = "suara_materi.mp3"
                asyncio.run(buat_suara_realistis(combined_narration, file_suara))
                
                audio_clip = AudioFileClip(file_suara)
                total_duration = audio_clip.duration
                durasi_per_scene = total_duration / len(scene_texts)
                
                # Render Video Animasi di Backend
                video_clips = []
                for i, text_scene in enumerate(scene_texts):
                    slide_path = buat_slide_elegan(
                        f"Materi {mapel} ({jenjang_kelas})", 
                        text_scene, 
                        i+1, 
                        len(scene_texts), 
                        f"scene_{i+1}.jpg"
                    )
                    slide_clip = ImageClip(slide_path).set_duration(durasi_per_scene)
                    animated_clip = slide_clip.resize(lambda t: 1.0 + 0.03 * (t / durasi_per_scene))
                    video_clips.append(animated_clip)
                
                final_visual_clip = concatenate_videoclips(video_clips)
                final_video = final_visual_clip.set_audio(audio_clip)
                
                file_video = "video_presentasi.mp4"
                final_video.write_videofile(file_video, fps=24, codec="libx264", audio_codec="aac", logger=None)
                
                # 3. Tampilkan Pemutar Video Animasi di UI
                st.markdown("---")
                st.markdown("## 🎬 Video Animasi Pembelajaran:")
                st.video(file_video)
                
            except Exception as e:
                st.error(f"Terjadi kendala saat memproses materi atau merender video: {e}")
    else:
        st.warning("Jangan lupa unggah foto halaman bukunya dulu ya!")
