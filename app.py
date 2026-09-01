import streamlit as st
import streamlit.components.v1 as components
import re
import time
import json
import base64
from PIL import Image
from google import genai
from google.genai import types
from google.cloud import texttospeech
from google.oauth2 import service_account

# --- KONFIGURASI BATAS MASTER (ANTI-FARMING) ---
BATAS_MASTER = 5 

# --- DESAIN UI / CSS CUSTOM STREAMLIT ---
st.set_page_config(page_title="$IGIL - Learn to Earn", page_icon="🎓", layout="centered")

# --- DATABASE KARAKTER GURU ---
DATA_GURU = {
    "SD": [
        {"nama": "Bu Nisa (Ceria & Lembut)", "voice": "id-ID-Wavenet-A", "pitch": 4.0, "rate": 0.9, "pesan": "Halo anak hebat! Aku Bu Nisa. Mari kita belajar sambil bermain dan bersenang-senang ya!"},
        {"nama": "Pak Andi (Asyik & Lucu)", "voice": "id-ID-Wavenet-B", "pitch": 2.0, "rate": 0.95, "pesan": "Halo jagoan! Sama Pak Andi, materi belajar hari ini pasti jadi gampang banget dipahami!"}
    ],
    "SMP": [
        {"nama": "Kak Maya (Ramah & Gaul)", "voice": "id-ID-Wavenet-D", "pitch": 1.0, "rate": 1.0, "pesan": "Halo sahabat! Bersama Kak Maya, materi serumit apapun pasti bisa kita pecahkan bareng-bareng!"},
        {"nama": "Kak Bimo (Semangat & Tegas)", "voice": "id-ID-Wavenet-C", "pitch": 0.0, "rate": 1.05, "pesan": "Yo! Aku Kak Bimo. Siap bantu kamu taklukkan semua tugas sekolah dan PR hari ini!"}
    ],
    "SMA": [
        {"nama": "Bu Ratna (Profesional & Rapi)", "voice": "id-ID-Wavenet-A", "pitch": -1.0, "rate": 1.15, "pesan": "Selamat datang. Saya Bu Ratna. Mari kita fokus dan pelajari materi ini dengan logika yang tajam."},
        {"nama": "Pak Surya (Logis & Cepat)", "voice": "id-ID-Wavenet-B", "pitch": -2.0, "rate": 1.15, "pesan": "Salam. Saya Pak Surya. Siapkan dirimu, kita akan membedah konsep ini dengan cepat dan akurat."}
    ]
}

# --- INISIALISASI SESSION STATE ---
if 'berhasil_baca' not in st.session_state:
    st.session_state.berhasil_baca = False
if 'tag_materi' not in st.session_state:
    st.session_state.tag_materi = ""
if 'naskah_layar' not in st.session_state:
    st.session_state.naskah_layar = ""
if 'file_suara' not in st.session_state:
    st.session_state.file_suara = "audio_guru.mp3"
if 'daftar_kuis' not in st.session_state:
    st.session_state.daftar_kuis = []
if 'qa_history' not in st.session_state:
    st.session_state.qa_history = []
if 'guru_aktif' not in st.session_state:
    st.session_state.guru_aktif = DATA_GURU["SD"][0] 

# Mata Uang $IGIL & Pelacakan Sertifikat Penguasaan
if 'saldo_igil' not in st.session_state:
    st.session_state.saldo_igil = 0
if 'tampilkan_toko' not in st.session_state:
    st.session_state.tampilkan_toko = False
if 'tracker_penguasaan' not in st.session_state:
    st.session_state.tracker_penguasaan = {} 
if 'sertifikat_lulus' not in st.session_state:
    st.session_state.sertifikat_lulus = [] 

# --- KONFIGURASI KUNCI API & GOOGLE CLOUD ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "MASUKKAN_GEMINI_API_KEY_ANDA_DI_SINI"

client_gemini = genai.Client(api_key=API_KEY)

try:
    gcp_json_str = st.secrets["GOOGLE_CREDENTIALS_JSON"]
    gcp_creds_dict = json.loads(gcp_json_str)
    gcp_credentials = service_account.Credentials.from_service_account_info(gcp_creds_dict)
    client_tts = texttospeech.TextToSpeechClient(credentials=gcp_credentials)
except Exception as e:
    client_tts = None

# --- FUNGSI PEMBUAT SUARA GOOGLE PREMIUM ---
def buat_suara_google(teks, nama_file, nama_suara, pitch_guru, rate_guru):
    if not client_tts:
        return
    synthesis_input = texttospeech.SynthesisInput(text=teks)
    voice = texttospeech.VoiceSelectionParams(language_code="id-ID", name=nama_suara)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=rate_guru, pitch=pitch_guru)
    response = client_tts.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    with open(nama_file, "wb") as out:
        out.write(response.audio_content)

# --- ANTARMUKA PENGGUNA (UI) UTAMA ---
st.title("🎓 $IGIL")
st.markdown("### *Learn to Earn Concept*")
st.markdown("Dengan rajin belajar di aplikasi **$IGIL**, kamu bisa membiayai pendidikanmu sendiri. <br> *Rajin belajar ➡️ Bisa jawab soal Latihan ➡️ Dapet hadiah beasiswa instant!!*", unsafe_allow_html=True)

# --- DOMPET SALDO $IGIL ---
st.markdown(f"""
<div style="background-color: #E0F7FA; padding: 15px 25px; border-radius: 12px; border-left: 8px solid #00BCD4; display: flex; justify-content: space-between; align-items: center; margin-top: 20px; margin-bottom: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
    <div style="font-size: 18px; font-weight: bold; color: #00838F;">💰 Nilai Beasiswa:</div>
    <div style="font-size: 26px; font-weight: 900; color: #00838F;">{st.session_state.saldo_igil} $IGIL</div>
</div>
""", unsafe_allow_html=True)

# --- SIMULASI TOKO PENCARIAN BEASISWA INSTAN ---
if st.button("🎓 Tukar Saldo $IGIL Menjadi Beasiswa Instan", use_container_width=True):
    st.session_state.tampilkan_toko = not st.session_state.tampilkan_toko

if st.session_state.tampilkan_toko:
    with st.container():
        st.markdown("<div style='background-color:#F5F5F5; padding:20px; border-radius:10px;'>", unsafe_allow_html=True)
        st.markdown("### 🎁 Etalase Beasiswa Instan")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("📚 **Voucher Buku Gramedia**\n\nBiaya: **500 $IGIL**")
            if st.button("Tukar Voucher", key="tukar_1"):
                if st.session_state.saldo_igil >= 500:
                    st.session_state.saldo_igil -= 500
                    st.success("✅ Berhasil! Kode Voucher: GRM-IGIL-8821")
                else:
                    st.error("❌ Saldo $IGIL kurang.")
        with col2:
            st.warning("🌐 **Kuota Internet Belajar 5GB**\n\nBiaya: **1.000 $IGIL**")
            if st.button("Tukar Kuota", key="tukar_2"):
                if st.session_state.saldo_igil >= 1000:
                    st.session_state.saldo_igil -= 1000
                    st.success("✅ Berhasil! Kuota masuk ke nomormu.")
                else:
                    st.error("❌ Saldo $IGIL kurang.")
        with col3:
            st.success("🏫 **Subsidi SPP Sekolah Rp 50.000**\n\nBiaya: **5.000 $IGIL**")
            if st.button("Tukar SPP", key="tukar_3"):
                if st.session_state.saldo_igil >= 5000:
                    st.session_state.saldo_igil -= 5000
                    st.success("✅ Berhasil! Dana dikirim ke sekolah.")
                else:
                    st.error("❌ Saldo $IGIL kurang.")
        st.markdown("</div><br>", unsafe_allow_html=True)

st.markdown("---")

# --- AREA BELAJAR & PENGISIAN DATA ---
mode_belajar = st.radio("Pilih Sumber Materi:", ["📸 Unggah Foto Buku", "✍️ Ketik Judul Materi"], horizontal=True)

col_siswa, col_kelas, col_mapel = st.columns(3)
with col_siswa: nama = st.text_input("Nama Siswa:", "Rigil")
with col_kelas: jenjang_kelas = st.selectbox("Jenjang & Kelas:", ["SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6", "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9", "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"], index=2)
with col_mapel: mapel = st.text_input("Mata Pelajaran:", "Matematika")
# Field Bab Materi Dihapus karena AI yang akan menebak secara otomatis!

if mode_belajar == "📸 Unggah Foto Buku":
    uploaded_files = st.file_uploader("Foto Halaman Buku Pelajaran (Bisa lebih dari 1):", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    judul_materi = ""
else:
    judul_materi = st.text_input("Penjelasan spesifik materi yang Ingin Dipelajari:")
    uploaded_files = []

# --- PEMILIHAN KARAKTER GURU ---
st.markdown("### 👨‍🏫 Pilih Guru Favoritmu!")
jenjang_inti = jenjang_kelas.split(" - ")[0] 
daftar_guru = DATA_GURU[jenjang_inti]

nama_guru_pilihan = st.radio("Daftar Guru Tersedia:", [g['nama'] for g in daftar_guru], horizontal=True, label_visibility="collapsed")
guru_terpilih = next(g for g in daftar_guru if g['nama'] == nama_guru_pilihan)

if st.button(f"🔊 Putar Suara Perkenalan {guru_terpilih['nama'].split(' ')[0]}"):
    if client_tts:
        buat_suara_google(guru_terpilih['pesan'], "test_suara.mp3", guru_terpilih['voice'], guru_terpilih['pitch'], guru_terpilih['rate'])
        st.audio("test_suara.mp3", autoplay=True)

st.markdown("<br>", unsafe_allow_html=True)
btn_analisis = st.button("Mulai Belajar! 🚀", use_container_width=True, type="primary")

# --- PROSES ANALISIS AI ---
if btn_analisis:
    if mode_belajar == "📸 Unggah Foto Buku" and not uploaded_files:
        st.warning("Silakan unggah minimal satu foto buku dulu ya!")
    elif mode_belajar == "✍️ Ketik Judul Materi" and not judul_materi:
        st.warning("Silakan ketik judul materi yang ingin dipelajari!")
    else:
        st.session_state.guru_aktif = guru_terpilih
        
        for key in list(st.session_state.keys()):
            if key.startswith('status_soal_') or key.startswith('koin_diberikan_') or key.startswith('boss_'):
                del st.session_state[key]
        st.session_state.qa_history = [] 
        
        with st.spinner(f"{st.session_state.guru_aktif['nama'].split(' ')[0]} sedang membaca materi & menyiapkan rumus tanpa kode..."):
            
            # --- PROMPT DIPERBARUI: PELACAKAN OTOMATIS & PEMBERSIHAN MATHJAX ---
            instruksi_format = f"""
            Keluarkan persis 4 bagian berikut dengan format pembatas ketat:

            ===TAG_MATERI===
            (Tuliskan nama SUB-BAB paling spesifik dari materi ini dalam maksimal 3 kata. Contoh: Perkalian Pecahan, Phytagoras 3D. Ini digunakan oleh sistem untuk mendeteksi materi secara otomatis).

            ===NASKAH_LAYAR===
            (Penjelasan materi detail. Gunakan EMOJI. Format HTML ketat, tanpa Markdown.
            ATURAN MATEMATIKA SANGAT KETAT: DILARANG KERAS menggunakan format kode LaTeX atau MathJax seperti tanda $, \\sqrt, \\frac, atau \\text. 
            Tuliskan rumus dengan teks biasa dan HTML murni. Contoh: gunakan <sup>2</sup> untuk kuadrat, tulis kata 'akar dari' atau simbol &radic; untuk akar, gunakan tanda kurung biasa. NASKAH HARUS BERSIH DARI KODE SIMBOL LAINNYA.)
            
            ===NASKAH_SUARA===
            (Versi lisan dari naskah layar, tanpa emoji, angka dan simbol WAJIB dieja dengan huruf agar terbaca mesin suara dengan mulus).

            ===KUIS===
            (Buatlah 5 soal. Angka HARUS BERBEDA dengan materi. Jika materi ini sudah pernah dibahas sebelumnya, buat variasinya.
            Untuk soal 1 sampai 4 (Pilihan Ganda):
            Pertanyaan 1?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
            Pertanyaan 2?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
            Pertanyaan 3?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
            [SIMULASI UJIAN NASIONAL HOTS] Pertanyaan 4?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
            
            Untuk soal 5, LEVEL BOSS (Ujian Lisan Esai):
            [UJIAN LISAN] Pertanyaan 5?|||LISAN
            )
            """

            if mode_belajar == "📸 Unggah Foto Buku":
                daftar_gambar = [Image.open(file) for file in uploaded_files]
                konteks = f"Kamu Tutor AI ahli {mapel}. Baca materi foto ini untuk siswa bernama {nama} kelas {jenjang_kelas}."
                payload_ai = [konteks + "\n\n" + instruksi_format] + daftar_gambar
            else:
                konteks = f"Kamu Tutor AI ahli {mapel}. Susun materi: '{judul_materi}' untuk siswa bernama {nama} kelas {jenjang_kelas}."
                payload_ai = [konteks + "\n\n" + instruksi_format]

            try:
                response = client_gemini.models.generate_content(model='gemini-3.6-flash', contents=payload_ai)
                full_text = response.text
                
                # Menangkap Pelabelan Sub-Bab Otomatis
                if "===TAG_MATERI===" in full_text:
                    tag_mentah = re.search(r'===TAG_MATERI===(.*?)(?====NASKAH_LAYAR===|$)', full_text, re.DOTALL).group(1).strip().upper()
                    # Membersihkan tag dari spasi atau karakter aneh agar database konsisten
                    tag_bersih = "".join(e for e in tag_mentah if e.isalnum() or e.isspace())
                    st.session_state.tag_materi = tag_bersih
                else:
                    st.session_state.tag_materi = "MATERI_UMUM"
                
                # Inisialisasi Kunci Pelacakan untuk Sub-bab Spesifik
                KUNCI_PELACAKAN = f"{jenjang_kelas}_{mapel}_{st.session_state.tag_materi}"
                if KUNCI_PELACAKAN not in st.session_state.tracker_penguasaan:
                    st.session_state.tracker_penguasaan[KUNCI_PELACAKAN] = 0
                
                if "===NASKAH_LAYAR===" in full_text:
                    st.session_state.naskah_layar = re.search(r'===NASKAH_LAYAR===(.*?)(?====NASKAH_SUARA===|$)', full_text, re.DOTALL).group(1).strip()
                
                if "===NASKAH_SUARA===" in full_text:
                    naskah_suara = re.search(r'===NASKAH_SUARA===(.*?)(?====KUIS===|$)', full_text, re.DOTALL).group(1).strip()
                    naskah_bersih = re.sub(r'[*#_`>-]', '', naskah_suara)
                    buat_suara_google(naskah_bersih, st.session_state.file_suara, guru_terpilih['voice'], guru_terpilih['pitch'], guru_terpilih['rate'])
                
                if "===KUIS===" in full_text:
                    kuis_raw = re.search(r'===KUIS===(.*)', full_text, re.DOTALL).group(1).strip()
                    lines = [line for line in kuis_raw.split('\n') if '|||' in line]
                    parsed_kuis = []
                    for line in lines:
                        parts = line.split("|||")
                        if len(parts) == 2 and "LISAN" in parts[1]:
                            parsed_kuis.append({"tipe": "lisan", "soal": parts[0].strip()})
                        elif len(parts) >= 5:
                            parsed_kuis.append({
                                "tipe": "pg",
                                "soal": parts[0].strip(),
                                "opsi": [parts[1].strip(), parts[2].strip(), parts[3].strip()],
                                "kunci": parts[4].strip()
                            })
                    st.session_state.daftar_kuis = parsed_kuis
                
                st.session_state.berhasil_baca = True
            except Exception as e:
                st.error(f"Gagal memproses materi: {e}")

# --- MENAMPILKAN MODUL BELAJAR INTERAKTIF ---
if st.session_state.berhasil_baca:
    st.markdown("---")
    
    KUNCI_PELACAKAN = f"{jenjang_kelas}_{mapel}_{st.session_state.tag_materi}"
    is_lulus = KUNCI_PELACAKAN in st.session_state.sertifikat_lulus
    progres = st.session_state.tracker_penguasaan.get(KUNCI_PELACAKAN, 0)
    
    if is_lulus:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #FFD700 0%, #FF8C00 100%); padding: 3px; border-radius: 15px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <div style="background-color: #FAFAFA; padding: 25px; border-radius: 12px; text-align: center; border: 2px dashed #FFB300;">
                <h1 style="color: #E65100; margin: 0; font-size: 36px;">🏆 SERTIFIKAT KELULUSAN 🏆</h1>
                <p style="font-size: 20px; color: #333; margin-top: 10px;">Diberikan secara resmi kepada:</p>
                <h2 style="color: #000; margin: 5px 0;">{nama}</h2>
                <p style="font-size: 18px; color: #555;">Telah berhasil menguasai dan menaklukkan {BATAS_MASTER} variasi Tantangan Ujian Nasional pada sub-bab:</p>
                <h3 style="color: #0078D7; margin: 5px 0;">{mapel} - {st.session_state.tag_materi}</h3>
                <br>
                <span style="background-color: #FFEB3B; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 14px;">🔒 Penambangan Koin Untuk Materi Ini Telah Dikunci</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background-color: #E8F5E9; padding: 10px 20px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 20px;">
            <b style="color: #2E7D32;">📈 Kemajuan Penguasaan '{st.session_state.tag_materi.title()}':</b> {progres} / {BATAS_MASTER} Soal Tantangan Dikuasai.
            <br><small style="color: #555;">(Penuhi target untuk mendapatkan Sertifikat Kelulusan!)</small>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"## 🎧 Dengarkan Penjelasan {st.session_state.guru_aktif['nama'].split(' ')[0]}")
    with open(st.session_state.file_suara, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode()
    
    html_animasi = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 10px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        .materi-card {{ background-color: #F4FBFF; border-left: 6px solid #2AB3FF; padding: 25px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); margin-bottom: 25px; }}
        .materi-card h3 {{ color: #0078D7; font-weight: 800; margin-top: 0; }}
        .materi-card p, .materi-card li {{ font-size: 17px; line-height: 1.7; color: #333333; }}
        .word {{ opacity: 0; transition: opacity 0.15s ease-out; }}
        .word.active {{ opacity: 1; }}
        .player-box {{ text-align: center; margin-bottom: 20px; padding: 15px; background: #fff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    </style>
    </head>
    <body>
        <div class="player-box">
            <p style="margin-top:0; color:#FF5722; font-weight:bold; font-size: 18px;">▶️ Klik PLAY untuk memunculkan catatan ajaib! ✨</p>
            <audio id="audio-player" controls style="width: 100%; outline: none;">
                <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
            </audio>
        </div>
        <div class="materi-card" id="materi-content">{st.session_state.naskah_layar}</div>
        <script>
            const audio = document.getElementById('audio-player');
            const content = document.getElementById('materi-content');
            let totalChars = 0; const wordData = [];
            function wrapWords(element) {{
                const children = Array.from(element.childNodes);
                children.forEach(child => {{
                    if (child.nodeType === Node.TEXT_NODE) {{
                        const words = child.nodeValue.split(/(\\s+)/);
                        const fragment = document.createDocumentFragment();
                        let hasWords = false;
                        words.forEach(word => {{
                            if (word.trim().length > 0) {{
                                const span = document.createElement('span'); span.className = 'word'; span.textContent = word;
                                fragment.appendChild(span); hasWords = true;
                                let charCount = word.trim().length; totalChars += charCount;
                                wordData.push({{ element: span, chars: charCount }});
                            }} else {{ fragment.appendChild(document.createTextNode(word)); }}
                        }});
                        if (hasWords) {{ element.replaceChild(fragment, child); }}
                    }} else if (child.nodeType === Node.ELEMENT_NODE) {{ wrapWords(child); }}
                }});
            }}
            wrapWords(content);
            audio.addEventListener('timeupdate', () => {{
                if (audio.duration) {{
                    let progress = ((audio.currentTime + 0.6) / audio.duration) * 1.35;
                    if (progress > 1) progress = 1;
                    let targetChars = progress * totalChars; let currentChars = 0;
                    for (let i = 0; i < wordData.length; i++) {{
                        currentChars += wordData[i].chars;
                        if (currentChars <= targetChars) {{ wordData[i].element.classList.add('active'); }} 
                        else {{ wordData[i].element.classList.remove('active'); }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    components.html(html_animasi, height=750, scrolling=True)

    # --- SEGMEN KUIS, SIMULASI UJIAN, & LEVEL BOSS ---
    st.markdown("---")
    st.markdown(f"## 🏆 Latihan & Dapatkan Beasiswa $IGIL, {nama}!")
    
    if st.session_state.daftar_kuis:
        for i, q in enumerate(st.session_state.daftar_kuis):
            
            # --- SOAL PILIHAN GANDA (1-4) ---
            if q['tipe'] == "pg":
                is_hots = "[SIMULASI" in q['soal'].upper()
                if is_hots:
                    soal_bersih = q['soal'].replace("[SIMULASI UJIAN NASIONAL HOTS]", "").replace("[SIMULASI UJIAN NASIONAL]", "").strip()
                    st.markdown(f"🔥 **{i+1}. [TANTANGAN LOGIKA] {soal_bersih}**")
                else:
                    st.markdown(f"**{i+1}. {q['soal']}**")
                
                jawaban_user = st.radio("Pilih jawaban:", q['opsi'], key=f"soal_radio_{i}", index=None, label_visibility="collapsed")
                
                if st.button(f"Cek Jawaban Soal {i+1}", key=f"btn_cek_{i}"):
                    if jawaban_user == q['kunci']:
                        st.session_state[f"status_soal_{i}"] = "benar"
                        
                        if not st.session_state.get(f"koin_diberikan_{i}", False):
                            st.session_state[f"koin_diberikan_{i}"] = True
                            
                            if is_lulus:
                                st.toast("✅ Benar! (Saldo tidak bertambah karena kamu sudah Lulus di Bab ini)")
                            else:
                                hadiah = 50 if is_hots else 10
                                st.session_state.saldo_igil += hadiah
                                st.toast(f"🎉 Hebat! +{hadiah} $IGIL ditambahkan!")
                                
                                if is_hots:
                                    st.session_state.tracker_penguasaan[KUNCI_PELACAKAN] += 1
                                    if st.session_state.tracker_penguasaan[KUNCI_PELACAKAN] >= BATAS_MASTER and not is_lulus:
                                        st.session_state.sertifikat_lulus.append(KUNCI_PELACAKAN)
                                        st.balloons()
                            time.sleep(1.5)
                            st.rerun()
                    elif jawaban_user is None:
                        st.session_state[f"status_soal_{i}"] = "kosong"
                    else:
                        st.session_state[f"status_soal_{i}"] = "salah"
                
                status_jawaban = st.session_state.get(f"status_soal_{i}")
                if status_jawaban == "benar":
                    st.success("Tepat sekali! ⭐" if is_lulus else "Tepat sekali! Nilai beasiswamu sudah ditambahkan. ⭐")
                elif status_jawaban == "salah":
                    st.error("Masih kurang tepat, coba lagi pelan-pelan.")
                st.write("")
                
            # --- SOAL 5: LEVEL BOSS LISAN BERWAKTU ---
            elif q['tipe'] == "lisan":
                boss_key = f"boss_state_{i}"
                start_key = f"boss_start_{i}"
                
                if boss_key not in st.session_state:
                    st.session_state[boss_key] = "idle" 
                    
                st.markdown("---")
                st.markdown(f"### 🐉 LEVEL BOSS: Ujian Lisan Berwaktu!")
                st.info(f"Waktumu hanya 45 detik untuk menjelaskan cara kerjanya secara lisan.")
                
                soal_lisan_bersih = q['soal'].replace("[UJIAN LISAN]", "").strip()
                st.markdown(f"**Pertanyaan:** {soal_lisan_bersih}")
                
                if st.session_state[boss_key] == "idle":
                    if st.button("▶️ Mulai Jawab! (Waktu 45 Detik Berjalan)", key=f"btn_mulai_{i}"):
                        st.session_state[boss_key] = "active"
                        st.session_state[start_key] = time.time()
                        st.rerun()
                        
                elif st.session_state[boss_key] == "active":
                    sisa_waktu = int(45 - (time.time() - st.session_state[start_key]))
                    if sisa_waktu > 0:
                        components.html(f"""
                        <div style="font-size:30px; color:#D32F2F; font-weight:900; text-align:center; padding:10px; border:3px dashed #D32F2F; background-color:#FFEBEE;">
                            ⏱️ Sisa Waktu: {sisa_waktu} Detik
                        </div>""", height=80)
                        
                        jawaban_audio_lisan = st.audio_input("Rekam Penjelasanmu:", key=f"audio_ujian_{i}")
                        
                        if st.button("Serahkan Ujian Lisan! 🎙️", key=f"btn_lisan_{i}"):
                            if time.time() - st.session_state[start_key] > 47:
                                st.session_state[boss_key] = "timeout"
                                st.rerun()
                            elif jawaban_audio_lisan:
                                with st.spinner("Menganalisis suaramu..."):
                                    prompt_evaluasi = f"Evaluasi suara siswa untuk soal: '{soal_lisan_bersih}'. Jika logika benar dan suara natural, beri [STATUS] LULUS. Jika salah/terdengar baca robot, beri [STATUS] GAGAL. Beri alasan singkat."
                                    try:
                                        resp_eval = client_gemini.models.generate_content(model='gemini-3.6-flash', contents=[prompt_evaluasi, types.Part.from_bytes(data=jawaban_audio_lisan.read(), mime_type='audio/wav')])
                                        st.session_state[f"boss_hasil_{i}"] = resp_eval.text
                                        st.session_state[boss_key] = "evaluated"
                                        st.rerun()
                                    except:
                                        st.error("Gagal memeriksa.")
                            else:
                                st.warning("Rekam suara dulu!")
                    else:
                        st.session_state[boss_key] = "timeout"
                        st.rerun()
                        
                elif st.session_state[boss_key] == "timeout":
                    st.error("⏳ Waktu habis!")
                    if st.button("🔄 Minta Soal Level Boss Baru", key=f"btn_ganti_timeout_{i}"):
                        try:
                            resp = client_gemini.models.generate_content(model='gemini-3.6-flash', contents=[f"Buat 1 soal HOTS lisan BARU yg berbeda dari '{soal_lisan_bersih}'. Format: [UJIAN LISAN] Soal?|||LISAN"])
                            st.session_state.daftar_kuis[i]['soal'] = resp.text.split("|||")[0].strip()
                            st.session_state[boss_key] = "idle"
                            st.rerun()
                        except:
                            st.error("Gagal membuat soal baru.")

                elif st.session_state[boss_key] == "evaluated":
                    hasil_teks = st.session_state.get(f"boss_hasil_{i}", "")
                    if "[STATUS] LULUS" in hasil_teks.upper():
                        st.success(hasil_teks.replace("[STATUS] LULUS", "✅ **LULUS LEVEL BOSS!**\n\n"))
                        if not st.session_state.get(f"koin_diberikan_{i}", False):
                            st.session_state[f"koin_diberikan_{i}"] = True
                            
                            if is_lulus:
                                st.toast("✅ Level Boss Selesai (Tidak ada koin, kamu sudah Lulus bab ini)")
                            else:
                                st.session_state.saldo_igil += 100
                                st.session_state.tracker_penguasaan[KUNCI_PELACAKAN] += 1
                                st.toast("🎉 LEVEL BOSS DITAKLUKKAN! +100 $IGIL!")
                                
                                if st.session_state.tracker_penguasaan[KUNCI_PELACAKAN] >= BATAS_MASTER:
                                    st.session_state.sertifikat_lulus.append(KUNCI_PELACAKAN)
                                    st.balloons()
                            time.sleep(1.5)
                            st.rerun()
                    else:
                        st.error(hasil_teks.replace("[STATUS] GAGAL", "❌ **BELUM LULUS!**\n\n"))
                        if st.button("🔄 Minta Soal Level Boss Baru", key=f"btn_ganti_gagal_{i}"):
                            try:
                                resp = client_gemini.models.generate_content(model='gemini-3.6-flash', contents=[f"Buat 1 soal HOTS lisan BARU yg berbeda dari '{soal_lisan_bersih}'. Format: [UJIAN LISAN] Soal?|||LISAN"])
                                st.session_state.daftar_kuis[i]['soal'] = resp.text.split("|||")[0].strip()
                                st.session_state[boss_key] = "idle"
                                st.rerun()
                            except:
                                st.error("Gagal membuat soal baru.")
