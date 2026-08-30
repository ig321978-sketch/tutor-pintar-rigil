import streamlit as st
import asyncio
import re
from PIL import Image, ImageDraw
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import imageio_ffmpeg
import moviepy.config as mp_config
from google import genai

# Konfigurasi MoviePy & Pillow
mp_config.ffmpeg_binary = imageio_ffmpeg.get_ffmpeg_exe()
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "MASUKKAN_API_KEY_ANDA_DI_SINI"

client = genai.Client(api_key=API_KEY)

# Fungsi membuat narasi suara
async def buat_suara(teks, nama_file):
    communicate = edge_tts.Communicate(teks, "id-ID-GadisNeural")
    await communicate.save(nama_file)

# Fungsi membuat visual slide ilustrasi
def buat_frame(judul, teks_scene, nomor, total, nama_file):
    img = Image.new('RGB', (1280, 720), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    d.rectangle([0, 0, 1280, 120], fill=(41, 128, 185))
    d.text((60, 45), "🎓 " + str(judul) + " - Bagian " + str(nomor) + "/" + str(total), fill=(255, 255, 255))
    
    d.rectangle([60, 150, 1220, 580], fill=(245, 247, 250), outline=(200, 210, 220), width=3)
    d.text((100, 190), "💡 Pemahaman Konsep Materi:", fill=(41, 128, 185))
    
    words = teks_scene.split()
    lines, current_line = [], ""
    for w in words:
        if len(current_line + " " + w) < 55:
            current_line += " " + w if current_line else w
        else:
            lines.append(current_line)
            current_line = w
    lines.append(current_line)
    
    y_text = 250
    for line in lines[:8]:
        d.text((100, y_text), line, fill=(44, 62, 80))
        y_text += 45
        
    img.save(nama_file)
    return nama_file

# Antarmuka
st.set_page_config(page_title="Tutor Pintar", page_icon="🎓")
st.title("🎓 Tutor Pintar AI")

with st.form("user_form"):
    nama = st.text_input("Nama Siswa:", "Rigil")
    jenjang_kelas = st.selectbox("Jenjang & Kelas:", ["SD - Kelas 4", "SMP - Kelas 8", "SMA - Kelas 10"], index=1)
    mapel = st.text_input("Mata Pelajaran:", "Matematika")
    uploaded_file = st.file_uploader("Foto Buku:", type=["jpg", "png", "jpeg"])
    submit_button = st.form_submit_button("Mulai Belajar! 🎬")

if submit_button and uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Buku Asli")
    
    with st.spinner("AI sedang memahami materi dan merender video secara lokal..."):
        try:
            prompt = (
                "Kamu adalah Tutor AI cerdas. Pahami materi di buku " + mapel + " ini untuk siswa " + jenjang_kelas + " bernama " + nama + ".\n"
                "Keluarkan 3 bagian berikut:\n\n"
                "===RINGKASAN===\n(Tulis rangkuman ramah menyapa " + nama + ")\n\n"
                "===KUIS===\n(Berikan 1 soal kuis tantangan)\n\n"
                "===NASKAH===\nScene 1: (Sapaan dan pendahuluan)\nScene 2: (Penjelasan inti materi)\nScene 3: (Kesimpulan dan penyemangat)"
            )
            
            # Memanggil Gemini 1.5 Flash (Lebih ramah kuota gratis)
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=[prompt, image]
            )
            teks_ai = response.text
            
            ringkasan = "Materi berhasil dipahami."
            kuis = "Siap untuk kuis?"
            naskah = "Halo " + nama + "! Mari kita mulai belajar materi " + mapel + "."
            
            # Memecah teks dengan aman
            if "===RINGKASAN===" in teks_ai:
                match_r = re.search(r'===RINGKASAN===(.*?)(?====KUIS===|$)', teks_ai, re.DOTALL)
                if match_r: ringkasan = match_r.group(1).strip()
            if "===KUIS===" in teks_ai:
                match_k = re.search(r'===KUIS===(.*?)(?====NASKAH===|$)', teks_ai, re.DOTALL)
                if match_k: kuis = match_k.group(1).strip()
            if "===NASKAH===" in teks_ai:
                match_n = re.search(r'===NASKAH===(.*)', teks_ai, re.DOTALL)
                if match_n: naskah = match_n.group(1).strip()
            
            # Tampilkan ke layar pengguna
            st.markdown("---")
            st.markdown("## 📚 Rangkuman Materi\n" + ringkasan)
            st.markdown("---")
            st.markdown("## 🏆 Kuis Tantangan\n" + kuis)
            
            # Memisahkan naskah menjadi adegan
            scenes = [s.strip() for s in naskah.split('Scene') if len(s.strip()) > 10]
            if not scenes: 
                scenes = [ringkasan]
            
            # Proses Audio (Bebas Kuota)
            full_audio_text = " ".join([re.sub(r'[*#_`>-]', '', s) for s in scenes])
            file_suara = "suara.mp3"
            asyncio.run(buat_suara(full_audio_text, file_suara))
            audio_clip = AudioFileClip(file_suara)
            durasi_per_scene = audio_clip.duration / len(scenes)
            
            # Proses Video Gabungan (Bebas Kuota)
            klip_video = []
            for i, sc in enumerate(scenes):
                teks_bersih = re.sub(r'[*#_`>-]', '', sc)
                f_path = buat_frame(mapel, teks_bersih, i+1, len(scenes), "frame_" + str(i) + ".jpg")
                img_clip = ImageClip(f_path).set_duration(durasi_per_scene)
                klip_video.append(img_clip)
                
            final_vis = concatenate_videoclips(klip_video)
            final_vid = final_vis.set_audio(audio_clip)
            file_hasil = "video_materi.mp4"
            final_vid.write_videofile(file_hasil, fps=12, codec="libx264", audio_codec="aac", logger=None)
            
            st.markdown("---")
            st.markdown("## 🎬 Video Pembelajaran:\n")
            st.video(file_hasil)
            
        except Exception as e:
            st.error("Gagal memproses data. Pastikan API Key benar dan memiliki kuota: " + str(e))
