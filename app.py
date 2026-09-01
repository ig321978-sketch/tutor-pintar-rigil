import streamlit as st
import streamlit.components.v1 as components
import re
import time
import json
import base64
import random
from PIL import Image
from google import genai
from google.genai import types
from google.cloud import texttospeech
from google.oauth2 import service_account

# --- KONFIGURASI APLIKASI ---
BATAS_MASTER = 5 
NYAWA_MAKSIMAL = 3

st.set_page_config(page_title="$IGIL - Learn to Earn", page_icon="🎓", layout="centered")

# --- DATABASE KARAKTER GURU ---
DATA_GURU = {
    "SD": [
        {"nama": "Bu Nisa (Ceria & Lembut)", "voice": "id-ID-Wavenet-A", "pitch": 4.0, "rate": 0.9, "pesan": "Halo anak hebat! Aku Bu Nisa."},
        {"nama": "Pak Andi (Asyik & Lucu)", "voice": "id-ID-Wavenet-B", "pitch": 2.0, "rate": 0.95, "pesan": "Halo jagoan! Sama Pak Andi belajar jadi asyik!"}
    ],
    "SMP": [
        {"nama": "Kak Maya (Ramah & Gaul)", "voice": "id-ID-Wavenet-D", "pitch": 1.0, "rate": 1.0, "pesan": "Halo sahabat! Bersama Kak Maya kita pecahkan masalahnya!"},
        {"nama": "Kak Bimo (Semangat & Tegas)", "voice": "id-ID-Wavenet-C", "pitch": 0.0, "rate": 1.05, "pesan": "Yo! Aku Kak Bimo. Siap bantu taklukkan PR hari ini!"}
    ],
    "SMA": [
        {"nama": "Bu Ratna (Profesional & Rapi)", "voice": "id-ID-Wavenet-A", "pitch": -1.0, "rate": 1.15, "pesan": "Selamat datang. Saya Bu Ratna. Mari kita fokus."},
        {"nama": "Pak Surya (Logis & Cepat)", "voice": "id-ID-Wavenet-B", "pitch": -2.0, "rate": 1.15, "pesan": "Salam. Saya Pak Surya. Siapkan dirimu."}
    ]
}

# --- INISIALISASI SESSION STATE ---
if 'berhasil_baca' not in st.session_state: st.session_state.berhasil_baca = False
if 'tag_materi' not in st.session_state: st.session_state.tag_materi = ""
if 'naskah_layar' not in st.session_state: st.session_state.naskah_layar = ""
if 'file_suara' not in st.session_state: st.session_state.file_suara = "audio_guru.mp3"
if 'daftar_kuis' not in st.session_state: st.session_state.daftar_kuis = []
if 'qa_history' not in st.session_state: st.session_state.qa_history = []
if 'guru_aktif' not in st.session_state: st.session_state.guru_aktif = DATA_GURU["SD"][0] 

# Sistem Ekonomi, Nyawa, dan Sertifikat
if 'saldo_igil' not in st.session_state: st.session_state.saldo_igil = 0
if 'nyawa' not in st.session_state: st.session_state.nyawa = NYAWA_MAKSIMAL
if 'tampilkan_toko' not in st.session_state: st.session_state.tampilkan_toko = False
if 'tracker_penguasaan' not in st.session_state: st.session_state.tracker_penguasaan = {} 
if 'sertifikat_lulus' not in st.session_state: st.session_state.sertifikat_lulus = [] 
if 'rapor_ai' not in st.session_state: st.session_state.rapor_ai = ""

# Dummy Data Papan Peringkat
if 'leaderboard' not in st.session_state:
    st.session_state.leaderboard = [
        {"Nama": "Budi (SD Jkt)", "Saldo": 4500}, {"Nama": "Siti (SD Bdg)", "Saldo": 3200},
        {"Nama": "Arif (SD Sby)", "Saldo": 2800}, {"Nama": "Nanda (SD Mdn)", "Saldo": 1500}
    ]

# Dummy Data Histori Belajar untuk Dashboard Orang Tua
if 'histori_belajar' not in st.session_state:
    st.session_state.histori_belajar = [
        {"tanggal": "28 Agustus 2026", "mapel": "IPA (Sains)", "bab": "Tata Surya", "skor": 45, "status": "Kurang Fokus"},
        {"tanggal": "30 Agustus 2026", "mapel": "Matematika", "bab": "Perkalian Dasar", "skor": 65, "status": "Sedang Berkembang"},
        {"tanggal": "1 September 2026", "mapel": "Matematika", "bab": "Transformasi Geometri", "skor": 95, "status": "Lulus Level Boss"}
    ]

# --- KONFIGURASI API ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = "MASUKKAN_GEMINI_API_KEY_ANDA_DI_SINI"
client_gemini = genai.Client(api_key=API_KEY)

try:
    gcp_json_str = st.secrets["GOOGLE_CREDENTIALS_JSON"]
    gcp_creds_dict = json.loads(gcp_json_str)
    gcp_credentials = service_account.Credentials.from_service_account_info(gcp_creds_dict)
    client_tts = texttospeech.TextToSpeechClient(credentials=gcp_credentials)
except:
    client_tts = None

def buat_suara_google(teks, nama_file, nama_suara, pitch_guru, rate_guru):
    if not client_tts: return
    synthesis_input = texttospeech.SynthesisInput(text=teks)
    voice = texttospeech.VoiceSelectionParams(language_code="id-ID", name=nama_suara)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=rate_guru, pitch=pitch_guru)
    response = client_tts.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    with open(nama_file, "wb") as out: out.write(response.audio_content)

# --- HEADER GLOBAL APLIKASI ---
st.title("🎓 $IGIL")
st.markdown("### *Learn to Earn Concept*")

# --- BANNER STATUS (SALDO & NYAWA) ---
st.markdown(f"""
<div style="background-color: #E0F7FA; padding: 15px 25px; border-radius: 12px; border-left: 8px solid #00BCD4; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
    <div>
        <div style="font-size: 16px; font-weight: bold; color: #00838F;">💰 Nilai Beasiswa:</div>
        <div style="font-size: 26px; font-weight: 900; color: #00838F;">{st.session_state.saldo_igil} $IGIL</div>
    </div>
    <div style="text-align: right;">
        <div style="font-size: 16px; font-weight: bold; color: #D32F2F;">❤️ Nyawa Belajar:</div>
        <div style="font-size: 26px; font-weight: 900; color: #D32F2F;">{st.session_state.nyawa} / {NYAWA_MAKSIMAL}</div>
    </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.nyawa <= 0:
    st.error("💔 Yaah! Nyawa belajarmu habis karena terlalu banyak menjawab salah.")
    if st.button("💊 Beli 3 Nyawa (Harga: 50 $IGIL)"):
        if st.session_state.saldo_igil >= 50:
            st.session_state.saldo_igil -= 50
            st.session_state.nyawa = 3
            st.success("Nyawa berhasil diisi penuh! Ayo belajar lagi.")
            time.sleep(1)
            st.rerun()
        else:
            st.warning("Saldo $IGIL mu tidak cukup. Kembalilah besok!")
    st.stop() 

# --- NAVIGASI TAB ---
tab_belajar, tab_leaderboard, tab_ortu = st.tabs(["📚 Ruang Belajar", "🏆 Papan Peringkat", "👨‍👩‍👧 Dashboard Orang Tua"])

# ==========================================
# TAB 1: RUANG BELAJAR
# ==========================================
with tab_belajar:
    if st.button("🎁 Tukar Saldo $IGIL Menjadi Beasiswa Instan", use_container_width=True):
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
                        st.success("✅ Berhasil! Kode: GRM-IGIL-8821")
                    else: st.error("❌ Saldo kurang.")
            with col2:
                st.warning("🌐 **Kuota Internet 5GB**\n\nBiaya: **1.000 $IGIL**")
                if st.button("Tukar Kuota", key="tukar_2"):
                    if st.session_state.saldo_igil >= 1000:
                        st.session_state.saldo_igil -= 1000
                        st.success("✅ Berhasil! Kuota dikirim.")
                    else: st.error("❌ Saldo kurang.")
            with col3:
                st.success("🏫 **Subsidi SPP Rp 50k**\n\nBiaya: **5.000 $IGIL**")
                if st.button("Tukar SPP", key="tukar_3"):
                    if st.session_state.saldo_igil >= 5000:
                        st.session_state.saldo_igil -= 5000
                        st.success("✅ Berhasil! Dana dikirim ke sekolah.")
                    else: st.error("❌ Saldo kurang.")
            st.markdown("</div><br>", unsafe_allow_html=True)

    st.markdown("---")
    mode_belajar = st.radio("Pilih Sumber Materi:", ["📸 Unggah Foto Buku", "✍️ Pilih/Ketik Topik Materi"], horizontal=True)

    col_siswa, col_kelas, col_mapel = st.columns(3)
    with col_siswa: nama = st.text_input("Nama Siswa:", "Rigil")
    with col_kelas: jenjang_kelas = st.selectbox("Jenjang & Kelas:", ["SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6", "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9", "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"], index=2)
    with col_mapel: 
        pilihan_mapel = st.selectbox("Mata Pelajaran:", ["Matematika", "Bahasa Indonesia", "Bahasa Inggris", "IPA (Sains)", "IPS (Sosial)", "Fisika", "Kimia", "Biologi", "LAINNYA (Ketik Manual)"])
        mapel = st.text_input("Ketik Mata Pelajaran:", placeholder="Contoh: Muatan Lokal") if pilihan_mapel == "LAINNYA (Ketik Manual)" else pilihan_mapel

    if mode_belajar == "📸 Unggah Foto Buku":
        uploaded_files = st.file_uploader("Foto Halaman Buku Pelajaran:", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        judul_materi = ""
    else:
        pilihan_bab = st.selectbox("Pilih Topik Pembelajaran:", ["Bab 1", "Bab 2", "Bab 3", "Bab 4", "Bab 5", "LAINNYA (Ketik Manual)"])
        judul_materi = st.text_input("Bab Materi yang ingin dipelajari:", placeholder="Contoh: Transformasi Geometri") if pilihan_bab == "LAINNYA (Ketik Manual)" else pilihan_bab
        uploaded_files = []

    st.markdown("### 👨‍🏫 Pilih Guru Favoritmu!")
    jenjang_inti = jenjang_kelas.split(" - ")[0] 
    daftar_guru = DATA_GURU[jenjang_inti]
    nama_guru_pilihan = st.radio("Daftar Guru Tersedia:", [g['nama'] for g in daftar_guru], horizontal=True, label_visibility="collapsed")
    guru_terpilih = next(g for g in daftar_guru if g['nama'] == nama_guru_pilihan)

    if st.button("🔊 Putar Suara Perkenalan"):
        if client_tts:
            buat_suara_google(guru_terpilih['pesan'], "test_suara.mp3", guru_terpilih['voice'], guru_terpilih['pitch'], guru_terpilih['rate'])
            st.audio("test_suara.mp3", autoplay=True)

    btn_analisis = st.button("Mulai Belajar! 🚀", use_container_width=True, type="primary")

    if btn_analisis:
        if not mapel: st.warning("Silakan isi Mata Pelajaran!")
        elif mode_belajar == "📸 Unggah Foto Buku" and not uploaded_files: st.warning("Silakan unggah minimal satu foto buku!")
        elif mode_belajar == "✍️ Pilih/Ketik Topik Materi" and not judul_materi: st.warning("Silakan pilih Bab!")
        else:
            st.session_state.guru_aktif = guru_terpilih
            for key in list(st.session_state.keys()):
                if key.startswith('status_soal_') or key.startswith('koin_diberikan_') or key.startswith('boss_'): del st.session_state[key]
            st.session_state.qa_history = [] 
            
            nama_asli_guru = st.session_state.guru_aktif['nama'].split('(')[0].strip()
            
            with st.spinner(f"{nama_asli_guru} sedang menyiapkan materi & rumus ajaib..."):
                instruksi_format = f"""
                Keluarkan persis 4 bagian berikut dengan format pembatas ketat:
                ===TAG_MATERI===
                (Tuliskan nama SUB-BAB spesifik dalam maksimal 3 kata).
                ===NASKAH_LAYAR===
                (Penjelasan materi detail. Gunakan HTML. DILARANG KERAS menggunakan LaTeX/MathJax).
                ===NASKAH_SUARA===
                (Versi lisan dari naskah layar, angka dieja huruf).
                ===KUIS===
                (Buat 5 soal. Soal 4: [SIMULASI UJIAN NASIONAL HOTS] Pertanyaan?|||Opsi 1|||Opsi 2|||Opsi 3|||Kunci. Soal 5: [UJIAN LISAN] Pertanyaan?|||LISAN)
                """
                payload_ai = [f"Kamu Tutor AI {mapel} bernama {nama_asli_guru}. Susun materi: '{judul_materi}' untuk siswa {nama} kelas {jenjang_kelas}.\n\n{instruksi_format}"]
                if mode_belajar == "📸 Unggah Foto Buku":
                    payload_ai = [f"Kamu Tutor AI {mapel} bernama {nama_asli_guru}. Baca foto ini untuk siswa {nama} kelas {jenjang_kelas}.\n\n{instruksi_format}"] + [Image.open(f) for f in uploaded_files]

                try:
                    response = client_gemini.models.generate_content(model='gemini-3.6-flash', contents=payload_ai)
                    full_text = response.text
                    
                    if "===TAG_MATERI===" in full_text:
                        tag_mentah = re.search(r'===TAG_MATERI===(.*?)(?====NASKAH_LAYAR===|$)', full_text, re.DOTALL).group(1).strip().upper()
                        st.session_state.tag_materi = "".join(e for e in tag_mentah if e.isalnum() or e.isspace())
                    
                    KUNCI_PELACAKAN = f"{jenjang_kelas}_{mapel}_{st.session_state.tag_materi}"
                    if KUNCI_PELACAKAN not in st.session_state.tracker_penguasaan: st.session_state.tracker_penguasaan[KUNCI_PELACAKAN] = 0
                    
                    if "===NASKAH_LAYAR===" in full_text: st.session_state.naskah_layar = re.search(r'===NASKAH_LAYAR===(.*?)(?====NASKAH_SUARA===|$)', full_text, re.DOTALL).group(1).strip()
                    if "===NASKAH_SUARA===" in full_text:
                        naskah_suara = re.search(r'===NASKAH_SUARA===(.*?)(?====KUIS===|$)', full_text, re.DOTALL).group(1).strip()
                        buat_suara_google(re.sub(r'[*#_`>-]', '', naskah_suara), st.session_state.file_suara, guru_terpilih['voice'], guru_terpilih['pitch'], guru_terpilih['rate'])
                    
                    if "===KUIS===" in full_text:
                        lines = [line for line in re.search(r'===KUIS===(.*)', full_text, re.DOTALL).group(1).strip().split('\n') if '|||' in line]
                        parsed_kuis = []
                        for line in lines:
                            parts = line.split("|||")
                            if len(parts) == 2 and "LISAN" in parts[1]: parsed_kuis.append({"tipe": "lisan", "soal": parts[0].strip()})
                            elif len(parts) >= 5: parsed_kuis.append({"tipe": "pg", "soal": parts[0].strip(), "opsi": [parts[1].strip(), parts[2].strip(), parts[3].strip()], "kunci": parts[4].strip()})
                        st.session_state.daftar_kuis = parsed_kuis
                    st.session_state.berhasil_baca = True
                except Exception as e: st.error(f"Gagal memproses: {e}")

    if st.session_state.berhasil_baca:
        st.markdown("---")
        nama_asli_guru = st.session_state.guru_aktif['nama'].split('(')[0].strip()
        KUNCI_PELACAKAN = f"{jenjang_kelas}_{mapel}_{st.session_state.tag_materi}"
        is_lulus = KUNCI_PELACAKAN in st.session_state.sertifikat_lulus
        
        if is_lulus:
            st.success(f"🏆 SERTIFIKAT KELULUSAN: {nama} telah menaklukkan materi {st.session_state.tag_materi}! (Penambangan Koin Terkunci)")
        else:
            st.info(f"📈 Kemajuan '{st.session_state.tag_materi.title()}': {st.session_state.tracker_penguasaan.get(KUNCI_PELACAKAN, 0)} / {BATAS_MASTER} Tantangan Dikuasai.")

        st.markdown(f"## 🎧 Dengarkan Penjelasan {nama_asli_guru}")
        with open(st.session_state.file_suara, "rb") as f: audio_b64 = base64.b64encode(f.read()).decode()
        components.html(f"""
        <div style="text-align:center; padding:15px; background:#fff; border-radius:10px; box-shadow:0 2px 8px rgba(0,0,0,0.1); margin-bottom:20px;">
            <audio controls style="width: 100%;"><source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3"></audio>
        </div>
        <div style="background-color:#F4FBFF; border-left:6px solid #2AB3FF; padding:25px; border-radius:10px; font-family:sans-serif; font-size:17px; line-height:1.7;">
            {st.session_state.naskah_layar}
        </div>
        """, height=600, scrolling=True)

        st.markdown("---")
        st.markdown(f"## 🏆 Latihan & Dapatkan Beasiswa $IGIL!")
        
        if st.session_state.daftar_kuis:
            for i, q in enumerate(st.session_state.daftar_kuis):
                if q['tipe'] == "pg":
                    is_hots = "[SIMULASI" in q['soal'].upper()
                    st.markdown(f"**{i+1}. {q['soal'].replace('[SIMULASI UJIAN NASIONAL HOTS]', '🔥 [TANTANGAN LOGIKA]')}**")
                    jawaban_user = st.radio("Pilih jawaban:", q['opsi'], key=f"soal_radio_{i}", index=None, label_visibility="collapsed")
                    
                    if st.button(f"Cek Jawaban Soal {i+1}", key=f"btn_cek_{i}"):
                        if jawaban_user == q['kunci']:
                            st.session_state[f"status_soal_{i}"] = "benar"
                            
                            # SIMULASI PENCATATAN KE DASHBOARD ORTU
                            data_log_baru = {"tanggal": "1 September 2026", "mapel": mapel, "bab": st.session_state.tag_materi.title(), "skor": 100, "status": "Berhasil"}
                            if data_log_baru not in st.session_state.histori_belajar:
                                st.session_state.histori_belajar.append(data_log_baru)
                                
                            if not st.session_state.get(f"koin_diberikan_{i}", False):
                                st.session_state[f"koin_diberikan_{i}"] = True
                                if not is_lulus:
                                    st.session_state.saldo_igil += 50 if is_hots else 10
                                    if is_hots:
                                        st.session_state.tracker_penguasaan[KUNCI_PELACAKAN] += 1
                                        if st.session_state.tracker_penguasaan[KUNCI_PELACAKAN] >= BATAS_MASTER:
                                            st.session_state.sertifikat_lulus.append(KUNCI_PELACAKAN)
                                            st.balloons()
                                st.rerun()
                        elif jawaban_user is not None:
                            st.session_state[f"status_soal_{i}"] = "salah"
                            st.session_state.nyawa -= 1
                            st.rerun()
                    
                    status = st.session_state.get(f"status_soal_{i}")
                    if status == "benar": st.success("Tepat sekali! ⭐")
                    elif status == "salah": st.error("❌ Salah! Nyawa berkurang 1.")
                    st.write("")
                    
                elif q['tipe'] == "lisan":
                    boss_key = f"boss_state_{i}"
                    start_key = f"boss_start_{i}"
                    if boss_key not in st.session_state: st.session_state[boss_key] = "idle" 
                    
                    st.markdown("---")
                    st.markdown(f"### 🐉 LEVEL BOSS: Ujian Lisan Berwaktu!")
                    soal_lisan_bersih = q['soal'].replace("[UJIAN LISAN]", "").strip()
                    st.markdown(f"**Pertanyaan:** {soal_lisan_bersih}")
                    
                    if st.session_state[boss_key] == "idle":
                        if st.button("▶️ Mulai Jawab! (45 Detik)", key=f"btn_mulai_{i}"):
                            st.session_state[boss_key] = "active"
                            st.session_state[start_key] = time.time()
                            st.rerun()
                    elif st.session_state[boss_key] == "active":
                        sisa_waktu = int(45 - (time.time() - st.session_state[start_key]))
                        if sisa_waktu > 0:
                            st.warning(f"⏱️ Sisa Waktu: {sisa_waktu} Detik")
                            jawaban_audio_lisan = st.audio_input("Rekam Penjelasanmu:", key=f"audio_ujian_{i}")
                            if st.button("Serahkan Ujian Lisan! 🎙️", key=f"btn_lisan_{i}"):
                                if jawaban_audio_lisan:
                                    with st.spinner("Menganalisis suaramu..."):
                                        try:
                                            resp_eval = client_gemini.models.generate_content(model='gemini-3.6-flash', contents=[f"Evaluasi lisan untuk soal: '{soal_lisan_bersih}'. Beri [STATUS] LULUS atau GAGAL.", types.Part.from_bytes(data=jawaban_audio_lisan.read(), mime_type='audio/wav')])
                                            st.session_state[f"boss_hasil_{i}"] = resp_eval.text
                                            st.session_state[boss_key] = "evaluated"
                                            if "[STATUS] GAGAL" in resp_eval.text.upper(): st.session_state.nyawa -= 1
                                            st.rerun()
                                        except: st.error("Gagal memeriksa.")
                        else:
                            st.session_state[boss_key] = "timeout"
                            st.session_state.nyawa -= 1
                            st.rerun()
                    elif st.session_state[boss_key] in ["timeout", "evaluated"]:
                        hasil_teks = st.session_state.get(f"boss_hasil_{i}", "Waktu Habis!")
                        if "[STATUS] LULUS" in hasil_teks.upper():
                            st.success("✅ **LULUS LEVEL BOSS!**")
                            if not st.session_state.get(f"koin_diberikan_{i}", False):
                                st.session_state[f"koin_diberikan_{i}"] = True
                                if not is_lulus:
                                    st.session_state.saldo_igil += 100
                                    st.session_state.tracker_penguasaan[KUNCI_PELACAKAN] += 1
                                    if st.session_state.tracker_penguasaan[KUNCI_PELACAKAN] >= BATAS_MASTER:
                                        st.session_state.sertifikat_lulus.append(KUNCI_PELACAKAN)
                                        st.balloons()
                                st.rerun()
                        else:
                            st.error(f"❌ **GAGAL/TIMEOUT! Nyawa berkurang 1.**\n\nAlasan AI: {hasil_teks}")
                            if st.button("🔄 Minta Soal Baru", key=f"btn_ganti_{i}"):
                                resp = client_gemini.models.generate_content(model='gemini-3.6-flash', contents=[f"Buat 1 soal HOTS lisan BARU yg berbeda dari '{soal_lisan_bersih}'. Format: [UJIAN LISAN] Soal?|||LISAN"])
                                st.session_state.daftar_kuis[i]['soal'] = resp.text.split("|||")[0].strip()
                                st.session_state[boss_key] = "idle"
                                st.rerun()

# ==========================================
# TAB 2: PAPAN PERINGKAT (LEADERBOARD)
# ==========================================
with tab_leaderboard:
    st.markdown("### 🏆 Papan Peringkat Nasional")
    semua_pemain = st.session_state.leaderboard.copy()
    semua_pemain.append({"Nama": f"{nama} (Kamu)", "Saldo": st.session_state.saldo_igil})
    semua_pemain = sorted(semua_pemain, key=lambda x: x['Saldo'], reverse=True)
    
    html_leaderboard = "<div style='background-color:#FAFAFA; padding:20px; border-radius:10px;'>"
    for idx, p in enumerate(semua_pemain):
        medali = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else "🎓"
        warna_bg = "#E3F2FD" if "(Kamu)" in p['Nama'] else "#FFFFFF"
        html_leaderboard += f"<div style='display:flex; justify-content:space-between; padding:15px; margin-bottom:10px; background-color:{warna_bg}; border-radius:8px; border:1px solid #E0E0E0;'><div style='font-size:18px;'><b>{medali} Peringkat {idx+1}</b> - {p['Nama']}</div><div style='font-size:18px; font-weight:bold; color:#00838F;'>{p['Saldo']} $IGIL</div></div>"
    html_leaderboard += "</div>"
    st.markdown(html_leaderboard, unsafe_allow_html=True)

# ==========================================
# TAB 3: DASHBOARD ORANG TUA (REPORT & TELEGRAM)
# ==========================================
with tab_ortu:
    st.markdown("### 👨‍👩‍👧 Panel Pantau Orang Tua")
    
    # --- 1. RINGKASAN HARI INI ---
    aktivitas_hari_ini = [log for log in st.session_state.histori_belajar if log['tanggal'] == "1 September 2026"]
    
    st.markdown("#### 📅 Aktivitas Hari Ini (1 September 2026)")
    if aktivitas_hari_ini:
        st.success(f"✅ Anak Anda, **{nama}**, SUDAH belajar hari ini!")
        for aksi in aktivitas_hari_ini:
            st.write(f"- Mempelajari **{aksi['mapel']}** (Bab: {aksi['bab']}) dengan skor **{aksi['skor']}** ({aksi['status']})")
    else:
        st.error(f"❌ Anak Anda, **{nama}**, BELUM membuka materi pelajaran apa pun hari ini.")
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- 2. GRAFIK RAPOR VISUAL ---
    st.markdown("#### 📊 Rapor Akademik AI")
    if len(st.session_state.histori_belajar) > 0:
        rata_rata = sum([item['skor'] for item in st.session_state.histori_belajar]) / len(st.session_state.histori_belajar)
        rata_rata = round(rata_rata)
        
        if rata_rata <= 50:
            warna_grafik = "#F44336" # Merah
            warna_bg = "#FFEBEE"
            status_rapor = "🔴 PERLU PERHATIAN EKSTRA"
        elif rata_rata <= 80:
            warna_grafik = "#FFC107" # Kuning
            warna_bg = "#FFF8E1"
            status_rapor = "🟡 CUKUP BAIK"
        else:
            warna_grafik = "#4CAF50" # Hijau
            warna_bg = "#E8F5E9"
            status_rapor = "🟢 SANGAT MEMUASKAN"
            
        html_rapor = f"""
        <div style="background-color: {warna_bg}; padding: 25px; border-radius: 12px; border: 1px solid {warna_grafik}; text-align: center; margin-bottom: 25px;">
            <h3 style="margin-top: 0; color: #333;">Nilai Rata-Rata Keseluruhan</h3>
            <div style="width: 100%; background-color: #E0E0E0; border-radius: 20px; height: 40px; margin: 15px 0; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);">
                <div style="width: {rata_rata}%; background-color: {warna_grafik}; height: 40px; border-radius: 20px 0 0 20px; text-align: right; padding-right: 15px; color: white; font-weight: bold; font-size: 20px; line-height: 40px; transition: width 1s ease-in-out;">
                    {rata_rata}%
                </div>
            </div>
            <h4 style="color: {warna_grafik}; margin-bottom: 0; font-size: 22px;">{status_rapor}</h4>
        </div>
        """
        components.html(html_rapor, height=190)
    else:
        st.info("Belum ada data nilai yang cukup untuk menghasilkan Grafik Rapor.")

    # --- 3. HISTORI BELAJAR LENGKAP ---
    st.markdown("#### 📚 Riwayat Historis Belajar")
    st.dataframe(
        st.session_state.histori_belajar,
        column_config={
            "tanggal": "Tanggal",
            "mapel": "Mata Pelajaran",
            "bab": "Topik/Bab",
            "skor": st.column_config.NumberColumn("Skor", format="%d/100"),
            "status": "Hasil Akhir"
        },
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    st.markdown("#### 📲 Integrasi Notifikasi Handphone")
    no_tele = st.text_input("ID/Nomor Telegram Ayah/Bunda:", placeholder="@username_ayah atau 08123456...")
    if st.button("Kirim Rapor Ini ke Telegram", use_container_width=True):
        if no_tele:
            with st.spinner("Menghubungkan ke API Telegram Bot..."):
                time.sleep(1.5)
                st.success(f"✅ Rapor interaktif berhasil dikirim ke perangkat Telegram: {no_tele}!")
        else:
            st.warning("Masukkan ID Telegram terlebih dahulu!")
