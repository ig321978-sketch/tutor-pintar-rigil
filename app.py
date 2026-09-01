import time
import plotly.graph_objects as go
import streamlit as st
import time
import json
import plotly.graph_objects as go
from supabase import create_client, Client
import google.generativeai as genai
from google.oauth2 import service_account
from google.cloud import texttospeech

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
def efek_mengetik(teks, jeda=0.05):
    """Memunculkan teks perlahan seperti mesin tik"""
    for kata in teks.split():
        yield kata + " "
        time.sleep(jeda)

def buat_suara(teks, guru):
    """Menghasilkan audio dari teks menggunakan GCP TTS"""
    synthesis_input = texttospeech.SynthesisInput(text=teks)
    
    # Pengaturan suara berdasarkan pilihan guru
    if guru == "Bu Nisa":
        voice = texttospeech.VoiceSelectionParams(
            language_code="id-ID", 
            name="id-ID-Standard-A" # Suara wanita standar
        )
    else:
        voice = texttospeech.VoiceSelectionParams(
            language_code="id-ID", 
            name="id-ID-Standard-B" # Suara pria standar
        )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=0.9 # Diperlambat sedikit agar natural
    )

    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    return response.audio_content

def tampilkan_grafik_contoh():
    """Menampilkan grafik interaktif Plotly (Bisa disesuaikan dari SD hingga SMA)"""
    fig = go.Figure()
    # Contoh kurva fungsi (Cocok untuk visualisasi aljabar/geometri)
    fig.add_trace(go.Scatter(x=[-3, -2, -1, 0, 1, 2, 3], y=[9, 4, 1, 0, 1, 4, 9], 
                             mode='lines+markers', name='Kurva $f(x)=x^2$', line=dict(color='firebrick', width=3)))
    fig.update_layout(
        title="📊 Visualisasi Konsep Matematika",
        xaxis_title="Sumbu X",
        yaxis_title="Sumbu Y",
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 3. ANTARMUKA UTAMA APLIKASI
# ==========================================
st.title("🎓 $IGIL - Tutor Pintar")
st.markdown("*Platform Learn to Earn: Dari SD hingga SMA*")

# Sistem Login Sederhana
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""

nama_input = st.text_input("Masukkan nama kamu untuk mulai belajar:", value=st.session_state.user_name)

if nama_input:
    st.session_state.user_name = nama_input
    
    # Cek atau buat profil di Supabase
    try:
        response = supabase.table("profil_siswa").select("*").eq("nama", nama_input).execute()
        if len(response.data) == 0:
            # Buat profil baru jika belum ada
            supabase.table("profil_siswa").insert({"nama": nama_input, "saldo_igil": 0, "nyawa": 3}).execute()
            saldo = 0
            nyawa = 3
        else:
            saldo = response.data[0]['saldo_igil']
            nyawa = response.data[0]['nyawa']
            
        # Tampilkan Dasbor Gamifikasi
        st.success(f"Selamat datang, {nama_input}!")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"💰 Hadiah Beasiswa: **{saldo} $IGIL**")
        with col2:
            st.warning(f"❤️ Nyawa Belajar: **{nyawa} / 3**")
            
        st.divider()

        # ==========================================
        # 4. RUANG BELAJAR & PEMINDAI BUKU
        # ==========================================
        st.subheader("📚 Ruang Belajar")
        
        col_tingkat, col_mapel = st.columns(2)
        with col_tingkat:
            tingkat = st.selectbox("Tingkat Pendidikan", ["SD - Kelas 3", "SMP", "SMA - Kelas 12"])
        with col_mapel:
            mapel = st.selectbox("Mata Pelajaran", ["Matematika", "Tematik", "Sains / IPA"])
            
        guru_pilihan = st.radio("🧑‍🏫 Pilih Guru Favoritmu:", ["Bu Nisa", "Pak Andi"], horizontal=True)

        foto_buku = st.file_uploader("📸 Foto Halaman Buku Pelajaran", type=["jpg", "jpeg", "png"])

        if st.button("🚀 Mulai Belajar!"):
            if foto_buku is None:
                st.error("Tolong unggah foto buku pelajarannya dulu ya!")
            else:
                with st.spinner("🧠 Guru AI sedang membaca bukumu..."):
                    try:
                        # 1. Panggil Gemini AI
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = f"Kamu adalah {guru_pilihan}, guru {mapel} untuk anak {tingkat}. Jelaskan materi dari gambar buku ini dengan gaya bahasa yang ceria, mudah dimengerti, dan berikan satu pertanyaan kuis di akhir. Jangan terlalu panjang."
                        
                        from PIL import Image
                        img = Image.open(foto_buku)
                        respons_ai = model.generate_content([prompt, img])
                        naskah_materi = respons_ai.text

                        # 2. Buat Suara TTS
                        audio_bytes = buat_suara(naskah_materi, guru_pilihan)

                        # 3. Tampilkan Hasil (Animasi & Grafik)
                        st.subheader("Penjelasan Materi:")
                        
                        # Tampilkan pemutar audio di atas agar bisa langsung ditekan
                        st.audio(audio_bytes, format="audio/mp3")
                        
                        # Munculkan teks dengan animasi ketikan
                        st.write_stream(efek_mengetik(naskah_materi))
                        
                        # Tampilkan grafik interaktif Plotly
                        st.divider()
                        tampilkan_grafik_contoh()
                        
                        st.success("🎉 Hebat! Kamu dapat hadiah 10 $IGIL karena sudah belajar hari ini!")
                        
                        # Update hadiah ke Supabase (Contoh penambahan saldo)
                        saldo_baru = saldo + 10
                        supabase.table("profil_siswa").update({"saldo_igil": saldo_baru}).eq("nama", nama_input).execute()

                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat memproses: {e}")

    except Exception as e:
        st.error(f"Gagal terhubung ke Database: {e}")