import streamlit as st
import re
import requests
import base64
from PIL import Image
from google import genai

# --- KONFIGURASI KUNCI API ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "MASUKKAN_API_KEY_ANDA_DI_SINI"

client = genai.Client(api_key=API_KEY)

# --- FUNGSI PEMBUAT SUARA GOOGLE PREMIUM (NEURAL2) ---
def buat_suara_google(teks, nama_file, kunci_api):
    url = "https://texttospeech.googleapis.com/v1/text:synthesize?key=" + kunci_api
    headers = {"Content-Type": "application/json"}
    
    data = {
        "input": {"text": teks},
        "voice": {"languageCode": "id-ID", "name": "id-ID-Neural2-D"},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": 0.95} 
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        audio_content = response.json()["audioContent"]
        with open(nama_file, "wb") as f:
            f.write(base64.b64decode(audio_content))
    else:
        raise Exception("Gagal membuat suara Google: " + response.text)

# --- INISIALISASI SESSION STATE ---
if 'berhasil_baca' not in st.session_state:
    st.session_state.berhasil_baca = False
if 'slide_materi' not in st.session_state:
    st.session_state.slide_materi = []
if 'file_suara' not in st.session_state:
    st.session_state.file_suara = "audio_guru.mp3"
if 'kuis_data' not in st.session_state:
    st.session_state.kuis_data = []

# --- ANTARMUKA PENGGUNA (UI) UTAMA ---
st.set_page_config(page_title="Tutor Pintar Rigil", page_icon="🎓", layout="wide")

# --- CUSTOM CSS ALA GAMMA APP ---
st.markdown("""
<style>
    .slide-card {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 30px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.08);
        margin-bottom: 25px;
        border-left: 10px solid #FF9800;
        border-top: 1px solid #f0f0f0;
        border-right: 1px solid #f0f0f0;
        border-bottom: 1px solid #f0f0f0;
    }
    .slide-title {
        color: #E65100;
        font-size: 28px;
        font-weight: 800;
        margin-bottom: 15px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .slide-content {
        color: #333333;
        font-size: 18px;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎓 Tutor Pintar Rigil (Interactive Slide Edition)")
st.write("Modul presentasi cerdas dengan visual ala Gamma, penjelasan audio utuh, dan 10 Tantangan Kuis!")

# --- FORMULIR UNGGAH BUKU ---
with st.form("user_form"):
    col1, col2, col3 = st.columns(3)
    with col1: nama = st.text_input("Nama Siswa:", "Rigil")
    with col2: jenjang_kelas = st.selectbox("Jenjang & Kelas:", ["SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6"], index=2)
    with col3: mapel = st.text_input("Mata Pelajaran:", "Matematika")
    
    uploaded_file = st.file_uploader("Foto Halaman Buku Pelajaran:", type=["jpg", "jpeg", "png"])
    btn_analisis = st.form_submit_button(label="Ubah Jadi Presentasi! 🚀")

# --- PROSES ANALISIS AI (OTAK SISTEM) ---
if btn_analisis:
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Buku Pelajaran Asli", width=400)
        
        with st.spinner("AI sedang merancang presentasi visual, menulis naskah, dan menyusun 10 kuis..."):
            try:
                # Instruksi canggih untuk memisahkan Slide Visual, Naskah, dan 10 Kuis
                ux_bridge_prompt = (
                    "Kamu adalah Tutor AI ahli " + mapel + " yang kreatif. Baca materi dari foto ini untuk siswa " + jenjang_kelas + " bernama " + nama + ".\n"
                    "Keluarkan persis 2 bagian berikut:\n\n"
                    "===PRESENTASI===\n"
                    "(Buat 3 hingga 5 Slide materi. Pisahkan tiap slide HANYA dengan tag [SLIDE].\n"
                    "Format tiap slide WAJIB seperti ini:\n"
                    "[SLIDE]\n"
                    "Judul: [Tulis Judul Slide Menarik]\n"
                    "Visual: [Tulis poin-poin materi untuk layar. Gunakan format tebal, daftar poin, dan banyak emoji agar secara visual menyerupai presentasi bergaya modern dan berbobot.]\n"
                    "Naskah: [Tulis naskah lisan guru yang SANGAT PANJANG, detail, dan sabar untuk dibacakan saat slide ini tampil. Jangan gunakan simbol rumit.])\n\n"
                    "===KUIS===\n"
                    "(Buat TEPAT 10 soal pilihan ganda yang bervariasi tingkat kesulitannya. Tiap soal WAJIB di baris baru dengan format pemisah '|||' HANYA seperti ini:)\n"
                    "Pertanyaan soal pertama?|||Opsi A|||Opsi B|||Opsi C|||Opsi D|||A\n"
                    "Pertanyaan soal kedua?|||Opsi A|||Opsi B|||Opsi C|||Opsi D|||B"
                )
                
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[ux_bridge_prompt, image]
                )
                full_text = response.text
                
                # 1. PARSING PRESENTASI (Visual & Naskah)
                naskah_audio_lengkap = ""
                st.session_state.slide_materi = []
                
                if "===PRESENTASI===" in full_text:
                    bagian_pres = re.search(r'===PRESENTASI===(.*?)(?====KUIS===|$)', full_text, re.DOTALL)
                    if bagian_pres:
                        slides_raw = bagian_pres.group(1).split("[SLIDE]")
                        for slide in slides_raw:
                            if len(slide.strip()) > 10:
                                judul = re.search(r'Judul:(.*?)(?=Visual:|$)', slide, re.DOTALL)
                                visual = re.search(r'Visual:(.*?)(?=Naskah:|$)', slide, re.DOTALL)
                                naskah = re.search(r'Naskah:(.*)', slide, re.DOTALL)
                                
                                j_teks = judul.group(1).strip() if judul else "Materi"
                                v_teks = visual.group(1).strip() if visual else "..."
                                n_teks = naskah.group(1).strip() if naskah else "..."
                                
                                st.session_state.slide_materi.append({"judul": j_teks, "visual": v_teks})
                                naskah_audio_lengkap += " " + n_teks

                # Merekam seluruh naskah ke dalam satu file audio yang mulus
                if naskah_audio_lengkap:
                    naskah_bersih = re.sub(r'[*#_`>-]', '', naskah_audio_lengkap)
                    buat_suara_google(naskah_bersih, st.session_state.file_suara, API_KEY)

                # 2. PARSING KUIS (10 Soal)
                st.session_state.kuis_data = []
                if "===KUIS===" in full_text:
                    bagian_kuis = re.search(r'===KUIS===(.*)', full_text, re.DOTALL)
                    if bagian_kuis:
                        baris_kuis = bagian_kuis.group(1).strip().split('\n')
                        for baris in baris_kuis:
                            parts = baris.split("|||")
                            if len(parts) >= 6:
                                st.session_state.kuis_data.append({
                                    "soal": parts[0].strip(),
                                    "opsi": [parts[1].strip(), parts[2].strip(), parts[3].strip(), parts[4].strip()],
                                    "kunci": parts[5].strip()
                                })
                
                st.session_state.berhasil_baca = True
                
            except Exception as e:
                st.error("Terjadi kendala saat meracik presentasi: " + str(e))
    else:
        st.warning("Silakan unggah foto bukunya dulu ya!")

# --- MENAMPILKAN MODUL PRESENTASI & KUIS ---
if st.session_state.berhasil_baca:
    st.markdown("---")
    
    # KONTROL AUDIO UTAMA
    st.markdown("### 🎧 Dengarkan Penjelasan Lengkap")
    st.info("Tekan tombol **Play** sambil membaca slide presentasi di bawah ini secara perlahan.")
    st.audio(st.session_state.file_suara, format="audio/mp3")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # RENDER SLIDE ALA GAMMA
    for i, slide in enumerate(st.session_state.slide_materi):
        st.markdown(
            '<div class="slide-card">'
            '<div class="slide-title">Slide ' + str(i+1) + ': ' + slide["judul"] + '</div>'
            '<div class="slide-content">', 
            unsafe_allow_html=True
        )
        # Render markdown native Streamlit di dalam card
        st.markdown(slide["visual"]) 
        st.markdown('</div></div>', unsafe_allow_html=True)
    
    # RENDER 10 KUIS INTERAKTIF
    st.markdown("---")
    st.markdown("## 🏆 Ujian Penguasaan Materi (10 Soal)")
    st.write("Mari kita lihat seberapa jauh " + nama + " memahami materi ini!")
    
    with st.form("kuis_form_10"):
        jawaban_user = []
        for i, q in enumerate(st.session_state.kuis_data):
            st.markdown("**" + str(i+1) + ". " + q["soal"] + "**")
            ans = st.radio("Pilih jawaban:", q["opsi"], key="q_" + str(i), label_visibility="collapsed")
            jawaban_user.append(ans)
            st.markdown("<br>", unsafe_allow_html=True)
            
        cek_skor = st.form_submit_button("Kumpulkan & Cek Nilai! 🎯")
        
        if cek_skor:
            skor_benar = 0
            for i, q in enumerate(st.session_state.kuis_data):
                # Validasi kunci jawaban sederhana (mencari kecocokan awal string)
                if jawaban_user[i].startswith(q["kunci"]) or q["kunci"] in jawaban_user[i]:
                    skor_benar += 1
            
            nilai_akhir = (skor_benar / len(st.session_state.kuis_data)) * 100
            
            st.markdown("---")
            if nilai_akhir == 100:
                st.success("LUAR BIASA! Nilaimu **100**! Benar semua! ⭐⭐⭐⭐⭐")
                st.balloons()
            elif nilai_akhir >= 70:
                st.info("Hebat! Nilaimu **" + str(int(nilai_akhir)) + "** (" + str(skor_benar) + " Benar). Sedikit lagi sempurna!")
            else:
                st.warning("Nilaimu **" + str(int(nilai_akhir)) + "** (" + str(skor_benar) + " Benar). Jangan menyerah, ayo dengarkan audionya lagi dan coba lagi!")
