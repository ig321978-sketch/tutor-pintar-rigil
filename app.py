import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw

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

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    GEMINI_API_KEY = "MASUKKAN_API_KEY_ANDA_DI_SINI"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3.5-flash-lite')

# --- FUNGSI PEMBUAT ILUSTRASI GRAFIS & DIAGRAM MATEMATIKA ---
def buat_slide_ilustrasi_grafis(judul, teks_scene, nomor_scene, total_scene, nama_file):
    # Kanvas latar belakang bersih dengan nuansa edukatif
    img = Image.new('RGB', (1280, 720), color=(240, 244, 248))
    d = ImageDraw.Draw(img)
    
    # Header Atas
    d.rectangle([0, 0, 1280, 110], fill=(41, 128, 185))
    d.text((50, 40), f"🎨 {judul} — Adegan {nomor_scene} dari {total_scene}", fill=(255, 255, 255))
    
    # Ilustrasi Grafis Visual (Blok & Diagram Berwarna Berdasarkan Adegan)
    # Kotak Ilustrasi Utama di sebelah kiri/atas
    d.rectangle([60, 140, 600, 580], fill=(255, 255, 255), outline=(52, 152, 219), width=4)
    d.text((90, 170), "📊 Ilustrasi & Blok Konsep Materi:", fill=(41, 128, 185))
    
    # Menggambar simulasi ilustrasi visual objek / kotak kelompok angka (berguna untuk matematika/visual)
    # Contoh menggambar kotak-kotak visual mewakili kelompok perkalian/objek
    start_x, start_y = 110, 240
    for row in range(2):
        for col in range(4):
            box_x = start_x + (col * 110)
            box_y = start_y + (row * 110)
            d.rectangle([box_x, box_y, box_x + 90, box_y + 90], fill=(235, 247, 248), outline=(41, 128, 185), width=2)
            d.text((box_x + 35, box_y + 35), f"⭐", fill=(230, 126, 34))

    # Kotak Panel Penjelasan Teks di sebelah kanan
    d.rectangle([630, 140, 1220, 580], fill=(255, 255, 255), outline=(189, 195, 199), width=3)
    d.text((660, 170), "💡 Penjelasan Langkah:", fill=(39, 174, 96))
    
    words = teks_scene.split()
    lines, current_line = [], ""
    for w in words:
        if len(current_line + " " + w) < 38:
            current_line += " " + w if current_line else w
        else:
            lines.append(current_line)
            current_line = w
    lines.append(current_line)
    
    y_text = 230
    for line in lines[:8]:
        d.text((660, y_text), line, fill=(44, 62, 80))
        y_text += 40
        
    # Footer Bawah
    d.rectangle([0, 630, 1280, 720], fill=(236, 240, 241))
    d.text((50, 660), "✨ Tutor Pintar AI — Video Animasi Ilustrasi Interaktif", fill=(127, 140, 141))
    
    img.save(nama_file)
    return nama_file

async def buat_suara_realistis(teks, nama_file):
    communicate = edge_tts.Communicate(teks, "id-ID-GadisNeural")
    await communicate.save(nama_file)

st.set_page_config(page_title="Tutor Pintar AI", page_icon="🎓", layout="centered")

st.title("🎓 Tutor Pintar AI - Video Ilustrasi Pembelajaran")
st.write("Unggah foto halaman buku, dan aplikasimu akan merender video ilustrasi grafis lengkap dengan kuis dan suara guru!")

with st.form("user_form"):
    nama = st.text_input("Nama Siswa:", "Rigil Atriani")
    jenjang_kelas = st.selectbox("Jenjang & Kelas:", [
        "SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6",
        "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9",
        "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"
    ], index=2)
    mapel = st.text_input("Mata Pelajaran:", "Matematika")
    uploaded_file = st.file_uploader("Foto Halaman Buku Pelajaran:", type=["jpg", "jpeg", "png"])
    submit_button = st.form_submit_button(label="Buat Video Ilustrasi Sekarang! 🎬")

if submit_button:
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(image, caption="Buku Pelajaran Asli", use_container_width=True)
        with col2:
            st.info(f"✨ **Halo {nama}!**\nTutor sedang merancang ilustrasi grafis dan video animasi untuk {mapel}.")
        
        with st.spinner("Menganalisis materi, menyusun kuis, dan merender video ilustrasi..."):
            try:
                if "SD" in jenjang_kelas:
                    gaya = "ramah, ceria, menggunakan analogi sehari-hari yang seru untuk anak-anak."
                elif "SMP" in jenjang_kelas:
                    gaya = "komunikatif, asik, dan relevan dengan dunia remaja."
                else:
                    gaya = "profesional, logis, terstruktur, dan akademis."

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

                st.markdown("---")
                st.markdown(f"## 📚 Rangkuman Materi ({mapel})")
                st.markdown(materi_part)
                
                st.markdown("---")
                st.markdown(f"## 🏆 Kuis Interaktif untuk {nama}!")
                st.markdown(kuis_part)
                
                scene_matches = re.findall(r'Scene\s*\d+\s*:\s*(.*?)(?=(?:Scene\s*\d+\s*:)|$)', naskah_part, re.DOTALL | re.IGNORECASE)
                if not scene_matches:
                    scene_matches = [s.strip() for s in naskah_part.split('\n') if s.strip()]
                
                scene_texts = [re.sub(r'[*#_`>-]', '', s).strip() for s in scene_matches if s.strip()]
                if not scene_texts:
                    scene_texts = [re.sub(r'[*#_`>-]', '', materi_part)]
                
                combined_narration = " ".join(scene_texts)
                
                file_suara = "suara_materi.mp3"
                asyncio.run(buat_suara_realistis(combined_narration, file_suara))
                
                audio_clip = AudioFileClip(file_suara)
                total_duration = audio_clip.duration
                durasi_per_scene = total_duration / len(scene_texts)
                
                video_clips = []
                for i, text_scene in enumerate(scene_texts):
                    slide_path = buat_slide_ilustrasi_grafis(
                        f"Materi {mapel} ({jenjang_kelas})", 
                        text_scene, 
                        i+1, 
                        len(scene_texts), 
                        f"scene_{i+1}.jpg"
                    )
                    slide_clip = ImageClip(slide_path).set_duration(durasi_per_scene)
                    animated_clip = slide_clip.resize(lambda t: 1.0 + 0.02 * (t / durasi_per_scene))
                    video_clips.append(animated_clip)
                
                final_visual_clip = concatenate_videoclips(video_clips)
                final_video = final_visual_clip.set_audio(audio_clip)
                
                file_video = "video_presentasi.mp4"
                final_video.write_videofile(file_video, fps=24, codec="libx264", audio_codec="aac", logger=None)
                
                st.markdown("---")
                st.markdown("## 🎬 Video Ilustrasi Grafis Pembelajaran:")
                st.video(file_video)
                
            except Exception as e:
                st.error(f"Terjadi kendala saat memproses materi atau merender video: {e}")
    else:
        st.warning("Jangan lupa unggah foto halaman bukunya dulu ya!")
