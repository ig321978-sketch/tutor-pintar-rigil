import streamlit as st
import re
import time
from PIL import Image
from google import genai
from openai import OpenAI

# --- KONFIGURASI KUNCI API ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "MASUKKAN_GEMINI_API_KEY_ANDA_DI_SINI"

try:
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except Exception:
    OPENAI_KEY = "MASUKKAN_OPENAI_API_KEY_ANDA_DI_SINI"

client_gemini = genai.Client(api_key=API_KEY)

if OPENAI_KEY and OPENAI_KEY != "MASUKKAN_OPENAI_API_KEY_ANDA_DI_SINI":
    client_openai = OpenAI(api_key=OPENAI_KEY)
else:
    client_openai = None

# --- FUNGSI PEMBUAT SUARA MANUSIA PREMIUM (OPENAI) ---
def buat_suara_premium(teks, nama_file, pilihan_suara):
    if not client_openai:
        raise Exception("API Key OpenAI belum dikonfigurasi di Secrets!")
    
    response = client_openai.audio.speech.create(
        model="tts-1",
        voice=pilihan_suara,
        input=teks
    )
    response.stream_to_file(nama_file)

# --- INISIALISASI SESSION STATE ---
if 'berhasil_baca' not in st.session_state:
    st.session_state.berhasil_baca = False
if 'naskah_layar' not in st.session_state:
    st.session_state.naskah_layar = ""
if 'file_suara' not in st.session_state:
    st.session_state.file_suara = "audio_guru.mp3"
if 'daftar_kuis' not in st.session_state:
    st.session_state.daftar_kuis = []

# --- ANTARMUKA PENGGUNA (UI) UTAMA ---
st.set_page_config(page_title="Tutor Pintar Rigil", page_icon="🎓", layout="centered")

st.title("🎓 Tutor Pintar Rigil")
st.write("Belajar asik dengan asisten suara AI yang 100% natural, membaca teks kata demi kata!")

# --- FORMULIR UNGGAH BUKU ---
with st.form("user_form"):
    nama = st.text_input("Nama Siswa:", "Rigil")
    jenjang_kelas = st.selectbox("Jenjang & Kelas:", [
        "SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6",
        "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9",
        "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"
    ], index=2)
    mapel = st.text_input("Mata Pelajaran:", "Matematika")
    uploaded_file = st.file_uploader("Foto Halaman Buku Pelajaran:", type=["jpg", "jpeg", "png"])
    
    btn_analisis = st.form_submit_button(label="Mulai Belajar! 🚀")

# --- PROSES ANALISIS AI (DENGAN SMART RETRY) ---
if btn_analisis:
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Buku Pelajaran Asli", use_container_width=True)
        
        with st.spinner("AI sedang menyiapkan penjelasan detail dan merekam suara..."):
            
            # Pengaturan karakter suara (SD menggunakan "nova" yang natural, hangat dan keibuan/kebapakan)
            if "SD" in jenjang_kelas:
                karakter_suara = "nova" 
            elif "SMP" in jenjang_kelas:
                karakter_suara = "echo" 
            else:
                karakter_suara = "alloy"

            maksimal_coba = 3
            for percobaan in range(maksimal_coba):
                try:
                    # PROMPT DIPERBARUI: Naskah Visual = Naskah Suara (100% Sama) & Sangat Detail
                    ux_bridge_prompt = f"""
                    Kamu adalah Tutor AI ahli {mapel} yang super sabar. Baca materi dari foto ini untuk siswa {jenjang_kelas} bernama {nama}.
                    Keluarkan persis 2 bagian berikut dengan format pembatas yang ketat:

                    ===NASKAH_PENJELASAN===
                    (Tuliskan SATU naskah utuh yang akan dibaca oleh anak di layar SEKALIGUS dibacakan oleh suara AI. 
                    Syarat Mutlak Naskah:
                    1. Sapa {nama} dengan hangat dan natural.
                    2. Jelaskan materi dengan SANGAT DETAIL. Jika di buku ada "Cara 1", "Cara 2", dst., JELASKAN SEMUANYA satu per satu beserta CONTOH ANGKA dan urutan perhitungannya. JANGAN ada yang dilewatkan.
                    3. Karena teks ini juga akan dibaca oleh robot suara, EJA DENGAN KATA-KATA untuk setiap angka atau simbol matematika (contoh: tulis "dua puluh satu dikali empat" BUKAN "21 x 4").
                    4. Gunakan gaya bahasa lisan yang ramah, jelas, dan paragraf yang rapi.)

                    ===KUIS===
                    (Buatlah 3 soal pilihan ganda dari materi. Wajib gunakan format ini per baris, dipisah dengan 3 garis lurus HANYA:)
                    Pertanyaan 1?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
                    Pertanyaan 2?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
                    Pertanyaan 3?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
                    (PENTING: Bagian akhir HANYA boleh berisi TEKS JAWABAN BENAR yang persis sama dengan isi salah satu opsi)
                    """
                    
                    response = client_gemini.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=[ux_bridge_prompt, image]
                    )
                    full_text = response.text
                    
                    # Memecah dan Memproses Teks
                    if "===NASKAH_PENJELASAN===" in full_text:
                        match_n = re.search(r'===NASKAH_PENJELASAN===(.*?)(?====KUIS===|$)', full_text, re.DOTALL)
                        if match_n: 
                            naskah_mentah = match_n.group(1).strip()
                            st.session_state.naskah_layar = naskah_mentah
                            
                            # Membersihkan sedikit simbol markdown (*, #) agar suara TTS tidak tersendat, 
                            # tapi struktur teks (kata-kata) tetap 100% persis dengan di layar.
                            naskah_suara = re.sub(r'[*#_`>-]', '', naskah_mentah)
                            buat_suara_premium(naskah_suara, st.session_state.file_suara, karakter_suara)
                    
                    if "===KUIS===" in full_text:
                        match_k = re.search(r'===KUIS===(.*)', full_text, re.DOTALL)
                        if match_k: 
                            kuis_raw = match_k.group(1).strip()
                            lines = [line for line in kuis_raw.split('\n') if '|||' in line]
                            parsed_kuis = []
                            for line in lines:
                                parts = line.split("|||")
                                if len(parts) >= 5:
                                    parsed_kuis.append({
                                        "soal": parts[0].strip(),
                                        "opsi": [parts[1].strip(), parts[2].strip(), parts[3].strip()],
                                        "kunci": parts[4].strip()
                                    })
                            st.session_state.daftar_kuis = parsed_kuis
                    
                    st.session_state.berhasil_baca = True
                    break 
                    
                except Exception as e:
                    if "503" in str(e) and percobaan < maksimal_coba - 1:
                        st.warning(f"Sistem Google sedang padat. Mencoba lagi dalam 5 detik... ({percobaan + 1}/{maksimal_coba})")
                        time.sleep(5)
                    else:
                        st.error(f"Gagal memproses materi: {e}")
                        break
    else:
        st.warning("Silakan unggah foto bukunya dulu ya!")

# --- MENAMPILKAN MODUL BELAJAR INTERAKTIF ---
if st.session_state.berhasil_baca:
    st.markdown("---")
    st.markdown("## 🎧 Dengarkan & Baca Penjelasan Guru")
    st.info("💡 Putar suara di bawah ini, lalu ikuti teksnya. Teks dan suara 100% sama!")
    
    # Audio dan Teks diletakkan berdekatan agar mudah diikuti
    st.audio(st.session_state.file_suara, format="audio/mp3")
    st.markdown(st.session_state.naskah_layar)
    
    st.markdown("---")
    st.markdown(f"## 🏆 Latihan Soal untuk {nama}!")
    
    # Kuis yang dipisah satu per satu (Tombol Radio kosong tanpa pilihan default)
    if st.session_state.daftar_kuis:
        for i, q in enumerate(st.session_state.daftar_kuis):
            st.markdown(f"**{i+1}. {q['soal']}**")
            
            # index=None menonaktifkan lingkaran merah bawaan
            jawaban_user = st.radio("Pilih jawaban:", q['opsi'], key=f"soal_{i}", index=None, label_visibility="collapsed")
            
            # Tombol cek satuan tanpa checklist
            if st.button(f"Cek Jawaban Soal {i+1}", key=f"btn_cek_{i}"):
                if jawaban_user == q['kunci']:
                    st.success("Tepat sekali! Hebat! ⭐")
                    if i == len(st.session_state.daftar_kuis) - 1:
                        st.balloons() # Balon keluar jika menjawab soal terakhir dengan benar
                elif jawaban_user is None:
                    st.warning("Kamu belum memilih jawaban, klik salah satu bulatan dulu ya.")
                else:
                    st.error("Wah, masih kurang tepat. Coba hitung pelan-pelan lagi ya!")
            
            st.write("") # Memberi jarak antar soal
