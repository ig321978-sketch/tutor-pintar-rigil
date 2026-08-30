import streamlit as st
import time
import re
from PIL import Image
from google import genai
from google.genai import types

# --- KONFIGURASI KUNCI API ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "MASUKKAN_API_KEY_ANDA_DI_SINI"

client = genai.Client(api_key=API_KEY)

# --- ANTARMUKA PENGGUNA (UI) ---
st.set_page_config(page_title="Tutor Pintar Rigil", page_icon="🎓", layout="centered")

st.title("🎓 Tutor Pintar Rigil (Edisi Premium)")
st.write("Aplikasi AI yang membaca buku pelajaran dan merender video animasi edukasi secara otomatis!")

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
            st.info("✨ **Halo " + nama + "!** AI sedang membaca materi dan menyiapkan animasi doodle 3 warna khusus untukmu...")
            
        # TAHAP 1: PEMAHAMAN AI (DENGAN SMART RETRY)
        with st.spinner("1. Menganalisis materi buku (Backend)..."):
            maksimal_coba = 3
            berhasil_baca = False
            video_prompt = ""
            
            for percobaan in range(maksimal_coba):
                try:
                    if "SD" in jenjang_kelas:
                        gaya = "ramah, ceria, dengan analogi sehari-hari yang seru."
                    elif "SMP" in jenjang_kelas:
                        gaya = "komunikatif, asik, dan relevan dengan dunia remaja."
                    else:
                        gaya = "profesional, logis, terstruktur, dan akademis."

                    # UX Bridge Prompt: Digabung secara linear agar bebas error saat disalin
                    ux_bridge_prompt = (
                        "Kamu adalah Tutor AI cerdas. Baca dan pahami foto halaman buku " + mapel + " ini untuk siswa bernama " + nama + " tingkat " + jenjang_kelas + ".\n"
                        "Keluarkan persis 3 bagian berikut:\n\n"
                        "===RINGKASAN_MATERI===\n(Tulis rangkuman materi dengan gaya " + gaya + " menyapa " + nama + ")\n\n"
                        "===KUIS_INTERAKTIF===\n(Berikan 1 soal kuis latihan. Beri pujian sebagai hadiah jika berhasil menjawab)\n\n"
                        "===MASTER_PROMPT_VIDEO===\n(Tulis SATU instruksi dalam BAHASA INGGRIS untuk AI Video Generator. Isinya harus wajib format ini: 'Create a high-quality educational video explaining [ISI MATERI]. Visual style: 3-color doodle animation (white background, dark blue outlines, and bright orange accents), dynamic drawing motion. Audio style: AI generated voiceover in Indonesian language perfectly synced with the visuals, starting with Halo " + nama + "!')"
                    )
                    
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=[ux_bridge_prompt, image]
                    )
                    full_text = response.text
                    
                    # Parsing teks aman dengan Regex
                    ringkasan = "Materi telah dipahami."
                    kuis = "Ayo belajar!"
                    video_prompt = "Create a high quality educational doodle animation."
                    
                    if "===RINGKASAN_MATERI===" in full_text:
                        match_r = re.search(r'===RINGKASAN_MATERI===(.*?)(?====KUIS_INTERAKTIF===|$)', full_text, re.DOTALL)
                        if match_r: ringkasan = match_r.group(1).strip()
                        
                    if "===KUIS_INTERAKTIF===" in full_text:
                        match_k = re.search(r'===KUIS_INTERAKTIF===(.*?)(?====MASTER_PROMPT_VIDEO===|$)', full_text, re.DOTALL)
                        if match_k: kuis = match_k.group(1).strip()
                        
                    if "===MASTER_PROMPT_VIDEO===" in full_text:
                        match_p = re.search(r'===MASTER_PROMPT_VIDEO===(.*)', full_text, re.DOTALL)
                        if match_p: video_prompt = match_p.group(1).strip()

                    # Render teks ke layar pengguna
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
                        st.warning("Server sibuk. Mengulang otomatis dalam 5 detik... (" + str(percobaan + 1) + "/" + str(maksimal_coba) + ")")
                        time.sleep(5)
                    else:
                        st.error("Gagal saat menganalisis materi: " + str(e))
                        st.stop()
                        
        # TAHAP 2: MESIN AI TEXT-TO-VIDEO PREMIUM
        if berhasil_baca:
            with st.spinner("2. Merender Video Animasi AI Profesional... (Bisa memakan waktu 1-3 menit)"):
                try:
                    operation = client.models.generate_videos(
                        model="veo-3.1-fast-generate-preview",
                        prompt=video_prompt,
                        config=types.GenerateVideosConfig(
                            resolution="720p"
                        )
                    )
                    
                    # Polling status pembuatan video di server cloud Google
                    while not operation.done:
                        time.sleep(5)
                        operation = client.operations.get(operation)
                    
                    vid_result = operation.result.generated_videos[0]
                    file_video_final = "hasil_animasi_premium.mp4"
                    client.files.download(file=vid_result.video)
                    vid_result.video.save(file_video_final)
                    
                    st.markdown("---")
                    st.markdown("## 🎬 Video Animasi Profesional:")
                    st.video(file_video_final)
                    
                except Exception as e:
                    st.error("Mesin pembuat video AI menemui kendala: " + str(e))
                
    else:
        st.warning("Jangan lupa unggah foto halaman bukunya dulu ya!")
