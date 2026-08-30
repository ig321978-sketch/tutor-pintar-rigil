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

# --- FUNGSI PEMBUAT SUARA MANUSIA PREMIUM (DINAMIS) ---
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
if 'ringkasan' not in st.session_state:
    st.session_state.ringkasan = ""
if 'file_suara' not in st.session_state:
    st.session_state.file_suara = "audio_guru.mp3"
if 'daftar_kuis' not in st.session_state:
    st.session_state.daftar_kuis = []

# --- ANTARMUKA PENGGUNA (UI) UTAMA ---
st.set_page_config(page_title="Tutor Pintar Rigil", page_icon="🎓", layout="centered")

st.title("🎓 Tutor Pintar Rigil (Premium AI Voice)")
st.write("Belajar asik dengan asisten suara AI yang beradaptasi dengan tingkat kelasmu!")

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
            
            # LOGIKA ADAPTASI LEVEL KELAS
            if "SD" in jenjang_kelas:
                karakter_suara = "shimmer" # Ceria & Terang
                gaya_naskah = f"Tulis naskah lisan KHUSUS ANAK {jenjang_kelas}. Mengajarlah dengan nada SANGAT CERIA, penuh semangat, dan ekspresif layaknya kakak pembimbing. Gunakan banyak kata seru santai seperti 'Wah!', 'Yuk!', 'Hebat!'. Sapa {nama} dengan hangat. Hindari bahasa baku/formal. Kalimat harus pendek-pendek."
            elif "SMP" in jenjang_kelas:
                karakter_suara = "nova" # Kasual & Bersahabat
                gaya_naskah = f"Tulis naskah lisan untuk remaja {jenjang_kelas}. Mengajarlah dengan gaya asik, komunikatif, dan kasual layaknya mentor. Sapa {nama} dengan santai. Gunakan analogi yang relevan dengan dunia remaja. Gunakan bahasa semi-formal yang luwes dan tidak menggurui."
            else:
                karakter_suara = "alloy" # Profesional & Tenang
                gaya_naskah = f"Tulis naskah lisan untuk siswa {jenjang_kelas}. Mengajarlah dengan gaya profesional, logis, terstruktur, namun tetap memotivasi. Sapa {nama} dengan sopan. Gunakan bahasa formal akademis yang mudah dipahami. Dorong pemikiran analitis."

            maksimal_coba = 3
            for percobaan in range(maksimal_coba):
                try:
                    ux_bridge_prompt = f"""
                    Kamu adalah Tutor AI ahli {mapel} yang sangat sabar. Baca materi dari foto ini untuk siswa {jenjang_kelas} bernama {nama}.
                    Keluarkan persis 3 bagian berikut dengan format pembatas yang ketat:

                    ===RINGKASAN===
                    (Tulis catatan visual materi ini. Gunakan format poin, teks tebal, dan emoji yang relevan agar menarik dibaca di layar.)

                    ===NASKAH_SUARA===
                    ({gaya_naskah} Jangan gunakan simbol matematika rumit, eja semua angka dengan jelas agar mudah dibaca oleh sistem teks-ke-suara.)

                    ===KUIS===
                    (Buatlah 3 soal pilihan ganda dari materi. Wajib gunakan format ini per baris, dipisah dengan 3 garis lurus HANYA:)
                    Pertanyaan 1?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
                    Pertanyaan 2?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
                    Pertanyaan 3?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
                    (PENTING: Bagian paling akhir HANYA boleh berisi TEKS JAWABAN BENAR yang persis sama dengan isi salah satu opsi, jangan gunakan huruf abjad A/B/C)
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
                            # Memasukkan pilihan suara dinamis ke dalam fungsi TTS
                            buat_suara_premium(naskah_bersih, st.session_state.file_suara, karakter_suara)
                    
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
    st.markdown(f"## 🏆 Latihan Soal untuk {nama}!")
    
    if st.session_state.daftar_kuis:
        with st.form("kuis_interaktif"):
            jawaban_user = []
            for i, q in enumerate(st.session_state.daftar_kuis):
                jwb = st.radio(f"**{i+1}. {q['soal']}**", q['opsi'], key=f"soal_{i}")
                jawaban_user.append(jwb)
            
            cek_jawaban = st.form_submit_button("Cek Jawaban ✔️")
            
            if cek_jawaban:
                skor = 0
                for i, q in enumerate(st.session_state.daftar_kuis):
                    if jawaban_user[i] == q['kunci']:
                        skor += 1
                
                if skor == len(st.session_state.daftar_kuis):
                    st.success(f"Luar biasa! Benar {skor} dari {len(st.session_state.daftar_kuis)} soal. Kamu dapat bintang! ⭐⭐⭐")
                    st.balloons()
                elif skor > 0:
                    st.warning(f"Wah, kamu menjawab {skor} soal dengan benar dari total {len(st.session_state.daftar_kuis)}. Sedikit lagi! Dengarkan ulang audionya ya.")
                else:
                    st.error("Belum ada jawaban yang tepat nih. Yuk coba dengarkan penjelasan guru lagi!")
