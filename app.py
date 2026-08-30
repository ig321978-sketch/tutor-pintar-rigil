import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import re

# --- KONFIGURASI API (PENTING!) ---
# Cara terbaik adalah menggunakan secrets management di Streamlit.
# Silakan ikuti panduan di sidebar aplikasi untuk mengaturnya.
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    st.error("Kunci API Google tidak ditemukan dalam rahasia Streamlit Anda. Harap konfigurasikan `.streamlit/secrets.toml`.")
    st.stop()

# Konfigurasi library AI
genai.configure(api_key=GOOGLE_API_KEY)

# Pilih model yang tepat untuk analisis gambar
model_vision = genai.GenerativeModel('gemini-pro-vision')

# --- FUNGSI UTAMA ---
def racik_presentasi_dari_gambar(prompt_text, image_obj):
    """Memanggil model AI dengan gambar dan prompt untuk membuat draf presentasi."""
    try:
        # Memanggil model AI
        response = model_vision.generate_content([prompt_text, image_obj])
        return response.text, None
    except Exception as e:
        # Menangani kesalahan server
        error_message = str(e)
        if "503" in error_message or "UNAVAILABLE" in error_message.upper():
            return None, "Server AI sedang sibuk (503 UNAVAILABLE). Silakan coba lagi nanti."
        else:
            return None, f"Terjadi kesalahan yang tidak terduga: {error_message}"

# --- ANTARMUKA PENGGUNA (UI) ---
st.title("Aplikasi Pembuat Presentasi Buku Pelajaran Cerdas")
st.write("Unggah gambar halaman buku pelajaran Anda, dan AI akan meracik draf presentasi yang rapi.")

# Komponen unggahan file
uploaded_file = st.file_uploader("Pilih gambar halaman buku pelajaran...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Memuat dan menampilkan gambar
    image = Image.open(uploaded_file)
    st.image(image, caption="Buku Pelajaran Asli", use_column_width=True)

    # Tombol untuk memicu analisis
    if st.button("Racik Presentasi"):
        # Menyimpan status tombol
        with st.spinner("Meracik presentasi dari gambar..."):
            
            # ==============================================================================
            # **BERIKUT ADALAH KODE YANG DIPERBAIKI UNTUK SYNTAXERROR**
            #
            # Masalah sebelumnya (penyebab EOL error):
            # prompt = """  <-- Dimulai dengan kutip tiga, tapi lupa ditutup di baris ini
            # Pola yang benar untuk string multi-baris (tiga tanda kutip):
            
            prompt = """
            Analisislah gambar halaman buku pelajaran ini secara mendalam.
            
            Berdasarkan konten tersebut, buatlah draf presentasi untuk menjelaskan topik tersebut kepada siswa.
            Presentasi harus mencakup:
            1. Judul Slide yang Menarik untuk Topik Ini.
            2. Poin-poin Utama (bullet points) yang menjelaskan konsep kunci secara jelas.
            3. Contoh-contoh spesifik yang disebutkan dalam teks buku.
            4. Ringkasan singkat untuk slide penutup.
            
            Berikan output dalam format Markdown yang rapi dengan header slide yang jelas.
            """
            
            # **Tanda kutip penutup tiga (") di atas sangat penting.**
            # Ini memberitahu Python bahwa string teks multi-baris telah berakhir.
            # Lupa memberikan tanda penutup ini adalah penyebab paling umum dari SyntaxError yang Anda alami.
            # ==============================================================================

            # Memanggil fungsi analisis
            presentation_text, error_info = racik_presentasi_dari_gambar(prompt, image)
            
            # Menampilkan hasil
            if presentation_text:
                st.subheader("Draf Presentasi yang Diracik:")
                st.markdown(presentation_text)
            
            # ==============================================================================
            # **BERIKUT ADALAH PENANGANAN UNTUK KESALAHAN 503 UNAVAILABLE**
            #
            # Kode ini menangkap kesalahan server AI yang terlihat dalam gambar Anda
            # dan menampilkan pesan yang ramah kepada pengguna.
            # ==============================================================================
            elif error_info:
                st.error(error_info)

# Instruksi penyiapan di sidebar
st.sidebar.title("Cara Menyiapkan Kunci API")
st.sidebar.markdown("""
Agar aplikasi ini berfungsi, Anda memerlukan Google AI API Key Anda sendiri.

1.  Dapatkan Kunci API Anda di Google AI Studio.
2.  Di folder proyek Anda, buat folder bernama `.streamlit`.
3.  Di dalam folder `.streamlit`, buat file bernama `secrets.toml`.
4.  Tambahkan baris berikut ke dalam file `secrets.toml`:
    
    `GOOGLE_API_KEY = "MASUKKAN_KUNCI_API_ANDA_DI_SINI"`
    
    *Ganti teks di dalam tanda kutip dengan kunci API Anda yang sebenarnya.*
5.  Jalankan aplikasi ini: `streamlit run app.py`
""")
