import streamlit as st
import time
import re
from PIL import Image
from google import genai
from google.genai import types
from moviepy.editor import VideoFileClip, concatenate_videoclips
import imageio_ffmpeg
import moviepy.config as mp_config

# Konfigurasi MoviePy untuk penggabungan video final
mp_config.ffmpeg_binary = imageio_ffmpeg.get_ffmpeg_exe()

# --- KONFIGURASI KUNCI API ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "MASUKKAN_API_KEY_ANDA_DI_SINI"

client = genai.Client(api_key=API_KEY)

# --- ANTARMUKA PENGGUNA (UI) ---
st.set_page_config(page_title="Tutor Pintar Rigil", page_icon="🎓", layout="centered")

st.title("🎓 Tutor Pintar Rigil (True Doodle Sync)")
st.write("Video papan tulis animasi di mana gambar dan suara dihasilkan bersamaan oleh AI agar sinkron sempurna!")

with st.form("user_form"):
    nama = st.text_input("Nama Siswa:", "Rigil")
    jenjang_kelas = st.selectbox("Jenjang & Kelas:", [
        "SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6",
        "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9",
        "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"
    ], index=2)
    mapel = st.text_input("Mata Pelajaran:", "Matematika")
    uploaded_file = st.file_uploader("Foto Halaman Buku Pelajaran:", type=["jpg", "jpeg", "png"])
    submit_button = st.form_submit_button(label="Buat Video Sinkron! 🎬")

# --- PROSES UTAMA ---
if submit_button:
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(image, caption="Buku Pelajaran Asli", use_container_width=True)
        with col2:
            st.info("✨ **Halo " + nama + "!** AI sedang memecah materi menjadi adegan animasi papan tulis...")
            
        # TAHAP 1: MEMECAH MATERI MENJADI ADEGAN (SCENE)
        with st.spinner("1. Menyiapkan instruksi visual dan suara (Backend)..."):
            try:
                # Instruksi ketat untuk AI agar HANYA membuat gaya Whiteboard Doodle
                visual_lock = "Visual style: Authentic whiteboard animation. A real human hand holding a black marker drawing simple 2D stick figures and line art on a white canvas. No 3D, no motion graphics, strictly hand-drawn doodle sketch style."
                
                ux_bridge_prompt = (
                    "Kamu adalah Tutor AI cerdas. Baca materi " + mapel + " ini untuk siswa " + jenjang_kelas + " bernama " + nama + ".\n"
                    "Keluarkan hasil dalam format ini:\n\n"
                    "===RINGKASAN===\n(Tulis rangkuman ramah untuk " + nama + ")\n\n"
                    "===SCENE_1_PROMPT===\n(Tulis prompt BAHASA INGGRIS untuk AI Video. Instruksi wajib: 'Create a video explaining [KONSEP AWAL]. " + visual_lock + " Audio style: Indonesian voiceover saying Halo " + nama + ", [JELASKAN KONSEP AWAL SECARA SINGKAT]. Audio and drawing motion must perfectly sync.')\n\n"
                    "===SCENE_2_PROMPT===\n(Tulis prompt BAHASA INGGRIS untuk AI Video. Instruksi wajib: 'Create a video explaining [INTI MATERI]. " + visual_lock + " Audio style: Indonesian voiceover explaining [JELASKAN INTI MATERI]. Audio and drawing motion must perfectly sync.')"
                )
                
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[ux_bridge_prompt, image]
                )
                full_text = response.text
                
                ringkasan = "Materi berhasil dipahami."
                prompt_scene_1 = "Create a whiteboard animation."
                prompt_scene_2 = "Create a whiteboard animation."
                
                if "===RINGKASAN===" in full_text:
                    match_r = re.search(r'===RINGKASAN===(.*?)(?====SCENE_1_PROMPT===|$)', full_text, re.DOTALL)
                    if match_r: ringkasan = match_r.group(1).strip()
                if "===SCENE_1_PROMPT===" in full_text:
                    match_1 = re.search(r'===SCENE_1_PROMPT===(.*?)(?====SCENE_2_PROMPT===|$)', full_text, re.DOTALL)
                    if match_1: prompt_scene_1 = match_1.group(1).strip()
                if "===SCENE_2_PROMPT===" in full_text:
                    match_2 = re.search(r'===SCENE_2_PROMPT===(.*)', full_text, re.DOTALL)
                    if match_2: prompt_scene_2 = match_2.group(1).strip()

                st.markdown("---")
                st.markdown("## 📚 Rangkuman Materi (" + mapel + ")")
                st.markdown(ringkasan)
                
            except Exception as e:
                st.error("Gagal saat merancang adegan: " + str(e))
                st.stop()
                        
        # TAHAP 2: RENDER VIDEO SINKRON & PENGGABUNGAN
        with st.spinner("2. Merender klip Doodle tersinkronisasi... (Estimasi: 3-5 Menit)"):
            try:
                # Render Scene 1
                op_1 = client.models.generate_videos(
                    model="veo-3.1-fast-generate-preview", prompt=prompt_scene_1, config=types.GenerateVideosConfig(resolution="720p")
                )
                while not op_1.done:
                    time.sleep(5)
                    op_1 = client.operations.get(op_1)
                vid_1 = op_1.result.generated_videos[0]
                file_1 = "scene1.mp4"
                client.files.download(file=vid_1.video)
                vid_1.video.save(file_1)
                
                # Render Scene 2
                op_2 = client.models.generate_videos(
                    model="veo-3.1-fast-generate-preview", prompt=prompt_scene_2, config=types.GenerateVideosConfig(resolution="720p")
                )
                while not op_2.done:
                    time.sleep(5)
                    op_2 = client.operations.get(op_2)
                vid_2 = op_2.result.generated_videos[0]
                file_2 = "scene2.mp4"
                client.files.download(file=vid_2.video)
                vid_2.video.save(file_2)
                
                # Menggabungkan kedua scene menjadi video utuh
                clip_1 = VideoFileClip(file_1)
                clip_2 = VideoFileClip(file_2)
                final_video = concatenate_videoclips([clip_1, clip_2])
                
                file_video_final = "doodle_sinkron_final.mp4"
                final_video.write_videofile(file_video_final, fps=24, codec="libx264", audio_codec="aac", logger=None)
                
                st.markdown("---")
                st.markdown("## 🎬 Video Whiteboard Doodle (Audio & Visual Sinkron):")
                st.video(file_video_final)
                
            except Exception as e:
                st.error("Gagal merender video akhir: " + str(e))
                
    else:
        st.warning("Silakan unggah foto halaman bukunya dulu!")
