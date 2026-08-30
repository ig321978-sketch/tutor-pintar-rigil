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
def buat_suara_premium(teks, nama_file):
    if not client_openai:
        raise Exception("API Key OpenAI belum dikonfigurasi di Secrets!")
    
    response = client_openai.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=teks
    )
    response.stream_to_file(nama_file)

# --- INISIALISASI SESSION STATE ---
if 'berhasil_baca' not in st.session_state:
    st.session_state.berhasil_baca = False
if 'ringkasan' not in st.session_state:
    st.session_state.ringkasan = ""
if 'file_suara' not in st.session_state:
    st.session_state.file_suara = "audio_guru.mp3"
if 'kuis_soal' not in st.session_state:
    st.session_state.kuis_soal = ""
if 'kuis_opsi' not in st.session_state:
    st.session_state.kuis_opsi = []
if 'kuis_kunci' not in st.session_state:
    st.session_state.kuis_kunci = ""

# --- ANTARMUKA PENGGUNA (UI) UTAMA ---
st.set_page_config(page_title="Tutor Pintar Rigil", page_icon="🎓", layout="centered")

st.title("🎓 Tutor Pintar Rigil (Premium AI Voice)")
st.write("Belajar asik dengan asisten suara AI yang 100% natural layaknya manusia!")

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
        
        with st.spinner("AI sedang meracik materi dan merekam suara guru..."):
            maksimal_coba = 3
            for percobaan in range(maksimal_coba):
                try:
                    ux_bridge_prompt = f"""
                    Kamu adalah Tutor AI ahli {mapel} yang sangat sabar. Baca materi dari foto ini untuk siswa {jenjang_kelas} bernama {nama}.
                    Keluarkan persis 3 bagian berikut dengan format pembatas yang ketat:

                    ===RINGKASAN===
                    (Tulis catatan visual materi ini. Gunakan format poin, teks tebal, dan emoji yang relevan agar menarik dibaca di layar.)

                    ===NASKAH_SUARA===
                    (Tulis naskah lisan. Mengajarlah secara detail, interaktif, dan sangat ramah layaknya guru manusia berbicara kepada {nama}. Gunakan bahasa sehari-hari yang luwes. Jangan gunakan simbol matematika rumit, eja semua angka dengan jelas.)

                    ===KUIS===
                    (Buat 1 soal pilihan ganda dari materi. Wajib gunakan format ini dipisah dengan 3 garis lurus HANYA:)
                    Pertanyaan soal?|||Opsi A|||Opsi B|||Opsi C|||A
                    """
                    
                    response = client_gemini.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=[ux_bridge_prompt, image]
                    )
                    full_text = response.text
                    
                    if "===RINGKASAN===" in full_text:
                        match_r = re.search(r'===RINGKASAN===(.*?)(?====NASKAH_SUARA===|$)', full_text, re.DOTALL)
                        if match_r: st.session_state.ringkasan = match_r.group(1).strip()
                    
                    if "===NASKAH_SUARA===" in full_text:
                        match_n = re.search(r'===NASKAH_SUARA===(.*?)(?====KUIS===|$)', full_text, re.DOTALL)
                        if match_n: 
                            naskah_mentah = match_n.group(1).strip()
                            naskah_bersih = re.sub(r'[*#_`>-]', '', naskah_mentah)
                            buat_suara_premium(naskah_bersih, st.session_state.file_suara)
                    
                    if "===KUIS===" in full_text:
                        match_k = re.search(r'===KUIS===(.*)', full_text, re.DOTALL)
                        if match_k: 
                            kuis_raw = match_k.group(1).strip()
                            parts = kuis_raw.split("|||")
                            if len(parts) >= 5:
                                st.session_state.kuis_soal = parts[0].strip()
                                st.session_state.kuis_opsi = [parts[1].strip(), parts[2].strip(), parts[3].strip()]
                                st.session_state.kuis_kunci = parts[4].strip()
                    
                    st.session_state.berhasil_baca = True
                    break # Jika sukses, keluar dari loop coba lagi
                    
                except Exception as e:
                    if "503" in str(e) and percobaan < maksimal_coba - 1:
                        st.warning(f"Jalur ke server Google sedang padat. Mencoba otomatis dalam 5 detik... ({percobaan + 1}/{maksimal_coba})")
                        time.sleep(5)
                    else:
                        st.error(f"Gagal memproses modul: {e}")
                        break
    else:
        st.warning("Silakan unggah foto bukunya dulu ya!")

# --- MENAMPILKAN MODUL BELAJAR INTERAKTIF ---
if st.session_state.berhasil_baca:
    st.markdown("---")
    st.markdown(f"## 📚 Catatan Pintar ({mapel})")
    st.markdown(st.session_state.ringkasan)
    
    st.markdown("---")
    st.markdown("## 🎧 Dengarkan Penjelasan Guru")
    st.info("💡 Klik tombol Play di bawah ini untuk mendengarkan guru menjelaskan materi!")
    st.audio(st.session_state.file_suara, format="audio/mp3")
    
    st.markdown("---")
    st.markdown(f"## 🏆 Kuis untuk {nama}!")
    
    with st.form("kuis_interaktif"):
        st.write(st.session_state.kuis_soal)
        pilihan = st.radio("Pilih jawaban yang paling tepat:", st.session_state.kuis_opsi)
        cek_jawaban = st.form_submit_button("Cek Jawaban ✔️")
        
        if cek_jawaban:
            if st.session_state.kuis_kunci in pilihan:
                st.success("Yeay! Jawabanmu TEPAT! Ini hadiah bintang untukmu! ⭐⭐⭐")
                st.balloons()
            else:
                st.error("Wah, hampir tepat. Coba dengarkan lagi audionya ya, kamu pasti bisa!")
