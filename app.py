import streamlit as st
import datetime

# --- DESAIN UI / CSS CUSTOM STREAMLIT ---
st.set_page_config(page_title="Dashboard Orang Tua - Tutor Pintar", page_icon="📊", layout="wide")

st.markdown("""
<style>
    .ai-insight {
        background-color: #F4FBFF;
        border-left: 5px solid #2AB3FF;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 25px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    .ai-insight h4 { color: #0078D7; margin-top: 0; }
    .badge-card {
        background-color: #FFF9E6;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #FFE082;
    }
    .badge-icon { font-size: 40px; }
</style>
""", unsafe_allow_html=True)

# --- HEADER DASBOR ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("📊 Dasbor Pantau Belajar")
    st.write("Selamat datang, **Bapak Iwan**! Berikut adalah ringkasan perkembangan belajar **Rigil**.")
with col_head2:
    st.info(f"📅 Tanggal: {datetime.date.today().strftime('%d %B %Y')}\n\n👑 Status: **Premium Member**")

st.markdown("---")

# --- KARTU METRIK UTAMA ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="⏱️ Total Waktu Belajar", value="12 Jam", delta="+2 Jam dari minggu lalu")
with col2:
    st.metric(label="📚 Topik Diselesaikan", value="8 Topik", delta="3 Topik baru")
with col3:
    st.metric(label="🎯 Rata-rata Nilai Kuis", value="85 / 100", delta="+5 Poin")
with col4:
    st.metric(label="❓ Total Bertanya ke AI", value="14 Kali", delta="Sangat Aktif", delta_color="normal")

st.markdown("<br>", unsafe_allow_html=True)

# --- ANALISIS KECERDASAN BUATAN (AI INSIGHT) ---
st.markdown("""
<div class="ai-insight">
    <h4>🤖 Laporan Analisis AI Tutor</h4>
    <p>Halo Bapak Iwan! Selama minggu ini, Rigil menunjukkan perkembangan yang luar biasa pada mata pelajaran <strong>Matematika</strong>, khususnya pada topik <em>Perkalian Bersusun</em> (Akurasi Kuis 100%).</p>
    <p>Namun, AI kami mendeteksi Rigil mengajukan banyak pertanyaan berulang di topik <em>Pembagian Pecahan</em>. Kami merekomendasikan Bapak untuk mendampingi Rigil mengulas kembali materi ini, atau meminta AI membuatkan latihan soal tambahan khusus pecahan esok hari.</p>
</div>
""", unsafe_allow_html=True)

# --- GRAFIK PENGUASAAN MATERI ---
st.markdown("### 📈 Tingkat Penguasaan Materi (Bulan Ini)")
col_prog1, col_prog2 = st.columns(2)

with col_prog1:
    st.write("**Matematika - Perkalian**")
    st.progress(95)
    st.write("**Matematika - Pembagian**")
    st.progress(60)
    st.write("**IPA - Ciri Makhluk Hidup**")
    st.progress(85)

with col_prog2:
    st.write("**Bahasa Indonesia - Kalimat Utama**")
    st.progress(75)
    st.write("**Bahasa Inggris - Vocabulary**")
    st.progress(90)
    st.write("**PPKn - Sila Pancasila**")
    st.progress(100)

st.markdown("<br>", unsafe_allow_html=True)

# --- RIWAYAT AKTIVITAS & PENGHARGAAN ---
col_hist1, col_hist2 = st.columns([2, 1])

with col_hist1:
    st.markdown("### 🕒 Riwayat Aktivitas Terakhir")
    # Menggunakan tabel bawaan Streamlit (Bisa diganti dengan Database Supabase nanti)
    riwayat_data = [
        {"Tanggal": "31 Ags 2026", "Aktivitas": "Membaca Naskah", "Topik": "Perkalian Bersusun", "Nilai Kuis": "100"},
        {"Tanggal": "30 Ags 2026", "Aktivitas": "Tanya Jawab AI", "Topik": "Pembagian Pecahan", "Nilai Kuis": "66"},
        {"Tanggal": "29 Ags 2026", "Aktivitas": "Membaca Naskah", "Topik": "Fotosintesis (IPA)", "Nilai Kuis": "80"},
        {"Tanggal": "28 Ags 2026", "Aktivitas": "Latihan Soal", "Topik": "Bahasa Inggris Dasar", "Nilai Kuis": "90"},
    ]
    st.table(riwayat_data)

with col_hist2:
    st.markdown("### 🏆 Lencana Koleksi Rigil")
    st.markdown("""
    <div class="badge-card">
        <div class="badge-icon">🔥</div>
        <strong>3 Hari Beruntun!</strong><br>
        <small>Rajin belajar tanpa bolos</small>
    </div>
    <br>
    <div class="badge-card">
        <div class="badge-icon">🧮</div>
        <strong>Master Hitung</strong><br>
        <small>Nilai 100 di Kuis Matematika</small>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.button("📥 Unduh Laporan PDF untuk Dicetak")
