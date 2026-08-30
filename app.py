import streamlit as st
import time
import re
from PIL import Image
from google import genai
from google.genai import types
from moviepy.editor import VideoFileClip, concatenate_videoclips
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

# --- INISIALISASI SESSION STATE ---
if 'naskah_siap' not in st.session_state:
    st.session_state.naskah_siap = False
if 'prompt_1' not in st.session_state:
    st.session_state.prompt_1 = ""
if 'prompt_2' not in st.session_state:
    st.session_state.prompt_2 = ""
if 'ringkasan_materi' not in st.session_state:
    st.session_state.ringkasan_materi = ""

# --- ANTARMUKA PENGGUNA (UI) ---
st.set_page_config(page_title="Tutor Pintar Rigil", page_icon="🎓", layout="centered")

st.title("🎓 Tutor Pintar Rigil (Mode Hemat & Presisi)")
st.write("Sistem dua langkah: Cek naskah gratis terlebih dahulu sebelum merender video berbayar!")

with st.form("user_form"):
    nama = st.text_input("Nama Siswa:", "Rigil")
    jenjang_kelas = st.selectbox("Jenjang & Kelas:", [
        "SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6",
        "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9",
        "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"
    ], index=2)
    mapel = st.text_input("Mata Pelajaran:", "Matematika")
    uploaded_file = st.file_uploader("Foto Halaman Buku Pelajaran:", type=["jpg", "jpeg", "png"])
    
    btn_analisis = st.form_submit_button(label="1. Analisis & Siapkan Naskah (Gratis) 📝")

# --- LANGKAH 1: ANALISIS & SUSUN PROMPT (GRATIS DENGAN SMART RETRY) ---
if btn_analisis:
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Buku Pelajaran Asli", use_container_width=True)
        
        with st.spinner("Membaca materi dan menyusun naskah rahasia..."):
            maksimal_coba = 3
            for percobaan in range(maksimal_coba):
                try:
                    visual_lock = "Visual strictly must be: Authentic whiteboard doodle. Only a human hand drawing simple black line art on a solid white background. No colors, no 3D, no motion graphics."
                    
                    ux_bridge_prompt = (
                        "Kamu adalah Tutor AI cerdas. Baca materi " + mapel + " ini untuk siswa " + jenjang_kelas + " bernama " + nama + ".\n"
                        "Keluarkan hasil dalam format ini:\n\n"
                        "===RINGKASAN===\n(Tulis rangkuman materi dengan ramah)\n\n"
                        "===SCENE_1_PROMPT===\n(Tulis instruksi Inggris. Format wajib: 'Create a video explaining [KONSEP]. " + visual_lock + " Audio: Indonesian voiceover saying Halo " + nama + ", [JELASKAN KONSEP]. Audio and hand drawing motion must perfectly sync.')\n\n"
                        "===SCENE_2_PROMPT===\n(Tulis instruksi Inggris. Format wajib: 'Create a video explaining [INTI]. " + visual_lock + " Audio: Indonesian voiceover explaining [INTI MATERI]. Audio and hand drawing motion must perfectly sync.')"
                    )
                    
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=[ux_bridge_prompt, image]
                    )
                    full_text = response.text
                    
                    if "===RINGKASAN===" in full_text:
                        match_r = re.search(r'===RINGKASAN===(.*?)(?====SCENE_1_PROMPT===|$)', full_text, re.DOTALL)
                        if match_r: st.session_state.ringkasan_materi = match_r.group(1).strip()
                    if "===SCENE_1_PROMPT===" in full_text:
                        match_1 = re.search(r'===SCENE_1_PROMPT===(.*?)(?====SCENE_2_PROMPT===|$)', full_text, re.DOTALL)
                        if match_1: st.session_state.prompt_1 = match_1.group(1).strip()
                    if "===SCENE_2_PROMPT===" in full_text:
                        match_2 = re.search(r'===SCENE_2_PROMPT===(.*)', full_text, re.DOTALL)
                        if match_2: st.session_state.prompt_2 = match_2.group(1).strip()
                    
                    st.session_state.naskah_siap = True
                    st.success("Naskah berhasil dibuat! Silakan periksa di bawah.")
                    break # Berhasil, keluar dari loop
                    
                except Exception as e:
                    if "503" in str(e) and percobaan < maksimal_coba - 1:
                        st.warning("Server sibuk. Mengulang otomatis dalam 5 detik... (" + str(percobaan + 1) + "/" + str(maksimal_coba) + ")")
                        time.sleep(5)
                    else:
                        st.error("Gagal saat menganalisis materi: " + str(e))
                        break

    else:
        st.warning("Unggah foto bukunya dulu!")

# --- TAMPILKAN HASIL LANGKAH 1 ---
if st.session_state.naskah_siap:
    st.markdown("---")
    st.markdown("### 📋 Draft Naskah & Rangkuman")
    st.markdown(st.session_state.ringkasan_materi)
    
    st.info("Sistem telah menyiapkan instruksi rahasia untuk mesin Video AI. Jika Anda sudah yakin, silakan klik tombol *Render* di bawah ini.")
    
    # --- LANGKAH 2: RENDER VIDEO (BERBAYAR) ---
    if st.button("2. Render Video Papan Tulis (Berbayar - Menggunakan Kuota) 🎬"):
        with st.spinner("Merender video... (Mohon tunggu 2-4 Menit)"):
            try:
                # Render Scene 1
                op_1 = client.models.generate_videos(
                    model="veo-3.1-fast-generate-preview", prompt=st.session_state.prompt_1, config=types.GenerateVideosConfig(resolution="720p")
                )
                while not op_1.done:
                    time.sleep(5)
                    op_1 = client.operations.get(op_1)
                vid_1 = op_1.result.generated_videos[0]
                client.files.download(file=vid_1.video)
                vid_1.video.save("scene1.mp4")
                
                # Render Scene 2
                op_2 = client.models.generate_videos(
                    model="veo-3.1-fast-generate-preview", prompt=st.session_state.prompt_2, config=types.GenerateVideosConfig(resolution="720p")
                )
                while not op_2.done:
                    time.sleep(5)
                    op_2 = client.operations.get(op_2)
                vid_2 = op_2.result.generated_videos[0]
                client.files.download(file=vid_2.video)
                vid_2.video.save("scene2.mp4")
                
                # Gabung Video
                clip_1 = VideoFileClip("scene1.mp4")
                clip_2 = VideoFileClip("scene2.mp4")
                final_video = concatenate_videoclips([clip_1, clip_2])
                
                file_video_final = "doodle_hemat.mp4"
                final_video.write_videofile(file_video_final, fps=24, codec="libx264", audio_codec="aac", logger=None)
                
                st.markdown("---")
                st.markdown("## 🎬 Video Whiteboard Doodle Anda:")
                st.video(file_video_final)
                
            except Exception as e:
                st.error("Gagal merender video: " + str(e))
