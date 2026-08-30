import streamlit as st
import time
from PIL import Image
from google import genai
from google.genai import types
import re # Tambahkan library Regex agar parsing teks sangat aman

# --- KONFIGURASI KUNCI API ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "MASUKKAN_API_KEY_ANDA_DI_SINI"

# Inisialisasi klien SDK Google GenAI
client = genai.Client(api_key=API_KEY)

# --- ANTARMUKA PENGGUNA (UI) ---
st.set_page_config(page_title="Tutor Pintar Rigil", page_icon="🎓", layout="centered")

st.title("🎓 Tutor Pintar Rigil")
st.write("Belajar asik dengan rangkuman cerdas dan video animasi Doodle 3 Warna yang di-generate langsung oleh AI!")

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

# --- PROSES UTAMA (UX BRIDGE & AI ENGINE) ---
if submit_button:
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(image, caption="Buku Pelajaran Asli", use_container_width=True)
        with col2:
            st.info(f"✨ **Halo {nama}!** AI sedang memahami materimu dan merancang animasinya...")
            
        # TAHAP 1: PEMAHAMAN AI & PENYUSUNAN UX BRIDGE PROMPT
        with st.spinner("1. Memahami materi dan merumuskan konsep video (Backend)..."):
            try:
                if "SD" in jenjang_kelas:
                    gaya = "ramah, ceria, dengan analogi yang seru untuk anak-anak."
                elif "SMP" in jenjang_kelas:
                    gaya = "komunikatif, asik, dan relevan dengan dunia remaja."
                else:
                    gaya = "profesional, logis, terstruktur, dan akademis."

                # UX Bridge: Instruksi tersembunyi
                ux_bridge_prompt = f"""
                Kamu adalah Tutor AI cerdas. Baca dan pahami foto halaman buku {mapel} ini untuk siswa bernama {nama} tingkat {jenjang_kelas}.
                Keluarkan persis 3 bagian berikut:

                ===RINGKASAN_MATERI===
                (Tulis penjelasan ringkasan materi dengan gaya bahasa {gaya} menyapa {nama})

                ===KUIS_INTERAKTIF===
                (Berikan 1-2 soal kuis latihan seru untuk menguji pemahaman {nama})

                ===MASTER_PROMPT_VIDEO===
                (Tulis SATU prompt komprehensif dalam BAHASA INGGRIS untuk mesin AI Video Generator. 
                Prompt ini WAJIB berisi instruksi ini: "Create an educational video explaining [ISI KONSEP MATERINYA]. Visual style: 3-color doodle animation (white background, dark blue outlines, and one bright accent color like orange or yellow), dynamic drawing motion like a teacher writing on a whiteboard. Audio style: AI generated voiceover in Indonesian language that is friendly and suited for {jenjang_kelas} students, starting with 'Halo {nama}!', explaining the concept naturally and perfectly synced with the visual doodles.")
                """
                
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[ux_bridge_prompt, image]
                )
                full_text = response.text
                
                # CARA PARSING BARU YANG 100% AMAN (Bebas error baris terpotong)
                ringkasan = "Materi telah dipahami."
                kuis = "Ayo belajar!"
                video_prompt = "Create an educational doodle animation."
                
                if "===RINGKASAN_MATERI===" in full_text:
                    match_ringkasan = re.search(r'===RINGKASAN_MATERI===(.*?)(?====KUIS_INTERAKTIF===|$)', full_text, re.DOTALL)
                    if match_ringkasan: ringkasan = match_ringkasan.group(1).strip()
                    
                if "===KUIS_INTERAKTIF===" in full_text:
                    match_kuis = re.search(r'===KUIS_INTERAKTIF===(.*?)(?====MASTER_PROMPT_VIDEO===|$)', full_text, re.DOTALL)
                    if match_kuis: kuis = match_kuis.group(1).strip()
                    
                if "===MASTER_PROMPT_VIDEO===" in full_text:
                    match_prompt = re.search(r'===MASTER_PROMPT_VIDEO===(.*)', full_text, re.DOTALL)
                    if match_prompt: video_prompt = match_prompt.group(1).strip()

                # Tampilkan ke UI
                st.markdown("---")
                st.markdown(f"## 📚 Rangkuman Materi ({mapel})")
                st.markdown(ringkasan)
                
                st.markdown("---")
                st.markdown(f"## 🏆 Kuis Tantangan untuk {nama}!")
                st.markdown(kuis)
                
            except Exception as e:
                st.error(f"Terjadi kesalahan saat AI membaca materi: {e}")
                st.stop()
                
        # TAHAP 2: GENERATE VIDEO (VISUAL & AUDIO OTOMATIS)
        with st.spinner("2. Merender Video Animasi Doodle 3 Warna... (Ini memakan waktu sekitar 1-2 menit)"):
            try:
                operation = client.models.generate_videos(
                    model="veo-3.1-fast-generate-preview",
                    prompt=video_prompt,
                    config=types.GenerateVideosConfig(
                        resolution="720p"
                    )
                )
                
                while not operation.done:
                    time.sleep(5)
                    operation = client.operations.get(operation)
                
                vid_result = operation.result.generated_videos[0]
                file_video_final = "hasil_animasi_doodle.mp4"
                client.files.download(file=vid_result.video)
                vid_result.video.save(file_video_final)
                
                st.markdown("---")
                st.markdown(f"## 🎬 Video Pembelajaran Khusus {nama}:")
                st.video(file_video_final)
                
            except Exception as e:
                st.error(f"Terjadi kendala pada mesin AI Video Generator: {e}")
                
    else:
        st.warning("Silakan unggah foto halaman bukunya terlebih dahulu!")
