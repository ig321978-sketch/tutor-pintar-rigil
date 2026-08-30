import streamlit as st
import time
import re
import asyncio
from PIL import Image
from google import genai
from google.genai import types
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip, vfx
import imageio_ffmpeg
import moviepy.config as mp_config

# Konfigurasi MoviePy
mp_config.ffmpeg_binary = imageio_ffmpeg.get_ffmpeg_exe()

# --- KONFIGURASI KUNCI API ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "MASUKKAN_API_KEY_ANDA_DI_SINI"

client = genai.Client(api_key=API_KEY)

# Fungsi membuat suara narasi lengkap
async def buat_suara(teks, nama_file):
    communicate = edge_tts.Communicate(teks, "id-ID-GadisNeural")
    await communicate.save(nama_file)

# --- ANTARMUKA PENGGUNA (UI) ---
st.set_page_config(page_title="Tutor Pintar Rigil", page_icon="🎓", layout="centered")

st.title("🎓 Tutor Pintar Rigil (Edisi Hybrid Premium)")
st.write("Aplikasi AI yang menghasilkan video animasi edukasi utuh dengan durasi lengkap!")

with st.form("user_form"):
    nama = st.text_input("Nama Siswa:", "Rigil")
    jenjang_kelas = st.selectbox("Jenjang & Kelas:", [
        "SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6",
        "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9",
        "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"
    ], index=2)
    mapel = st.text_input("Mata Pelajaran:", "Matematika")
    uploaded_file = st.file_uploader("Foto Halaman Buku Pelajaran:", type=["jpg", "jpeg", "png"])
    submit_button = st.form_submit_button(label="Mulai Belajar! 🎬")

# --- PROSES UTAMA ---
if submit_button:
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(image, caption="Buku Pelajaran Asli", use_container_width=True)
        with col2:
            st.info("✨ **Halo " + nama + "!** AI sedang menyusun materi utuh dan merender animasinya...")
            
        # TAHAP 1: PEMAHAMAN AI & NASKAH LENGKAP
        with st.spinner("1. Menganalisis materi dan menulis naskah lengkap..."):
            maksimal_coba = 3
            berhasil_baca = False
            video_prompt = ""
            naskah_audio = ""
            
            for percobaan in range(maksimal_coba):
                try:
                    if "SD" in jenjang_kelas:
                        gaya = "ramah, ceria, dan sangat pelan agar mudah dimengerti anak-anak."
                    else:
                        gaya = "komunikatif, asik, dan relevan dengan dunia remaja."

                    # UX Bridge Prompt ditambahkan instruksi Naskah Audio
                    ux_bridge_prompt = (
                        "Kamu adalah Tutor AI cerdas. Baca foto buku " + mapel + " ini untuk siswa " + jenjang_kelas + " bernama " + nama + ".\n"
                        "Keluarkan persis 4 bagian berikut:\n\n"
                        "===RINGKASAN_MATERI===\n(Tulis rangkuman materi dengan gaya " + gaya + ")\n\n"
                        "===KUIS_INTERAKTIF===\n(Berikan 1 soal kuis latihan)\n\n"
                        "===NASKAH_AUDIO===\n(Tulis naskah lisan penjelasan materi secara sangat lengkap dari awal sampai akhir, seolah guru sedang mengajar. Sapa " + nama + " di awal. Durasi bacaan sekitar 30-60 detik. HANYA TEKS yang dibaca, tanpa simbol.)\n\n"
                        "===MASTER_PROMPT_VIDEO===\n(Tulis SATU instruksi BAHASA INGGRIS untuk AI Video Generator: 'Create an educational video explaining [MATERI]. Visual style: 3-color doodle animation, dynamic whiteboard drawing.')"
                    )
                    
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=[ux_bridge_prompt, image]
                    )
                    full_text = response.text
                    
                    # Parsing teks aman
                    ringkasan = "Materi telah dipahami."
                    kuis = "Ayo belajar!"
                    naskah_audio = "Halo " + nama + "! Mari kita mulai belajar."
                    video_prompt = "Create a high quality educational doodle animation."
                    
                    if "===RINGKASAN_MATERI===" in full_text:
                        match_r = re.search(r'===RINGKASAN_MATERI===(.*?)(?====KUIS_INTERAKTIF===|$)', full_text, re.DOTALL)
                        if match_r: ringkasan = match_r.group(1).strip()
                    if "===KUIS_INTERAKTIF===" in full_text:
                        match_k = re.search(r'===KUIS_INTERAKTIF===(.*?)(?====NASKAH_AUDIO===|$)', full_text, re.DOTALL)
                        if match_k: kuis = match_k.group(1).strip()
                    if "===NASKAH_AUDIO===" in full_text:
                        match_n = re.search(r'===NASKAH_AUDIO===(.*?)(?====MASTER_PROMPT_VIDEO===|$)', full_text, re.DOTALL)
                        if match_n: naskah_audio = match_n.group(1).strip()
                    if "===MASTER_PROMPT_VIDEO===" in full_text:
                        match_p = re.search(r'===MASTER_PROMPT_VIDEO===(.*)', full_text, re.DOTALL)
                        if match_p: video_prompt = match_p.group(1).strip()

                    st.markdown("---")
                    st.markdown("## 📚 Rangkuman Materi (" + mapel + ")")
                    st.markdown(ringkasan)
                    st.markdown("---")
                    st.markdown("## 🏆 Kuis Tantangan untuk " + nama + "!")
                    st.markdown(kuis)
                    
                    berhasil_baca = True
                    break 
                    
                except Exception as e:
                    if "503" in str(e) and percobaan < maksimal_coba - 1:
                        time.sleep(5)
                    else:
                        st.error("Gagal saat menganalisis materi: " + str(e))
                        st.stop()
                        
        # TAHAP 2: RENDER VIDEO & PENGGABUNGAN AUDIO PENUH
        if berhasil_baca:
            with st.spinner("2. Menyatukan Suara Lengkap & Klip Animasi AI... (Memakan waktu sekitar 1-3 menit)"):
                try:
                    # A. Buat Audio Lengkap dari Naskah
                    teks_bersih = re.sub(r'[*#_`>-]', '', naskah_audio)
                    file_suara = "suara_premium.mp3"
                    asyncio.run(buat_suara(teks_bersih, file_suara))
                    audio_clip = AudioFileClip(file_suara)
                    durasi_total = audio_clip.duration
                    
                    # B. Generate Klip Video AI (8 Detik)
                    operation = client.models.generate_videos(
                        model="veo-3.1-fast-generate-preview",
                        prompt=video_prompt,
                        config=types.GenerateVideosConfig(resolution="720p")
                    )
                    
                    while not operation.done:
                        time.sleep(5)
                        operation = client.operations.get(operation)
                    
                    vid_result = operation.result.generated_videos[0]
                    file_veo_mentah = "veo_mentah.mp4"
                    client.files.download(file=vid_result.video)
                    vid_result.video.save(file_veo_mentah)
                    
                    # C. Penggabungan Hybrid (MoviePy melooping video 8 detik agar sepanjang audio)
                    veo_clip = VideoFileClip(file_veo_mentah)
                    # Looping video agar durasinya sama dengan durasi audio lisan
                    looped_video = veo_clip.fx(vfx.loop, duration=durasi_total)
                    final_video = looped_video.set_audio(audio_clip)
                    
                    file_video_final = "hasil_animasi_premium_lengkap.mp4"
                    final_video.write_videofile(file_video_final, fps=24, codec="libx264", audio_codec="aac", logger=None)
                    
                    st.markdown("---")
                    st.markdown("## 🎬 Video Pembelajaran Lengkap:")
                    st.video(file_video_final)
                    
                except Exception as e:
                    st.error("Gagal merender video akhir: " + str(e))
                
    else:
        st.warning("Silakan unggah foto halaman bukunya dulu!")
