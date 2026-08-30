import streamlit as st
import time
from PIL import Image
from google import genai
from google.genai import types
import re 

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
            
        # TAHAP 1: PEMAHAMAN AI & PENYUSUNAN UX BRIDGE PROMPT (DENGAN SMART RETRY)
        with st.spinner("1. Memahami materi dan merumuskan konsep video (Backend)..."):
            maksimal_coba = 3
            berhasil_baca = False
            video_prompt = ""
            
            for percobaan in range(maksimal_coba):
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
