import streamlit as st
import streamlit.components.v1 as components
import re
import time
import json
import base64
from PIL import Image
from google import genai
from google.cloud import texttospeech
from google.oauth2 import service_account

# --- DESAIN UI / CSS CUSTOM STREAMLIT ---
st.set_page_config(page_title="Tutor Pintar Rigil", page_icon="🎓", layout="centered")

# --- INISIALISASI SESSION STATE ---
if 'berhasil_baca' not in st.session_state:
    st.session_state.berhasil_baca = False
if 'naskah_layar' not in st.session_state:
    st.session_state.naskah_layar = ""
if 'file_suara' not in st.session_state:
    st.session_state.file_suara = "audio_guru.mp3"
if 'daftar_kuis' not in st.session_state:
    st.session_state.daftar_kuis = []
if 'pesan_error_json' not in st.session_state:
    st.session_state.pesan_error_json = ""
# Tambahan State untuk Q&A dan Karakter Suara
if 'karakter_suara' not in st.session_state:
    st.session_state.karakter_suara = "id-ID-Wavenet-A"
if 'qa_history' not in st.session_state:
    st.session_state.qa_history = []

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
    st.session_state.pesan_error_json = str(e)

# --- FUNGSI PEMBUAT SUARA GOOGLE PREMIUM (VERSI CEPAT & CERIA) ---
def buat_suara_google(teks, nama_file, nama_suara):
    if not client_tts:
        raise Exception("Kunci JSON belum siap!")
    
    synthesis_input = texttospeech.SynthesisInput(text=teks)
    voice = texttospeech.VoiceSelectionParams(language_code="id-ID", name=nama_suara)
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.15,  # <-- Suara cepat dan energik
        pitch=4.0            
    )
    
    response = client_tts.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    
    with open(nama_file, "wb") as out:
        out.write(response.audio_content)

# --- ANTARMUKA PENGGUNA (UI) UTAMA ---
st.title("🎓 Tutor Pintar Rigil")
st.write("Asisten belajar cerdas dengan animasi teks dan suara AI Google Premium!")

st.markdown("---")
mode_belajar = st.radio("Pilih Sumber Materi:", ["📸 Unggah Foto Buku", "✍️ Ketik Judul Materi"], horizontal=True)

with st.form("user_form"):
    nama = st.text_input("Nama Siswa:", "Rigil")
    jenjang_kelas = st.selectbox("Jenjang & Kelas:", [
        "SD - Kelas 1", "SD - Kelas 2", "SD - Kelas 3", "SD - Kelas 4", "SD - Kelas 5", "SD - Kelas 6",
        "SMP - Kelas 7", "SMP - Kelas 8", "SMP - Kelas 9",
        "SMA - Kelas 10", "SMA - Kelas 11", "SMA - Kelas 12"
    ], index=2)
    mapel = st.text_input("Mata Pelajaran:", "Matematika")
    
    if mode_belajar == "📸 Unggah Foto Buku":
        uploaded_files = st.file_uploader("Foto Halaman Buku Pelajaran (Bisa lebih dari 1):", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        judul_materi = ""
    else:
        judul_materi = st.text_input("Topik/Judul Materi yang Ingin Dipelajari:")
        uploaded_files = []
    
    btn_analisis = st.form_submit_button(label="Mulai Belajar! 🚀")

# --- PROSES ANALISIS AI ---
if btn_analisis:
    if mode_belajar == "📸 Unggah Foto Buku" and not uploaded_files:
        st.warning("Silakan unggah minimal satu foto buku dulu ya!")
    elif mode_belajar == "✍️ Ketik Judul Materi" and not judul_materi:
        st.warning("Silakan ketik judul materi yang ingin dipelajari!")
    else:
        if not client_tts:
            st.error(f"**Gagal membaca Kunci JSON Google!**")
            st.stop()
            
        # Reset riwayat jika mencari materi baru
        for key in list(st.session_state.keys()):
            if key.startswith('status_soal_'):
                del st.session_state[key]
        st.session_state.qa_history = [] 
        
        with st.spinner("AI sedang meracik materi dan menyiapkan animasi sinkronisasi suara..."):
            
            # Simpan karakter suara ke session_state agar bisa dipakai saat Q&A nanti
            if "SD" in jenjang_kelas:
                st.session_state.karakter_suara = "id-ID-Wavenet-A" 
            elif "SMP" in jenjang_kelas:
                st.session_state.karakter_suara = "id-ID-Wavenet-D" 
            else:
                st.session_state.karakter_suara = "id-ID-Wavenet-B" 

            instruksi_format = f"""
            Keluarkan persis 3 bagian berikut dengan format pembatas yang ketat:

            ===NASKAH_LAYAR===
            (Tulis penjelasan materi SANGAT DETAIL dan MENARIK. Gunakan BANYAK EMOJI 🌟🚀💡. 
            SYARAT MUTLAK: WAJIB GUNAKAN FORMAT HTML (Gunakan tag <h3>, <p>, <ul>, <li>, <strong>, <br>). 
            DILARANG KERAS MENGGUNAKAN MARKDOWN (jangan pakai simbol bintang * atau pagar #). 
            Susun dengan rapi. Sapa {nama} dengan sangat antusias di kalimat pertama!)

            ===NASKAH_SUARA===
            (Tulis versi lisan dari NASKAH_LAYAR di atas. Kalimatnya HARUS 100% sama maknanya, TETAPI DILARANG KERAS MENGGUNAKAN EMOJI SAMA SEKALI. Semua angka dan simbol matematika WAJIB DIEJA dengan huruf agar mesin suara membacanya dengan mulus.)

            ===KUIS===
            (Buatlah 3 soal pilihan ganda. SYARAT WAJIB: Pertanyaan dan angka yang digunakan pada Kuis TIDAK BOLEH SAMA dengan contoh yang sudah dibahas di Naskah Layar. Wajib gunakan format per baris, dipisah 3 garis lurus HANYA:)
            Pertanyaan 1?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
            Pertanyaan 2?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
            Pertanyaan 3?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
            (PENTING: Bagian akhir HANYA boleh berisi TEKS JAWABAN BENAR yang persis sama dengan isi salah satu opsi)
            """

            if mode_belajar == "📸 Unggah Foto Buku":
                daftar_gambar = [Image.open(file) for file in uploaded_files]
                st.write("📸 **Buku Pelajaran Asli:**")
                kolom_gambar = st.columns(len(daftar_gambar)) if len(daftar_gambar) <= 3 else st.columns(3)
                for i, img in enumerate(daftar_gambar):
                    kolom_gambar[i % len(kolom_gambar)].image(img, use_container_width=True)
                
                konteks = f"Kamu adalah Tutor AI ahli {mapel} yang super sabar. Baca materi dari foto halaman buku terlampir untuk siswa {jenjang_kelas} bernama {nama}."
                payload_ai = [konteks + "\n\n" + instruksi_format] + daftar_gambar
            else:
                konteks = f"Kamu adalah Tutor AI ahli {mapel} yang super sabar. Susun materi pembelajaran yang detail tentang topik: '{judul_materi}'. Materi ditujukan untuk siswa {jenjang_kelas} bernama {nama}."
                payload_ai = [konteks + "\n\n" + instruksi_format]

            maksimal_coba = 3
            for percobaan in range(maksimal_coba):
                try:
                    response = client_gemini.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=payload_ai
                    )
                    full_text = response.text
                    
                    if "===NASKAH_LAYAR===" in full_text:
                        match_l = re.search(r'===NASKAH_LAYAR===(.*?)(?====NASKAH_SUARA===|$)', full_text, re.DOTALL)
                        if match_l: st.session_state.naskah_layar = match_l.group(1).strip()
                    
                    if "===NASKAH_SUARA===" in full_text:
                        match_s = re.search(r'===NASKAH_SUARA===(.*?)(?====KUIS===|$)', full_text, re.DOTALL)
                        if match_s: 
                            naskah_suara = match_s.group(1).strip()
                            naskah_bersih = re.sub(r'[*#_`>-]', '', naskah_suara)
                            buat_suara_google(naskah_bersih, st.session_state.file_suara, st.session_state.karakter_suara)
                    
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
                        st.warning(f"Sistem Google sedang padat. Mencoba lagi dalam 5 detik... ({percobaan + 1}/{maksimal_coba})")
                        time.sleep(5)
                    else:
                        st.error(f"Gagal memproses materi: {e}")
                        break

# --- MENAMPILKAN MODUL BELAJAR INTERAKTIF ---
if st.session_state.berhasil_baca:
    st.markdown("---")
    st.markdown("## 🎧 Dengarkan & Baca Penjelasan Guru")
    
    with open(st.session_state.file_suara, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode()
    
    # HTML Kustom dengan Kalibrasi Sinkronisasi Kecepatan Teks SUPER CEPAT (Dipercepat 25% lagi)
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
            <p style="margin-top:0; color:#FF5722; font-weight:bold; font-size: 18px;">
                ▶️ Klik PLAY untuk memunculkan catatan ajaib! ✨
            </p>
            <audio id="audio-player" controls style="width: 100%; outline: none;">
                <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
            </audio>
        </div>
        <div class="materi-card" id="materi-content">{st.session_state.naskah_layar}</div>
        <script>
            const audio = document.getElementById('audio-player');
            const content = document.getElementById('materi-content');
            let totalChars = 0;
            const wordData = [];
            
            function wrapWords(element) {{
                const children = Array.from(element.childNodes);
                children.forEach(child => {{
                    if (child.nodeType === Node.TEXT_NODE) {{
                        const words = child.nodeValue.split(/(\\s+)/);
                        const fragment = document.createDocumentFragment();
                        let hasWords = false;
                        words.forEach(word => {{
                            if (word.trim().length > 0) {{
                                const span = document.createElement('span');
                                span.className = 'word';
                                span.textContent = word;
                                fragment.appendChild(span);
                                hasWords = true;
                                let charCount = word.trim().length;
                                totalChars += charCount;
                                wordData.push({{ element: span, chars: charCount }});
                            }} else {{
                                fragment.appendChild(document.createTextNode(word));
                            }}
                        }});
                        if (hasWords) {{ element.replaceChild(fragment, child); }}
                    }} else if (child.nodeType === Node.ELEMENT_NODE) {{
                        wrapWords(child);
                    }}
                }});
            }}
            wrapWords(content);
            
            audio.addEventListener('timeupdate', () => {{
                if (audio.duration) {{
                    // KALIBRASI SUPER CEPAT: Ditambah 25% lebih ngebut!
                    // Dorongan awal dari 0.4 jadi 0.6 detik
                    let adjustedTime = audio.currentTime + 0.6;
                    // Pengali kelajuan dari 1.05 dinaikkan tajam ke 1.35
                    let progress = (adjustedTime / audio.duration) * 1.35;
                    
                    if (progress > 1) progress = 1;
                    let targetChars = progress * totalChars;
                    let currentChars = 0;
                    
                    for (let i = 0; i < wordData.length; i++) {{
                        currentChars += wordData[i].chars;
                        if (currentChars <= targetChars) {{
                            wordData[i].element.classList.add('active');
                        }} else {{
                            wordData[i].element.classList.remove('active');
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    components.html(html_animasi, height=750, scrolling=True)

    # --- SEGMEN TANYA JAWAB (Q&A) TAK TERBATAS ---
    st.markdown("---")
    st.markdown(f"## 🙋‍♂️ Ada Pertanyaan, {nama}?")
    st.info("💡 Belum paham? Ketik pertanyaanmu di bawah, Guru AI akan langsung menjawab dengan teks dan suara!")

    for idx, qa in enumerate(st.session_state.qa_history):
        with st.chat_message("user", avatar="👦"):
            st.write(f"**{nama}:** {qa['tanya']}")
        with st.chat_message("assistant", avatar="👩‍🏫"):
            st.write(qa['jawab_teks'])
            st.audio(qa['file_audio'], format="audio/mp3")

    pertanyaan_baru = st.text_input("Ketik pertanyaan barumu di sini:", placeholder="Misal: Bu Guru, apa itu...")
    
    if st.button("Minta Jawaban Guru 🎙️"):
        if pertanyaan_baru:
            with st.spinner("Guru sedang memikirkan jawaban terbaik..."):
                prompt_qa = f"""Kamu adalah Tutor AI ahli {mapel} yang super ramah dan sabar.
                Konteks materi saat ini: "{st.session_state.naskah_layar}"
                
                Siswa bernama {nama} ({jenjang_kelas}) bertanya: "{pertanyaan_baru}"
                
                Keluarkan persis 2 bagian berikut:
                ===TEKS===
                (Jawab dengan singkat, jelas, dan sangat ramah untuk anak. Gunakan emoji yang sesuai 🌟💡)
                ===SUARA===
                (Versi lisan dari TEKS di atas. DILARANG KERAS MENGGUNAKAN EMOJI SAMA SEKALI. Angka dan simbol wajib dieja huruf)
                """
                
                try:
                    response_qa = client_gemini.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt_qa
                    )
                    
                    full_qa_text = response_qa.text
                    jawab_teks = ""
                    jawab_suara = ""
                    
                    match_t = re.search(r'===TEKS===(.*?)(?====SUARA===|$)', full_qa_text, re.DOTALL)
                    if match_t: jawab_teks = match_t.group(1).strip()
                    
                    match_s = re.search(r'===SUARA===(.*)', full_qa_text, re.DOTALL)
                    if match_s: 
                        jawab_suara = match_s.group(1).strip()
                        jawab_suara_bersih = re.sub(r'[*#_`>-]', '', jawab_suara)
                        
                        nama_file_dinamis = f"audio_qa_{int(time.time())}.mp3"
                        buat_suara_google(jawab_suara_bersih, nama_file_dinamis, st.session_state.karakter_suara)
                        
                        st.session_state.qa_history.append({
                            "tanya": pertanyaan_baru,
                            "jawab_teks": jawab_teks,
                            "file_audio": nama_file_dinamis
                        })
                        
                        st.rerun()
                except Exception as e:
                    st.error(f"Gagal membuat jawaban: {e}")
        else:
            st.warning("Eits, ketik dulu pertanyaannya ya sebelum menekan tombol!")

    # --- SEGMEN KUIS ---
    st.markdown("---")
    st.markdown(f"## 🏆 Latihan Soal untuk {nama}!")
    
    if st.session_state.daftar_kuis:
        for i, q in enumerate(st.session_state.daftar_kuis):
            st.markdown(f"**{i+1}. {q['soal']}**")
            
            jawaban_user = st.radio("Pilih jawaban:", q['opsi'], key=f"soal_radio_{i}", index=None, label_visibility="collapsed")
            
            if st.button(f"Cek Jawaban Soal {i+1}", key=f"btn_cek_{i}"):
                if jawaban_user == q['kunci']:
                    st.session_state[f"status_soal_{i}"] = "benar"
                    if i == len(st.session_state.daftar_kuis) - 1:
                        st.balloons() 
                elif jawaban_user is None:
                    st.session_state[f"status_soal_{i}"] = "kosong"
                else:
                    st.session_state[f"status_soal_{i}"] = "salah"
            
            status_jawaban = st.session_state.get(f"status_soal_{i}")
            if status_jawaban == "benar":
                st.success("Tepat sekali! Ini hadiah bintang untukmu! ⭐")
            elif status_jawaban == "kosong":
                st.warning("Kamu belum memilih jawaban, klik salah satu bulatan dulu ya.")
            elif status_jawaban == "salah":
                st.error("Wah, masih kurang tepat. Coba hitung pelan-pelan lagi ya!")
            
            st.write("")
