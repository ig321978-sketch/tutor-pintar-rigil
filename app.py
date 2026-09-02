import streamlit as st
import streamlit.components.v1 as components
import re
import time
import json
import base64
import uuid
import os
from datetime import datetime
from PIL import Image
from google import genai
from google.genai import types
from google.cloud import texttospeech
from google.oauth2 import service_account
from supabase import create_client, Client

# --- KONFIGURASI APLIKASI ---
BATAS_MASTER = 5 
NYAWA_MAKSIMAL = 3

st.set_page_config(page_title="$IGIL - Learn to Earn", page_icon="🎓", layout="centered")

# --- INISIALISASI KONEKSI SUPABASE ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
    koneksi_db_aktif = True
except Exception as e:
    koneksi_db_aktif = False
    st.error(f"Gagal terhubung ke Database: {e}")

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

# --- INISIALISASI SESSION STATE LOKAL ---
if 'berhasil_baca' not in st.session_state: st.session_state.berhasil_baca = False
if 'tag_materi' not in st.session_state: st.session_state.tag_materi = ""
if 'naskah_layar' not in st.session_state: st.session_state.naskah_layar = ""
if 'img_prompt' not in st.session_state: st.session_state.img_prompt = ""
if 'img_html_final' not in st.session_state: st.session_state.img_html_final = ""
if 'file_suara' not in st.session_state: st.session_state.file_suara = "audio_guru.mp3"
if 'daftar_kuis' not in st.session_state: st.session_state.daftar_kuis = []
if 'guru_aktif' not in st.session_state: st.session_state.guru_aktif = DATA_GURU["SD"][0] 
if 'tampilkan_toko' not in st.session_state: st.session_state.tampilkan_toko = False
if 'nama_siswa' not in st.session_state: st.session_state.nama_siswa = ""
if 'sudah_login' not in st.session_state: st.session_state.sudah_login = False

# --- KONFIGURASI API GOOGLE ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = "MASUKKAN_KUNCI"
client_gemini = genai.Client(api_key=API_KEY)

try:
    gcp_json_str = st.secrets.get("GOOGLE_CREDENTIALS_JSON", "")
    if gcp_json_str:
        gcp_creds_dict = json.loads(gcp_json_str)
        gcp_credentials = service_account.Credentials.from_service_account_info(gcp_creds_dict)
        client_tts = texttospeech.TextToSpeechClient(credentials=gcp_credentials)
    else:
        client_tts = None
except:
    client_tts = None

def buat_suara_google(teks, nama_file, nama_suara, pitch_guru, rate_guru):
    if not client_tts: return False
    try:
        synthesis_input = texttospeech.SynthesisInput(text=teks)
        voice = texttospeech.VoiceSelectionParams(language_code="id-ID", name=nama_suara)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=rate_guru, pitch=pitch_guru)
        response = client_tts.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        with open(nama_file, "wb") as out: out.write(response.audio_content)
        return True
    except Exception as e:
        print(f"Gagal generate suara: {e}")
        return False

# --- FUNGSI LOGIKA KURIKULUM MERDEKA ---
def get_mapel_list(kelas):
    if "SD" in kelas:
        if "Kelas 1" in kelas or "Kelas 2" in kelas: return ["Matematika", "Bahasa Indonesia", "Pendidikan Pancasila", "Bahasa Inggris", "Seni & Prakarya", "PJOK"]
        else: return ["Matematika", "Bahasa Indonesia", "IPAS", "Pendidikan Pancasila", "Bahasa Inggris", "Seni & Prakarya", "PJOK"]
    elif "SMP" in kelas: return ["Matematika", "Bahasa Indonesia", "IPA", "IPS", "Bahasa Inggris", "Pendidikan Pancasila", "Informatika", "Seni Budaya", "PJOK", "Prakarya"]
    elif "SMA" in kelas:
        if "Kelas 10" in kelas: return ["Matematika", "Bahasa Indonesia", "IPA Terpadu", "IPS Terpadu", "Bahasa Inggris", "Pendidikan Pancasila", "Informatika", "Seni Budaya", "PJOK"]
        else: return ["Matematika Wajib", "Matematika Tingkat Lanjut", "Fisika", "Kimia", "Biologi", "Ekonomi", "Sosiologi", "Geografi", "Sejarah", "Bahasa Indonesia", "Bahasa Inggris", "Pendidikan Pancasila", "Informatika", "PJOK"]
    return []

def get_bab_list(kelas, mapel):
    if "SD" in kelas:
        if mapel == "Matematika": return ["Bab 1: Bilangan Cacah sampai 1.000", "Bab 2: Penjumlahan & Pengurangan", "Bab 3: Perkalian & Pembagian", "Bab 4: Pecahan Sederhana", "Bab 5: Pengukuran Panjang, Berat, & Waktu", "Bab 6: Keliling & Bangun Datar"]
        if mapel == "IPAS": return ["Bab 1: Mari Kenali Hewan di Sekitarmu", "Bab 2: Siklus Hidup Makhluk Hidup", "Bab 3: Hidup Bersama Alam", "Bab 4: Benda dan Sifatnya", "Bab 5: Energi di Sekitar Kita", "Bab 6: Permukaan Bumi"]
        if mapel == "Bahasa Indonesia": return ["Bab 1: Mari Bermain & Belajar", "Bab 2: Kawan Seiring", "Bab 3: Pengalamanku", "Bab 4: Cuaca di Sekitarku", "Bab 5: Berkomunikasi yang Baik"]
        if mapel == "Pendidikan Pancasila": return ["Bab 1: Aku Anak Indonesia", "Bab 2: Mengenal Lambang Negara", "Bab 3: Hak dan Kewajibanku di Rumah & Sekolah", "Bab 4: Kebersamaan dalam Keberagaman"]
    if "SMP" in kelas:
        if mapel == "Matematika": return ["Bab 1: Bilangan Berpangkat & Bentuk Akar", "Bab 2: Persamaan & Pertidaksamaan Linear", "Bab 3: Fungsi Kuadrat", "Bab 4: Teorema Pythagoras", "Bab 5: Transformasi Geometri", "Bab 6: Kesebangunan & Kekongruenan", "Bab 7: Bangun Ruang Sisi Datar & Lengkung", "Bab 8: Statistika & Peluang"]
        if mapel == "IPA": return ["Bab 1: Besaran & Pengukuran", "Bab 2: Klasifikasi Makhluk Hidup", "Bab 3: Suhu, Kalor, & Pemuaian", "Bab 4: Gerak & Gaya", "Bab 5: Sistem Pencernaan & Pernapasan", "Bab 6: Sistem Peredaran Darah", "Bab 7: Tekanan Zat", "Bab 8: Listrik Statis & Dinamis", "Bab 9: Kemagnetan & Induksi Elektromagnetik"]
        if mapel == "IPS": return ["Bab 1: Keadaan Alam & Aktivitas Penduduk Indonesia", "Bab 2: Dinamika Kependudukan & Pembangunan", "Bab 3: Perubahan Sosial Budaya & Globalisasi", "Bab 4: Interaksi Antarruang & Dampaknya", "Bab 5: Masa Kemerdekaan hingga Reformasi"]
        if mapel == "Informatika": return ["Bab 1: Berpikir Komputasional", "Bab 2: Sistem Komputer", "Bab 3: Jaringan Komputer & Internet", "Bab 4: Analisis Data", "Bab 5: Algoritma & Pemrograman"]
    if "SMA" in kelas and "Kelas 10" not in kelas:
        if mapel == "Fisika": return ["Bab 1: Listrik Statis & Dinamis", "Bab 2: Medan Magnet & Induksi Elektromagnetik", "Bab 3: Rangkaian Arus Bolak-Balik (AC)", "Bab 4: Gelombang Elektromagnetik", "Bab 5: Relativitas Khusus", "Bab 6: Konsep Fotokimia & Kuantum", "Bab 7: Fisika Inti & Radioaktivitas"]
        if mapel == "Kimia": return ["Bab 1: Struktur Atom & Tabel Periodik", "Bab 2: Ikatan Kimia", "Bab 3: Stoikiometri & Laju Reaksi", "Bab 4: Kesetimbangan Kimia", "Bab 5: Larutan Asam Basa & Penyangga", "Bab 6: Sifat Koligatif Larutan", "Bab 7: Reaksi Redoks & Elektrokimia", "Bab 8: Kimia Karbon & Makromolekul"]
        if mapel == "Biologi": return ["Bab 1: Struktur & Fungsi Sel", "Bab 2: Sistem Gerak & Sirkulasi", "Bab 3: Sistem Pencernaan & Pernapasan", "Bab 4: Sistem Koordinasi, Hormon & Saraf", "Bab 5: Reproduksi Manusia", "Bab 6: Pertumbuhan & Perkembangan", "Bab 7: Metabolisme & Enzim", "Bab 8: Pewarisan Sifat (Genetika)", "Bab 9: Evolusi", "Bab 10: Bioteknologi"]
        if mapel == "Ekonomi": return ["Bab 1: Konsep Dasar Ilmu Ekonomi", "Bab 2: Keseimbangan Pasar & Struktur Pasar", "Bab 3: Lembaga Jasa Keuangan", "Bab 4: Pendapatan Nasional & Kesenjangan", "Bab 5: APBN & APBD", "Bab 6: Kebijakan Moneter & Fiskal", "Bab 7: Akuntansi Perusahaan Jasa", "Bab 8: Akuntansi Perusahaan Dagang"]
        if mapel == "Sosiologi": return ["Bab 1: Kelompok Sosial dalam Masyarakat", "Bab 2: Permasalahan Sosial Akibat Globalisasi", "Bab 3: Perbedaan, Kesetaraan, & Harmoni Sosial", "Bab 4: Konflik Sosial & Resolusi", "Bab 5: Kearifan Lokal & Pemberdayaan Komunitas"]
    return [f"Bab 1: Pendahuluan {mapel}", f"Bab 2: Konsep Dasar {mapel}", f"Bab 3: Analisis {mapel}"]

# --- HEADER GLOBAL APLIKASI ---
st.title("🎓 $IGIL")
st.markdown("### *Learn to Earn Concept*")

# ==========================================
# HALAMAN LOGIN
# ==========================================
if not st.session_state.sudah_login:
    st.markdown("---")
    st.markdown("### 👋 Selamat Datang! Silakan Masuk")
    st.info("Masukkan nama kamu untuk memulai belajar dan mengumpulkan POINT KAMU.")
    with st.form("formulir_login"):
        input_nama = st.text_input("Nama Siswa:", placeholder="Contoh: Jagoan")
        btn_masuk = st.form_submit_button("Masuk 🚀", use_container_width=True)
        if btn_masuk:
            if input_nama.strip() == "": st.warning("Nama tidak boleh kosong!")
            else:
                st.session_state.nama_siswa = input_nama.strip()
                st.session_state.sudah_login = True
                st.rerun()
    st.stop() 

# ==========================================
# APLIKASI UTAMA
# ==========================================
nama_siswa = st.session_state.nama_siswa
siswa_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, nama_siswa.lower()))

col_header1, col_header2 = st.columns([3, 1])
with col_header1: st.success(f"Masuk sebagai: **{nama_siswa}**")
with col_header2:
    if st.button("Keluar / Ganti Akun"):
        st.session_state.sudah_login = False
        st.session_state.nama_siswa = ""
        st.rerun()

# SINKRONISASI DATABASE
saldo_saat_ini, nyawa_saat_ini, penguasaan_materi = 0, NYAWA_MAKSIMAL, 0
data_histori_db, data_leaderboard_db = [], []

if koneksi_db_aktif:
    try:
        profil_resp = supabase.table("profil_siswa").select("*").eq("id", siswa_id).execute()
        if not profil_resp.data:
            supabase.table("profil_siswa").insert({"id": siswa_id, "nama": nama_siswa, "jenjang_kelas": "Belum Diatur", "saldo_igil": 0, "nyawa_belajar": NYAWA_MAKSIMAL}).execute()
        else:
            saldo_saat_ini = profil_resp.data[0]["saldo_igil"]
            nyawa_saat_ini = profil_resp.data[0]["nyawa_belajar"]
        histori_resp = supabase.table("histori_belajar").select("*").eq("siswa_id", siswa_id).order("created_at", desc=True).execute()
        data_histori_db = histori_resp.data
        if st.session_state.tag_materi:
            progres_resp = supabase.table("histori_belajar").select("id").eq("siswa_id", siswa_id).eq("bab", st.session_state.tag_materi).execute()
            penguasaan_materi = len(progres_resp.data)
        lb_resp = supabase.table("profil_siswa").select("nama, saldo_igil").order("saldo_igil", desc=True).limit(10).execute()
        data_leaderboard_db = lb_resp.data
    except Exception as e:
        st.warning(f"Terjadi kendala sinkronisasi Database: {e}")

# BANNER STATUS
st.markdown(f"""
<div style="background-color: #E0F7FA; padding: 15px 25px; border-radius: 12px; border-left: 8px solid #00BCD4; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <div><div style="font-size: 16px; font-weight: bold; color: #00838F;">💰 POINT KAMU:</div><div style="font-size: 26px; font-weight: 900; color: #00838F;">{saldo_saat_ini} POINT KAMU</div></div>
    <div style="text-align: right;"><div style="font-size: 16px; font-weight: bold; color: #D32F2F;">❤️ Nyawa Belajar:</div><div style="font-size: 26px; font-weight: 900; color: #D32F2F;">{nyawa_saat_ini} / {NYAWA_MAKSIMAL}</div></div>
</div>
""", unsafe_allow_html=True)

if nyawa_saat_ini <= 0:
    st.error("💔 Yaah! Nyawa belajarmu habis karena terlalu banyak menjawab salah.")
    if st.button("💊 Beli 3 Nyawa (Harga: 50 POINT KAMU)") and saldo_saat_ini >= 50 and koneksi_db_aktif:
        supabase.table("profil_siswa").update({"saldo_igil": saldo_saat_ini - 50, "nyawa_belajar": NYAWA_MAKSIMAL}).eq("id", siswa_id).execute()
        st.success("Nyawa diisi penuh! Memuat ulang...")
        time.sleep(1.5)
        st.rerun()
    elif saldo_saat_ini < 50:
        st.warning("POINT KAMU tidak cukup untuk membeli nyawa. Kembalilah besok!")
    st.stop() 

tab_belajar, tab_rapor, tab_leaderboard = st.tabs(["📚 Ruang Belajar", "👨‍👩‍👧 Rapor Anak", "🏆 Papan Peringkat"])

# ==========================================
# TAB 1: RUANG BELAJAR
# ==========================================
with tab_belajar:
    st.markdown("---")
    mode_belajar = st.radio("Pilih Sumber Materi:", ["📸 Unggah Foto Buku", "📑 Pilih Topik (Kurikulum)"], horizontal=True)

    col_kelas, col_mapel = st.columns(2)
    with col_kelas: 
        jenjang_kelas = st.selectbox("Jenjang & Kelas:", ["SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6", "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9", "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"], index=2)
    jenjang_inti = jenjang_kelas.split(" - ")[0] 
    
    with col_mapel: 
        daftar_mapel_dinamis = get_mapel_list(jenjang_kelas)
        daftar_mapel_dinamis.append("LAINNYA (ketik disini)")
        pilihan_mapel = st.selectbox("Mata Pelajaran:", daftar_mapel_dinamis)
        if pilihan_mapel == "LAINNYA (ketik disini)": mapel = st.text_input("Ketik Mata Pelajaran spesifik:", placeholder="Contoh: Muatan Lokal / Bahasa Sunda")
        else: mapel = pilihan_mapel

    if mode_belajar == "📸 Unggah Foto Buku":
        uploaded_files = st.file_uploader("Foto Halaman Buku Pelajaran:", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        judul_materi = ""
    else:
        daftar_bab_dinamis = get_bab_list(jenjang_kelas, mapel)
        daftar_bab_dinamis.append("LAINNYA (ketik disini)")
        pilihan_bab = st.selectbox("Pilih Topik/Bab Pembelajaran:", daftar_bab_dinamis)
        if pilihan_bab == "LAINNYA (ketik disini)": judul_materi = st.text_input("Ketik Bab/Topik spesifik:", placeholder="Contoh: Menghitung Luas Segitiga")
        else: judul_materi = pilihan_bab
        uploaded_files = []

    st.markdown("### 👨‍🏫 Pilih Guru Favoritmu!")
    daftar_guru = DATA_GURU[jenjang_inti]
    nama_guru_pilihan = st.radio("Daftar Guru Tersedia:", [g['nama'] for g in daftar_guru], horizontal=True, label_visibility="collapsed")
    guru_terpilih = next(g for g in daftar_guru if g['nama'] == nama_guru_pilihan)

    btn_analisis = st.button("Mulai Belajar! 🚀", use_container_width=True, type="primary")

    if btn_analisis:
        if not mapel: st.warning("Silakan isi Mata Pelajaran!")
        elif mode_belajar == "📸 Unggah Foto Buku" and not uploaded_files: st.warning("Silakan unggah minimal satu foto buku!")
        elif mode_belajar == "📑 Pilih Topik (Kurikulum)" and not judul_materi: st.warning("Silakan ketik atau pilih Topik Pembelajaran!")
        else:
            st.session_state.guru_aktif = guru_terpilih
            st.session_state.img_html_final = ""
            for key in list(st.session_state.keys()):
                if key.startswith('status_soal_') or key.startswith('koin_diberikan_') or key.startswith('boss_'): del st.session_state[key]
            if koneksi_db_aktif: supabase.table("profil_siswa").update({"jenjang_kelas": jenjang_kelas}).eq("id", siswa_id).execute()
                 
            nama_asli_guru = st.session_state.guru_aktif['nama'].split('(')[0].strip()
            
            if os.path.exists(st.session_state.file_suara):
                os.remove(st.session_state.file_suara)
            
            with st.spinner(f"{nama_asli_guru} sedang menyusun materi dan memanggil pelukis AI Imagen 3..."):
                
                # LANGKAH 1: Gemini 1.5 Flash membuat naskah dan mengekstrak Prompt Gambar
                instruksi_format = """
                Keluarkan 4 bagian berurutan:
                ===TAG_MATERI=== (Maksimal 3 kata)
                ===PROMPT_GAMBAR=== (WAJIB: Tuliskan deskripsi inti visual dalam BAHASA INGGRIS, fokus pada objek, latar, pencahayaan, sesuai materi. DILARANG bahasa Indonesia.)
                ===NASKAH_LAYAR=== 
                (Tuliskan materi pelajaran SEPERTI SLIDE PRESENTASI menggunakan HTML. DILARANG memasukkan tag <img> di sini. 
                Gunakan struktur "Kartu" seperti ini:
                   <div style="background: linear-gradient(135deg, #ffffff, #f4f9fb); border-radius: 16px; padding: 25px; margin-bottom: 25px; box-shadow: 0 8px 16px rgba(0,0,0,0.06); border-left: 6px solid #2AB3FF; font-family: sans-serif;">
                       <h3 style="color: #00838F; margin-top: 0;">Judul Sub-topik</h3>
                       <p style="color: #444; line-height: 1.8; font-size: 16px;">Penjelasan...</p>
                   </div>
                )
                ===KUIS=== (5 soal. Soal 4: [SIMULASI UJIAN NASIONAL HOTS] Pertanyaan?|||Opsi 1|||Opsi 2|||Opsi 3|||Kunci. Soal 5: [UJIAN LISAN] Pertanyaan?|||LISAN)
                """
                payload_ai = [f"Kamu Tutor AI {mapel} bernama {nama_asli_guru}. Susun materi: '{judul_materi}' untuk {nama_siswa} kelas {jenjang_kelas}.\n\n{instruksi_format}"]
                if mode_belajar == "📸 Unggah Foto Buku":
                    payload_ai = [f"Kamu Tutor AI {mapel}. Baca foto buku ini untuk {nama_siswa} kelas {jenjang_kelas}.\n\n{instruksi_format}"] + [Image.open(f) for f in uploaded_files]

                try:
                    response = client_gemini.models.generate_content(model='gemini-3.6-flash', contents=payload_ai)
                    full_text = response.text
                    
                    if "===TAG_MATERI===" in full_text:
                        tag_mentah = re.search(r'===TAG_MATERI===(.*?)(?====PROMPT_GAMBAR===|===NASKAH_LAYAR===|$)', full_text, re.DOTALL).group(1).strip().upper()
                        st.session_state.tag_materi = "".join(e for e in tag_mentah if e.isalnum() or e.isspace())
                    
                    if "===PROMPT_GAMBAR===" in full_text:
                        prompt_mentah = re.search(r'===PROMPT_GAMBAR===(.*?)(?====NASKAH_LAYAR===|$)', full_text, re.DOTALL)
                        if prompt_mentah: st.session_state.img_prompt = prompt_mentah.group(1).strip()
                    
                    if "===NASKAH_LAYAR===" in full_text: 
                        naskah_kotor = re.search(r'===NASKAH_LAYAR===(.*?)(?====KUIS===|$)', full_text, re.DOTALL).group(1).strip()
                        st.session_state.naskah_layar = naskah_kotor.replace('\n', '')
                        
                        teks_suara_murni = re.sub(r'<[^>]+>', '', naskah_kotor) 
                        teks_suara_murni = re.sub(r'[*#_`>-]', '', teks_suara_murni) 
                        buat_suara_google(teks_suara_murni, st.session_state.file_suara, guru_terpilih['voice'], guru_terpilih['pitch'], guru_terpilih['rate'])
                    
                    if "===KUIS===" in full_text:
                        lines = [line for line in re.search(r'===KUIS===(.*)', full_text, re.DOTALL).group(1).strip().split('\n') if '|||' in line]
                        parsed_kuis = []
                        for line in lines:
                            parts = line.split("|||")
                            if len(parts) == 2 and "LISAN" in parts[1]: parsed_kuis.append({"tipe": "lisan", "soal": parts[0].strip()})
                            elif len(parts) >= 5: parsed_kuis.append({"tipe": "pg", "soal": parts[0].strip(), "opsi": [parts[1].strip(), parts[2].strip(), parts[3].strip()], "kunci": parts[4].strip()})
                        st.session_state.daftar_kuis = parsed_kuis
                except Exception as e: 
                    st.error(f"Gagal memproses Teks AI: {e}")

            # LANGKAH 2: Menggunakan IMAGEN 3 dari Kode Anda
            if hasattr(st.session_state, 'img_prompt') and st.session_state.img_prompt:
                with st.spinner("Sedang menggambar sketsa dengan Google Imagen 3..."):
                    try:
                        # Menambahkan gaya spesifik (seperti kode Anda)
                        prompt_sketsa = f"{st.session_state.img_prompt}, rough pencil sketch style, black and white, educational textbook art, clean background, completely no text"
                        
                        respons_gambar = client_gemini.models.generate_images(
                            model='imagen-3.0-generate-001',
                            prompt=prompt_sketsa,
                            config=dict(
                                number_of_images=1,
                                aspect_ratio="4:3",
                                output_mime_type="image/jpeg"
                            )
                        )
                        
                        # Mengambil byte gambar dan mengonversinya ke Base64 untuk ditampilkan di Web
                        gambar_bytes = respons_gambar.generated_images[0].image.image_bytes
                        img_b64 = base64.b64encode(gambar_bytes).decode('utf-8')
                        
                        st.session_state.img_html_final = f"""
                        <div style="text-align: center; margin-bottom: 25px;">
                            <img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; max-width: 450px; border-radius: 12px; border: 2px solid #555; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                            <p style="font-size: 13px; color: #555; margin-top: 10px; font-style: italic;">🎨 Sketsa Edukasi AI (Imagen 3)</p>
                        </div>
                        """
                    except Exception as img_error:
                        print(f"Gagal memanggil Imagen 3: {img_error}")
                        # JIKA IMAGEN 3 GAGAL (Mungkin karena Billing belum diatur), tampilkan Peringatan Santun
                        st.session_state.img_html_final = f"""
                        <div style="text-align: center; padding: 15px; background: #FFF3E0; border-radius: 10px; border: 1px dashed #FFB74D; margin-bottom: 25px;">
                            <p style="color: #E65100; margin: 0; font-weight: bold;">⚠️ Gambar Sketsa Premium Tidak Muncul</p>
                            <p style="color: #E65100; font-size: 13px; margin-top: 5px;">Akses Imagen 3 ditolak oleh Google. Pastikan Kunci API Anda berasal dari proyek yang sudah mengaktifkan "Billing" (Kartu Kredit/Debit) di Google Cloud Console.</p>
                        </div>
                        """

            st.session_state.berhasil_baca = True
            st.rerun()

    if st.session_state.berhasil_baca:
        st.markdown("---")
        nama_asli_guru = st.session_state.guru_aktif['nama'].split('(')[0].strip()
        is_lulus = penguasaan_materi >= BATAS_MASTER
        
        if is_lulus:
            st.markdown(f"""
            <div style="background-color: #FFF8E1; padding: 20px; border-radius: 15px; border: 2px dashed #FFC107; text-align: center; margin-bottom: 25px;">
                <h1 style="margin:0; font-size: 40px;">🏆🏅</h1>
                <h3 style="color: #F57F17; margin-top: 10px;">SERTIFIKAT KELULUSAN MASTER</h3>
                <p style="font-size: 16px; color: #555;">Luar biasa! <b>{nama_siswa}</b> telah berhasil menaklukkan materi <b>{st.session_state.tag_materi}</b>.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info(f"📈 Kemajuan Lencana '{st.session_state.tag_materi.title()}': {penguasaan_materi} / {BATAS_MASTER} Tantangan Dikuasai.")

        st.markdown(f"## 🎧 Dengarkan Penjelasan {nama_asli_guru}")
        
        audio_tersedia = os.path.exists(st.session_state.file_suara)
        
        if audio_tersedia:
            with open(st.session_state.file_suara, "rb") as f: audio_b64 = base64.b64encode(f.read()).decode()
            audio_html_element = f"""
            <div style="text-align:center; padding:15px; background:#fff; border-radius:10px; box-shadow:0 2px 8px rgba(0,0,0,0.1); margin-bottom:20px;">
                <audio id="guruAudio" controls style="width: 100%;">
                    <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
                </audio>
                <p style="font-size:12px; color:#888; margin-top:5px;">Tekan tombol Play untuk mulai mendengarkan penjelasan</p>
            </div>
            """
            script_trigger = "audioEl.addEventListener('play', () => {"
        else:
            audio_html_element = """
            <div style="text-align:center; padding:15px; background:#E3F2FD; border-radius:10px; border: 1px solid #90CAF9; margin-bottom:20px;">
                <p style="color: #1565C0; margin:0; font-weight:bold;">✨ Tampilan Mode Presentasi ✍️</p>
                <p style="font-size:13px; color:#1565C0; margin-top:5px;">Sistem sedang menyusun naskah bergaya Gamma untukmu...</p>
            </div>
            """
            script_trigger = "setTimeout(() => {"
            
        # Menggabungkan Gambar Imagen 3 + Teks Materi UI Gamma
        naskah_gabungan = st.session_state.get('img_html_final', '') + st.session_state.naskah_layar
        safe_html = naskah_gabungan.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
        
        html_typewriter = f"""
        {audio_html_element}
        
        <div id="scrollContainer" style="padding:10px; height: 500px; overflow-y: auto; scroll-behavior: smooth; position: relative; background-color: #fcfcfc;">
            <div id="typewriterBox"></div>
        </div>

        <script>
            const rawHTMLText = `{safe_html}`;
            const targetDiv = document.getElementById("typewriterBox");
            const scrollContainer = document.getElementById("scrollContainer");
            const audioEl = document.getElementById("guruAudio");
            
            let isTyping = false;
            let typedText = "";
            let currentIndex = 0;
            let typingInterval;
            
            const typingSpeedMs = 60; 
            
            function typeWriter() {{
                if (currentIndex < rawHTMLText.length) {{
                    if (rawHTMLText.charAt(currentIndex) === '<') {{
                        let tag = "";
                        while (rawHTMLText.charAt(currentIndex) !== '>' && currentIndex < rawHTMLText.length) {{
                            tag += rawHTMLText.charAt(currentIndex);
                            currentIndex++;
                        }}
                        tag += '>';
                        typedText += tag;
                        currentIndex++;
                    }} else {{
                        typedText += rawHTMLText.charAt(currentIndex);
                        currentIndex++;
                    }}
                    targetDiv.innerHTML = typedText;
                    scrollContainer.scrollTop = scrollContainer.scrollHeight;
                }} else {{
                    clearInterval(typingInterval);
                }}
            }}

            {script_trigger}
                if (!isTyping) {{
                    isTyping = true;
                    typedText = "";
                    currentIndex = 0;
                    targetDiv.innerHTML = "";
                    typingInterval = setInterval(typeWriter, typingSpeedMs);
                }}
            {'});' if audio_tersedia else '}, 1000);'}

            if(audioEl) {{
                audioEl.addEventListener('pause', () => {{
                    clearInterval(typingInterval);
                    isTyping = false;
                }});
                
                audioEl.addEventListener('ended', () => {{
                    clearInterval(typingInterval);
                    targetDiv.innerHTML = rawHTMLText;
                    setTimeout(() => {{ scrollContainer.scrollTop = scrollContainer.scrollHeight; }}, 100);
                }});
            }}
        </script>
        """
        components.html(html_typewriter, height=620)

        st.markdown("---")
        st.markdown(f"## 🏆 Latihan & Dapatkan POINT KAMU!")
        
        if st.session_state.daftar_kuis:
            for i, q in enumerate(st.session_state.daftar_kuis):
                if q['tipe'] == "pg":
                    is_hots = "[SIMULASI" in q['soal'].upper()
                    st.markdown(f"**{i+1}. {q['soal'].replace('[SIMULASI UJIAN NASIONAL HOTS]', '🔥 [TANTANGAN LOGIKA]')}**")
                    jawaban_user = st.radio("Pilih jawaban:", q['opsi'], key=f"soal_radio_{i}", index=None, label_visibility="collapsed")
                    
                    if st.button(f"Cek Jawaban Soal {i+1}", key=f"btn_cek_{i}"):
                        if jawaban_user == q['kunci']:
                            st.session_state[f"status_soal_{i}"] = "benar"
                            if not st.session_state.get(f"koin_diberikan_{i}", False):
                                st.session_state[f"koin_diberikan_{i}"] = True
                                if not is_lulus and koneksi_db_aktif:
                                    hadiah = 50 if is_hots else 10
                                    supabase.table("profil_siswa").update({"saldo_igil": saldo_saat_ini + hadiah}).eq("id", siswa_id).execute()
                                    log_baru = {"siswa_id": siswa_id, "mapel": mapel, "bab": st.session_state.tag_materi.title(), "skor": 100 if is_hots else 80, "status_lulus": is_hots}
                                    supabase.table("histori_belajar").insert(log_baru).execute()
                                    if not is_lulus and penguasaan_materi + 1 >= BATAS_MASTER: st.balloons()
                                st.rerun()
                        elif jawaban_user is not None:
                            st.session_state[f"status_soal_{i}"] = "salah"
                            if koneksi_db_aktif:
                                supabase.table("profil_siswa").update({"nyawa_belajar": nyawa_saat_ini - 1}).eq("id", siswa_id).execute()
                                log_salah = {"siswa_id": siswa_id, "mapel": mapel, "bab": st.session_state.tag_materi.title(), "skor": 0, "status_lulus": False}
                                supabase.table("histori_belajar").insert(log_salah).execute()
                            st.rerun()
                    
                    status = st.session_state.get(f"status_soal_{i}")
                    if status == "benar": st.success("Tepat sekali! ⭐")
                    elif status == "salah": st.error("❌ Salah! Nyawa berkurang 1.")
                    st.write("")
                    
                elif q['tipe'] == "lisan":
                    boss_key, start_key = f"boss_state_{i}", f"boss_start_{i}"
                    if boss_key not in st.session_state: st.session_state[boss_key] = "idle" 
                    
                    st.markdown("---")
                    st.markdown(f"### 🐉 LEVEL BOSS: Ujian Lisan Berwaktu!")
                    soal_lisan_bersih = q['soal'].replace("[UJIAN LISAN]", "").strip()
                    st.markdown(f"**Pertanyaan:** {soal_lisan_bersih}")
                    
                    if st.session_state[boss_key] == "idle":
                        if st.button("▶️ Mulai Jawab! (45 Detik)", key=f"btn_mulai_{i}"):
                            st.session_state[boss_key], st.session_state[start_key] = "active", time.time()
                            st.rerun()
                    elif st.session_state[boss_key] == "active":
                        sisa_waktu = int(45 - (time.time() - st.session_state[start_key]))
                        if sisa_waktu > 0:
                            st.warning(f"⏱️ Sisa Waktu: {sisa_waktu} Detik")
                            jawaban_audio_lisan = st.audio_input("Rekam Penjelasanmu:", key=f"audio_ujian_{i}")
                            if st.button("Serahkan Ujian Lisan! 🎙️", key=f"btn_lisan_{i}") and jawaban_audio_lisan:
                                with st.spinner("Menganalisis suaramu..."):
                                    try:
                                        resp_eval = client_gemini.models.generate_content(model='gemini-3.6-flash', contents=[f"Evaluasi lisan untuk soal: '{soal_lisan_bersih}'. Beri [STATUS] LULUS atau GAGAL.", types.Part.from_bytes(data=jawaban_audio_lisan.read(), mime_type='audio/wav')])
                                        st.session_state[f"boss_hasil_{i}"] = resp_eval.text
                                        st.session_state[boss_key] = "evaluated"
                                        if "[STATUS] GAGAL" in resp_eval.text.upper() and koneksi_db_aktif:
                                            supabase.table("profil_siswa").update({"nyawa_belajar": nyawa_saat_ini - 1}).eq("id", siswa_id).execute()
                                            supabase.table("histori_belajar").insert({"siswa_id": siswa_id, "mapel": mapel, "bab": st.session_state.tag_materi.title(), "skor": 20, "status_lulus": False}).execute()
                                        st.rerun()
                                    except: st.error("Gagal memeriksa.")
                        else:
                            st.session_state[boss_key] = "timeout"
                            if koneksi_db_aktif:
                                supabase.table("profil_siswa").update({"nyawa_belajar": nyawa_saat_ini - 1}).eq("id", siswa_id).execute()
                                supabase.table("histori_belajar").insert({"siswa_id": siswa_id, "mapel": mapel, "bab": st.session_state.tag_materi.title(), "skor": 0, "status_lulus": False}).execute()
                            st.rerun()
                    elif st.session_state[boss_key] in ["timeout", "evaluated"]:
                        hasil_teks = st.session_state.get(f"boss_hasil_{i}", "Waktu Habis!")
                        if "[STATUS] LULUS" in hasil_teks.upper():
                            st.success("✅ **LULUS LEVEL BOSS!**")
                            if not st.session_state.get(f"koin_diberikan_{i}", False):
                                st.session_state[f"koin_diberikan_{i}"] = True
                                if not is_lulus and koneksi_db_aktif:
                                    supabase.table("profil_siswa").update({"saldo_igil": saldo_saat_ini + 100}).eq("id", siswa_id).execute()
                                    supabase.table("histori_belajar").insert({"siswa_id": siswa_id, "mapel": mapel, "bab": st.session_state.tag_materi.title(), "skor": 100, "status_lulus": True}).execute()
                                    if not is_lulus and penguasaan_materi + 1 >= BATAS_MASTER: st.balloons()
                                st.rerun()
                        else:
                            st.error(f"❌ **GAGAL/TIMEOUT! Nyawa berkurang 1.**\n\nAlasan AI: {hasil_teks}")
                            if st.button("🔄 Minta Soal Baru", key=f"btn_ganti_{i}"):
                                resp = client_gemini.models.generate_content(model='gemini-3.6-flash', contents=[f"Buat 1 soal HOTS lisan BARU yg berbeda dari '{soal_lisan_bersih}'. Format: [UJIAN LISAN] Soal?|||LISAN"])
                                st.session_state.daftar_kuis[i]['soal'] = resp.text.split("|||")[0].strip()
                                st.session_state[boss_key] = "idle"
                                st.rerun()

# ==========================================
# TAB 2: RAPOR ANAK (REAL DATA DATABASE)
# ==========================================
with tab_rapor:
    st.markdown("### 👨‍👩‍👧 Rapor Anak")
    hari_ini = datetime.now().strftime("%Y-%m-%d")
    aktivitas_hari_ini = [log for log in data_histori_db if str(log.get('created_at', '')).startswith(hari_ini)]
    
    st.markdown(f"#### 📅 Aktivitas Hari Ini")
    if aktivitas_hari_ini:
        st.success(f"✅ Anak Anda, **{nama_siswa}**, SUDAH belajar hari ini!")
        for aksi in aktivitas_hari_ini[:3]:
            st.write(f"- Mempelajari **{aksi.get('mapel')}** (Bab: {aksi.get('bab')}) - Status: {'Lulus/Benar' if aksi.get('status_lulus') else 'Belajar/Salah'}")
    else:
        st.error(f"❌ Anak Anda, **{nama_siswa}**, BELUM membuka materi pelajaran apa pun hari ini.")
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 📊 Rapor Akademik Keseluruhan")
    if len(data_histori_db) > 0:
        rata_rata = sum([item['skor'] for item in data_histori_db]) / len(data_histori_db)
        rata_rata = round(rata_rata)
        warna_grafik, warna_bg, status_rapor = ("#F44336", "#FFEBEE", "🔴 PERLU PERHATIAN EKSTRA") if rata_rata <= 50 else ("#FFC107", "#FFF8E1", "🟡 CUKUP BAIK") if rata_rata <= 80 else ("#4CAF50", "#E8F5E9", "🟢 SANGAT MEMUASKAN")
            
        components.html(f"""
        <div style="background-color: {warna_bg}; padding: 25px; border-radius: 12px; border: 1px solid {warna_grafik}; text-align: center; margin-bottom: 25px;">
            <h3 style="margin-top: 0; color: #333;">Nilai Rata-Rata Keseluruhan</h3>
            <div style="width: 100%; background-color: #E0E0E0; border-radius: 20px; height: 40px; margin: 15px 0; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);">
                <div style="width: {rata_rata}%; background-color: {warna_grafik}; height: 40px; border-radius: 20px 0 0 20px; text-align: right; padding-right: 15px; color: white; font-weight: bold; font-size: 20px; line-height: 40px;">{rata_rata}%</div>
            </div>
            <h4 style="color: {warna_grafik}; margin-bottom: 0; font-size: 22px;">{status_rapor}</h4>
        </div>
        """, height=190)
    else:
        st.info("Belum ada riwayat pengerjaan soal kuis untuk memunculkan rapor.")

    st.markdown("#### 📚 Riwayat Historis Belajar")
    if data_histori_db:
        st.dataframe([{"Tanggal": log.get('created_at', '')[:10], "Mata Pelajaran": log.get("mapel"), "Topik/Bab": log.get("bab"), "Skor": log.get("skor"), "Status Akhir": "Berhasil Lulus" if log.get("status_lulus") else "Belajar/Gagal"} for log in data_histori_db], use_container_width=True, hide_index=True)
    else:
        st.write("Belum ada data.")

# ==========================================
# TAB 3: PAPAN PERINGKAT
# ==========================================
with tab_leaderboard:
    st.markdown("### 🏆 Papan Peringkat Nasional")
    if not data_leaderboard_db:
        st.info("Papan peringkat masih kosong. Jadilah yang pertama!")
    else:
        html_leaderboard = "<div style='background-color:#FAFAFA; padding:20px; border-radius:10px;'>"
        for idx, p in enumerate(data_leaderboard_db):
            medali = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else "🎓"
            warna_bg = "#E3F2FD" if p['nama'] == nama_siswa else "#FFFFFF"
            html_leaderboard += f"<div style='display:flex; justify-content:space-between; padding:15px; margin-bottom:10px; background-color:{warna_bg}; border-radius:8px; border:1px solid #E0E0E0;'><div style='font-size:18px;'><b>{medali} Peringkat {idx+1}</b> - {p['nama']}</div><div style='font-size:18px; font-weight:bold; color:#00838F;'>{p['saldo_igil']} POINT KAMU</div></div>"
        html_leaderboard += "</div>"
        st.markdown(html_leaderboard, unsafe_allow_html=True)