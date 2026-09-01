import streamlit as st
import time
import json
import plotly.graph_objects as go
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
# 2. FUNGSI PENDUKUNG (VISUAL & AUDIO)
# ==========================================
def efek_mengetik(teks, jeda=0.04):
    """Memunculkan teks perlahan seperti mesin tik"""
    for kata in teks.split():
        yield kata + " "
        time.sleep(jeda)

def buat_suara(teks, guru):
    """Menghasilkan audio dari teks menggunakan GCP TTS"""
    synthesis_input = texttospeech.SynthesisInput(text=teks)
    
    if guru == "Bu Nisa":
        voice = texttospeech.VoiceSelectionParams(language_code="id-ID", name="id-ID-Standard-A")
    else:
        voice = texttospeech.VoiceSelectionParams(language_code="id-ID", name="id-ID-Standard-B")

    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=0.9)
    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    return response.audio_content

def tampilkan_grafik_contoh(bab):
    """Menampilkan grafik interaktif Plotly"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[-3, -2, -1, 0, 1, 2, 3], y=[9, 4, 1, 0, 1, 4, 9], 
                             mode='lines+markers', name='Visualisasi', line=dict(color='firebrick', width=3)))
    fig.update_layout(
        title=f"📊 Visualisasi Materi: {bab}",
        xaxis_title="Indikator X", yaxis_title="Indikator Y", template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 3. ANTARMUKA UTAMA APLIKASI
# ==========================================
st.title("🎓 $IGIL")
st.markdown("### *Learn to Earn Concept*")

# Sistem Login
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""

nama_input = st.text_input("Masuk sebagai:", value=st.session_state.user_name, placeholder="Ketik nama kamu di sini...")

if nama_input:
    st.session_state.user_name = nama_input
    
    try:
        # Sinkronisasi Database
        response = supabase.table("profil_siswa").select("*").eq("nama", nama_input).execute()
        if len(response.data) == 0:
            supabase.table("profil_siswa").insert({"nama": nama_input, "saldo_igil": 0, "nyawa": 3}).execute()
            saldo = 0
            nyawa = 3
        else:
            saldo = response.data[0]['saldo_igil']
            nyawa = response.data[0]['nyawa']
            
        # Tampilan Dasbor
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"💰 Nilai Beasiswa:\n### {saldo} $IGIL")
        with col2:
            st.error(f"❤️ Nyawa Belajar:\n### {nyawa} / 3")
            
        st.button("🎁 Tukar Saldo $IGIL Menjadi Beasiswa Instan", use_container_width=True)
        st.divider()

        # ==========================================
        # 4. SISTEM TAB (RUANG BELAJAR, RAPOR, PERINGKAT)
        # ==========================================
        tab1, tab2, tab3 = st.tabs(["📚 Ruang Belajar", "🧑‍🤝‍🧑 Rapor Anak", "🏆 Papan Peringkat"])

        with tab1:
            col_tingkat, col_mapel = st.columns(2)
            with col_tingkat:
                # DAFTAR TINGKAT PENDIDIKAN DARI KELAS 1 SD - 12 SMA
                tingkat = st.selectbox("Tingkat Pendidikan", [
                    "SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6", 
                    "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9", 
                    "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"
                ])
            with col_mapel:
                # DAFTAR MATA PELAJARAN LENGKAP
                mapel = st.selectbox("Mata Pelajaran", [
                    "Matematika", "Tematik (SD)", "IPA Terpadu (SMP)", "IPS Terpadu (SMP)", 
                    "Bahasa Indonesia", "Bahasa Inggris", "Fisika (SMA)", "Kimia (SMA)", 
                    "Biologi (SMA)", "Ekonomi", "Geografi", "Sosiologi", "Sejarah", 
                    "Pendidikan Pancasila (PPKn)", "Lainnya"
                ])
                
            judul_bab = st.text_input("Judul / Bab Materi:", placeholder="Contoh: Pecahan, Transformasi Geometri, dll.")
            guru_pilihan = st.radio("🧑‍🏫 Pilih Guru Favoritmu:", ["Bu Nisa (Ceria & Lembut)", "Pak Andi (Asyik & Lucu)"], horizontal=True)

            metode_belajar = st.radio("Metode Belajar:", ["Ambil dari Foto/Gambar", "Ketik Teks Materi Langsung"], horizontal=True)

            teks_materi = None
            foto_buku = None

            if metode_belajar == "Ambil dari Foto/Gambar":
                foto_buku = st.file_uploader("📸 Foto Halaman Buku Pelajaran", type=["jpg", "jpeg", "png"])
            else:
                teks_materi = st.text_area("📝 Ketik atau tempelkan materi pelajaran di sini:")

            if st.button("🚀 Mulai Belajar!", use_container_width=True):
                if not judul_bab:
                    st.warning("Mohon isi Judul / Bab Materi terlebih dahulu agar guru bisa fokus.")
                elif metode_belajar == "Ambil dari Foto/Gambar" and foto_buku is None:
                    st.error("Tolong unggah foto buku pelajarannya dulu ya!")
                elif metode_belajar == "Ketik Teks Materi Langsung" and not teks_materi:
                    st.error("Tolong ketik materi pelajarannya dulu ya!")
                else:
                    with st.spinner("🧠 Guru AI sedang meracik materi belajar..."):
                        try:
                            # 1. Panggil Gemini AI
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            nama_guru_singkat = "Bu Nisa" if "Nisa" in guru_pilihan else "Pak Andi"
                            
                            if metode_belajar == "Ambil dari Foto/Gambar":
                                prompt = f"Kamu adalah {nama_guru_singkat}, guru {mapel} untuk siswa {tingkat}. Materi saat ini adalah tentang '{judul_bab}'. Berdasarkan gambar buku ini, jelaskan intisari materinya dengan gaya bahasa yang sesuai tingkat usianya. Akhiri dengan satu pertanyaan kuis interaktif."
                                img = Image.open(foto_buku)
                                respons_ai = model.generate_content([prompt, img])
                            else:
                                prompt = f"Kamu adalah {nama_guru_singkat}, guru {mapel} untuk siswa {tingkat}. Materi saat ini adalah tentang '{judul_bab}'. Berdasarkan teks berikut, jelaskan intisari materinya dengan gaya bahasa yang sesuai tingkat usianya. Akhiri dengan satu pertanyaan kuis interaktif.\n\nTeks Materi:\n{teks_materi}"
                                respons_ai = model.generate_content(prompt)

                            naskah_materi = respons_ai.text

                            # 2. Buat Suara TTS
                            audio_bytes = buat_suara(naskah_materi, nama_guru_singkat)

                            # 3. Tampilkan Hasil
                            st.divider()
                            st.audio(audio_bytes, format="audio/mp3")
                            st.write_stream(efek_mengetik(naskah_materi))
                            
                            st.write("---")
                            tampilkan_grafik_contoh(judul_bab)
                            
                            st.success("🎉 Luar biasa! Hadiah 10 $IGIL telah ditambahkan ke dompet beasiswamu!")
                            saldo_baru = saldo + 10
                            supabase.table("profil_siswa").update({"saldo_igil": saldo_baru}).eq("nama", nama_input).execute()

                        except Exception as e:
                            st.error(f"Terjadi kesalahan teknis: {e}")

        with tab2:
            st.info("Fitur Rapor Anak sedang dalam tahap pengembangan.")
            
        with tab3:
            st.info("Fitur Papan Peringkat (Leaderboard) sedang dalam tahap pengembangan.")

    except Exception as e:
        st.error(f"Gagal sinkronisasi dengan Database: {e}")