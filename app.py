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
        input=teks,
        speed=0.5  # <-- Kecepatan dilambatkan 50% agar sangat santai dan mudah diikuti
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
st.write("Belajar asik dengan asisten suara AI yang 100% natural, membaca materi secara tuntas!")

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
        
        # Menghapus memori kuis lama setiap kali mengunggah materi baru
        for key in list(st.session_state.keys()):
            if key.startswith('status_soal_'):
                del st.session_state[key]
        
        with st.spinner("AI sedang menyiapkan penjelasan detail dan merekam suara..."):
            
            # Pengaturan karakter suara 
            if "SD" in jenjang_kelas:
                karakter_suara = "nova" # Natural, sabar, seperti guru pendamping anak
            elif "SMP" in jenjang_kelas:
                karakter_suara = "echo" # Santai, sedikit maskulin
            else:
                karakter_suara = "alloy" # Profesional dan berwibawa

            maksimal_coba = 3
            for percobaan in range(maksimal_coba):
                try:
                    # PROMPT: Naskah Layar Profesional vs Naskah Suara Penuh Ejaan
                    ux_bridge_prompt = (
                        "Kamu adalah Tutor AI ahli " + mapel + " yang super sabar. Baca materi dari foto ini untuk siswa " + jenjang_kelas + " bernama " + nama + ".\n"
                        "Keluarkan persis 3 bagian berikut dengan format pembatas yang ketat:\n\n"
                        "===NASKAH_LAYAR===\n"
                        "(Tulis penjelasan materi SANGAT DETAIL. Jika ada 'Cara 1', 'Cara 2', jelaskan SEMUANYA beserta contoh perhitungan angkanya secara urut. "
                        "FORMAT: Profesional layaknya materi pelajaran. Gunakan angka asli dan simbol matematika (misal: 35 x 2 = 70). Jangan dieja dengan huruf. Sapa " + nama + " di awal kalimat.)\n\n"
                        "===NASKAH_SUARA===\n"
                        "(Tulis versi lisan dari NASKAH_LAYAR di atas. Kalimatnya HARUS 100% sama dan sinkron dengan naskah layar, TETAPI semua angka dan simbol matematika WAJIB DIEJA dengan huruf (misal: 'tiga puluh lima dikali dua sama dengan tujuh puluh'). Ini agar mesin suara dapat membacanya dengan tepat dan tidak tersendat.)\n\n"
                        "===KUIS===\n"
                        "(Buatlah 3 soal pilihan ganda dari materi. Wajib gunakan format ini per baris, dipisah dengan 3 garis lurus HANYA:)\n"
                        "Pertanyaan 1?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar\n"
                        "Pertanyaan 2?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar\n"
                        "Pertanyaan 3?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar\n"
                        "(PENTING: Bagian akhir HANYA boleh berisi TEKS JAWABAN BENAR yang persis sama dengan isi salah satu opsi)"
                    )
                    
                    response = client_gemini.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=[ux_bridge_prompt, image]
                    )
                    full_text = response.text
                    
                    # Parsing Naskah Layar
                    if "===NASKAH_LAYAR===" in full_text:
                        match_l = re.search(r'===NASKAH_LAYAR===(.*?)(?====NASKAH_SUARA===|$)', full_text, re.DOTALL)
                        if match_l: 
                            st.session_state.naskah_layar = match_l.group(1).strip()
                    
                    # Parsing Naskah Suara & Generate Audio
                    if "===NASKAH_SUARA===" in full_text:
                        match_s = re.search(r'===NASKAH_SUARA===(.*?)(?====KUIS===|$)', full_text, re.DOTALL)
                        if match_s: 
                            naskah_suara = match_s.group(1).strip()
                            naskah_bersih = re.sub(r'[*#_`>-]', '', naskah_suara)
                            buat_suara_premium(naskah_bersih, st.session_state.file_suara, karakter_suara)
                    
                    # Parsing Kuis
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
    st.info("💡 Putar suara di bawah ini, lalu ikuti teksnya. Suara akan membaca teks ini dengan detail!")
    
    st.audio(st.session_state.file_suara, format="audio/mp3")
    st.markdown(st.session_state.naskah_layar)
    
    st.markdown("---")
    st.markdown(f"## 🏆 Latihan Soal untuk {nama}!")
    
    if st.session_state.daftar_kuis:
        for i, q in enumerate(st.session_state.daftar_kuis):
            st.markdown(f"**{i+1}. {q['soal']}**")
            
            # index=None agar lingkaran merah (radio) kosong saat awal dimuat
            jawaban_user = st.radio("Pilih jawaban:", q['opsi'], key=f"soal_radio_{i}", index=None, label_visibility="collapsed")
            
            # Tombol Cek Jawaban (tanpa checklist)
            if st.button(f"Cek Jawaban Soal {i+1}", key=f"btn_cek_{i}"):
                if jawaban_user == q['kunci']:
                    st.session_state[f"status_soal_{i}"] = "benar"
                    if i == len(st.session_state.daftar_kuis) - 1:
                        st.balloons() # Munculkan balon jika soal terakhir diklik benar
                elif jawaban_user is None:
                    st.session_state[f"status_soal_{i}"] = "kosong"
                else:
                    st.session_state[f"status_soal_{i}"] = "salah"
            
            # Menampilkan hasil evaluasi HANYA jika tombol sudah pernah ditekan, dan tidak akan hilang
            status_jawaban = st.session_state.get(f"status_soal_{i}")
            if status_jawaban == "benar":
                st.success("Tepat sekali! Hebat! ⭐")
            elif status_jawaban == "kosong":
                st.warning("Kamu belum memilih jawaban, klik salah satu bulatan dulu ya.")
            elif status_jawaban == "salah":
                st.error("Wah, masih kurang tepat. Coba hitung pelan-pelan lagi ya!")
            
            st.write("") # Memberi jarak antar soal
