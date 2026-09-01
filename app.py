import streamlit as st
import time
import json
from supabase import create_client, Client
import google.generativeai as genai
from google.oauth2 import service_account
from google.cloud import texttospeech
from PIL import Image

# ==========================================
# 1. KONFIGURASI HALAMAN & CREDENTIALS
# ==========================================
st.set_page_config(page_title="Tutor Pintar Rigil", page_icon="🎓", layout="centered")

# Inisialisasi Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_supabase()

# Inisialisasi Gemini AI
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Inisialisasi Google Cloud TTS
@st.cache_resource
def init_tts_client():
    creds_json = st.secrets["GOOGLE_CREDENTIALS_JSON"]
    if isinstance(creds_json, str):
        creds_info = json.loads(creds_json)
    else:
        creds_info = creds_json
    credentials = service_account.Credentials.from_service_account_info(creds_info)
    return texttospeech.TextToSpeechClient(credentials=credentials)

tts_client = init_tts_client()

# ==========================================
# 2. FUNGSI PENDUKUNG (AUDIO & VISUAL)
# ==========================================
def buat_suara(teks, guru):
    """Menghasilkan audio dari teks menggunakan GCP TTS"""
    synthesis_input = texttospeech.SynthesisInput(text=teks)
    name = "id-ID-Standard-A" if "Nisa" in guru else "id-ID-Standard-B"
    voice = texttospeech.VoiceSelectionParams(language_code="id-ID", name=name)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=0.9)
    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    return response.audio_content

def efek_mengetik(teks, jeda=0.04):
    """Memunculkan teks perlahan seperti mesin tik"""
    for kata in teks.split():
        yield kata + " "
        time.sleep(jeda)

# ==========================================
# 3. ANTARMUKA UTAMA APLIKASI
# ==========================================
st.title("🎓 $IGIL")
st.markdown("### *Learn to Earn Concept*")

# --- SISTEM LOGIN SEMALAM ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""

if not st.session_state.logged_in:
    nama_input = st.text_input("Masuk sebagai:", placeholder="Ketik nama kamu di sini...")
    if st.button("Masuk", type="primary"):
        if nama_input:
            st.session_state.user_name = nama_input
            st.session_state.logged_in = True
            st.rerun()
else:
    # Header Login Aktif & Tombol Keluar
    col_login1, col_login2 = st.columns([3, 1])
    with col_login1:
        st.success(f"Masuk sebagai: **{st.session_state.user_name}**")
    with col_login2:
        if st.button("Keluar / Ganti Akun", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_name = ""
            st.rerun()

    # Sinkronisasi Database Supabase
    try:
        response = supabase.table("profil_siswa").select("*").eq("nama", st.session_state.user_name).execute()
        if len(response.data) == 0:
            supabase.table("profil_siswa").insert({"nama": st.session_state.user_name, "saldo_igil": 0, "nyawa": 3}).execute()
            saldo = 0
            nyawa = 3
        else:
            saldo = response.data[0]['saldo_igil']
            nyawa = response.data[0]['nyawa']
    except Exception as e:
        st.error(f"Gagal sinkronisasi Database: {e}")
        saldo = 0
        nyawa = 3
        
    # Tampilan Dasbor Gamifikasi
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"💰 Nilai Beasiswa:\n### {saldo} $IGIL")
    with col2:
        st.error(f"❤️ Nyawa Belajar:\n### {nyawa} / 3")

    # ==========================================
    # 4. SISTEM TAB (RUANG BELAJAR, RAPOR, PERINGKAT)
    # ==========================================
    tab1, tab2, tab3 = st.tabs(["📚 Ruang Belajar", "🧑‍🤝‍🧑 Rapor Anak", "🏆 Papan Peringkat"])

    with tab1:
        st.button("🎁 Tukar Saldo $IGIL Menjadi Beasiswa Instan", use_container_width=True)
        st.divider()

        col_tingkat, col_mapel = st.columns(2)
        with col_tingkat:
            tingkat = st.selectbox("Tingkat Pendidikan", [
                "SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6", 
                "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9", 
                "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"
            ])
        with col_mapel:
            mapel = st.selectbox("Mata Pelajaran", [
                "Matematika", "Tematik (SD)", "IPA Terpadu (SMP)", "IPS Terpadu (SMP)", 
                "Bahasa Indonesia", "Bahasa Inggris", "Fisika (SMA)", "Kimia (SMA)", 
                "Biologi (SMA)", "Ekonomi", "Geografi", "Sosiologi", "Sejarah", 
                "Pendidikan Pancasila (PPKn)", "Lainnya"
            ])
            
        judul_bab = st.text_input("Judul / Bab Materi:", placeholder="Contoh: Pecahan, Transformasi Geometri, dll.")
        
        st.write("🧑‍🏫 Pilih Guru Favoritmu!")
        guru_pilihan = st.radio("Pilih Guru", ["Bu Nisa (Ceria & Lembut)", "Pak Andi (Asyik & Lucu)"], horizontal=True, label_visibility="collapsed")

        # Tombol Suara Perkenalan Semalam
        if st.button("🔊 Putar Suara Perkenalan"):
            with st.spinner("Menyiapkan suara..."):
                teks_intro = f"Halo {st.session_state.user_name}! Saya siap menemani kamu belajar hari ini. Ayo kumpulkan hadiah IGIL sebanyak-banyaknya!"
                audio_intro = buat_suara(teks_intro, guru_pilihan)
                st.audio(audio_intro, format="audio/mp3", autoplay=True)

        foto_buku = st.file_uploader("📸 Foto Halaman Buku Pelajaran", type=["jpg", "jpeg", "png"])

        if st.button("🚀 Mulai Belajar!", type="primary", use_container_width=True):
            if not judul_bab:
                st.warning("Mohon isi Judul / Bab Materi terlebih dahulu agar guru bisa fokus.")
            elif foto_buku is None:
                st.error("Tolong unggah foto buku pelajarannya dulu ya!")
            else:
                with st.spinner("🧠 Guru AI sedang meracik materi belajar..."):
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        nama_guru_singkat = "Bu Nisa" if "Nisa" in guru_pilihan else "Pak Andi"
                        
                        prompt = f"Kamu adalah {nama_guru_singkat}, guru {mapel} untuk siswa {tingkat}. Materi saat ini adalah '{judul_bab}'. Jelaskan gambar buku ini dengan gaya bahasa yang sesuai. Akhiri dengan satu kuis interaktif."
                        img = Image.open(foto_buku)
                        respons_ai = model.generate_content([prompt, img])
                        naskah = respons_ai.text

                        audio_materi = buat_suara(naskah, nama_guru_singkat)

                        st.divider()
                        st.audio(audio_materi, format="audio/mp3")
                        st.write_stream(efek_mengetik(naskah))
                        
                        st.success("🎉 Luar biasa! Hadiah 10 $IGIL telah ditambahkan ke dompet beasiswamu!")
                        supabase.table("profil_siswa").update({"saldo_igil": saldo + 10}).eq("nama", st.session_state.user_name).execute()

                    except Exception as e:
                        st.error(f"Terjadi kesalahan teknis: {e}")

    with tab2:
        st.info("Fitur Rapor Anak sedang dalam tahap pengembangan.")
        
    with tab3:
        st.info("Fitur Papan Peringkat (Leaderboard) sedang dalam tahap pengembangan.")