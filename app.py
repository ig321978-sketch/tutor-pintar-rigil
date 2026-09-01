import streamlit as st
import streamlit.components.v1 as components
import re
import time
import json
import base64
from PIL import Image
from google import genai
from google.genai import types # Tambahan modul untuk membaca file suara
from google.cloud import texttospeech
from google.oauth2 import service_account

# --- DESAIN UI / CSS CUSTOM STREAMLIT ---
st.set_page_config(page_title="Tutor Pintar Rigil", page_icon="🎓", layout="centered")

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
if 'naskah_layar' not in st.session_state:
    st.session_state.naskah_layar = ""
if 'file_suara' not in st.session_state:
    st.session_state.file_suara = "audio_guru.mp3"
if 'daftar_kuis' not in st.session_state:
    st.session_state.daftar_kuis = []
if 'pesan_error_json' not in st.session_state:
    st.session_state.pesan_error_json = ""
if 'qa_history' not in st.session_state:
    st.session_state.qa_history = []
if 'guru_aktif' not in st.session_state:
    st.session_state.guru_aktif = DATA_GURU["SD"][0] 

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

# --- FUNGSI PEMBUAT SUARA GOOGLE PREMIUM ---
def buat_suara_google(teks, nama_file, nama_suara, pitch_guru, rate_guru):
    if not client_tts:
        raise Exception("Kunci JSON belum siap!")
    
    synthesis_input = texttospeech.SynthesisInput(text=teks)
    voice = texttospeech.VoiceSelectionParams(language_code="id-ID", name=nama_suara)
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=rate_guru,  
        pitch=pitch_guru            
    )
    
    response = client_tts.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    
    with open(nama_file, "wb") as out:
        out.write(response.audio_content)

# --- ANTARMUKA PENGGUNA (UI) UTAMA ---
st.title("🎓 Tutor Pintar")
st.write("Asisten belajar cerdas dengan animasi teks dan suara AI Google Premium!")

st.markdown("---")
mode_belajar = st.radio("Pilih Sumber Materi:", ["📸 Unggah Foto Buku", "✍️ Ketik Judul Materi"], horizontal=True)

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

# --- PEMILIHAN KARAKTER GURU ---
st.markdown("### 👨‍🏫 Pilih Guru Favoritmu!")
jenjang_inti = jenjang_kelas.split(" - ")[0] 
daftar_guru = DATA_GURU[jenjang_inti]

nama_guru_pilihan = st.radio("Daftar Guru Tersedia:", [g['nama'] for g in daftar_guru], horizontal=True, label_visibility="collapsed")
guru_terpilih = next(g for g in daftar_guru if g['nama'] == nama_guru_pilihan)

if st.button(f"🔊 Putar Suara Perkenalan {guru_terpilih['nama'].split(' ')[0]}"):
    if client_tts:
        with st.spinner("Mengambil suara guru..."):
            buat_suara_google(
                guru_terpilih['pesan'], "test_suara.mp3", 
                guru_terpilih['voice'], guru_terpilih['pitch'], guru_terpilih['rate']
            )
        st.audio("test_suara.mp3", autoplay=True)
    else:
        st.error("Kunci API Google belum terhubung.")

st.markdown("<br>", unsafe_allow_html=True)
btn_analisis = st.button("Mulai Belajar! 🚀", use_container_width=True, type="primary")

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
            
        st.session_state.guru_aktif = guru_terpilih
        for key in list(st.session_state.keys()):
            if key.startswith('status_soal_'):
                del st.session_state[key]
        st.session_state.qa_history = [] 
        
        with st.spinner(f"{st.session_state.guru_aktif['nama'].split(' ')[0]} sedang meracik materi untukmu..."):
            
            instruksi_format = f"""
            Keluarkan persis 3 bagian berikut dengan format pembatas yang ketat:

            ===NASKAH_LAYAR===
            (Tulis penjelasan materi SANGAT DETAIL dan MENARIK. Sesuaikan gaya bahasamu dengan karaktermu. Gunakan EMOJI yang relevan 🌟🚀💡. 
            SYARAT MUTLAK: WAJIB GUNAKAN FORMAT HTML (Gunakan tag <h3>, <p>, <ul>, <li>, <strong>, <br>). 
            DILARANG KERAS MENGGUNAKAN MARKDOWN (jangan pakai simbol bintang * atau pagar #). 
            Susun dengan rapi. Sapa {nama} dengan gaya khasmu di kalimat pertama!)

            ===NASKAH_SUARA===
            (Tulis versi lisan dari NASKAH_LAYAR di atas. Kalimatnya HARUS 100% sama maknanya, TETAPI DILARANG KERAS MENGGUNAKAN EMOJI SAMA SEKALI. Semua angka dan simbol matematika WAJIB DIEJA dengan huruf agar mesin suara membacanya dengan mulus.)

            ===KUIS===
            (Buatlah 3 soal pilihan ganda. SYARAT WAJIB: Angka yang digunakan pada Kuis TIDAK BOLEH SAMA dengan contoh yang dibahas di Naskah Layar. Format:)
            Pertanyaan 1?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
            Pertanyaan 2?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
            Pertanyaan 3?|||Opsi 1|||Opsi 2|||Opsi 3|||Teks Jawaban Benar
            """

            if mode_belajar == "📸 Unggah Foto Buku":
                daftar_gambar = [Image.open(file) for file in uploaded_files]
                konteks = f"Kamu adalah Tutor AI ahli {mapel} bernama {st.session_state.guru_aktif['nama']}. Baca materi dari foto halaman buku terlampir untuk siswa {jenjang_kelas} bernama {nama}."
                payload_ai = [konteks + "\n\n" + instruksi_format] + daftar_gambar
            else:
                konteks = f"Kamu adalah Tutor AI ahli {mapel} bernama {st.session_state.guru_aktif['nama']}. Susun materi pembelajaran yang detail tentang topik: '{judul_materi}'. Materi ditujukan untuk siswa {jenjang_kelas} bernama {nama}."
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
                            guru = st.session_state.guru_aktif
                            buat_suara_google(naskah_bersih, st.session_state.file_suara, guru['voice'], guru['pitch'], guru['rate'])
                    
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
                        time.sleep(5)
                    else:
                        st.error(f"Gagal memproses materi: {e}")
                        break

# --- MENAMPILKAN MODUL BELAJAR INTERAKTIF ---
if st.session_state.berhasil_baca:
    st.markdown("---")
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
                    let adjustedTime = audio.currentTime + 0.6;
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

    # --- SEGMEN TANYA JAWAB (Q&A) DENGAN INPUT SUARA MIKROFON ---
    st.markdown("---")
    st.markdown(f"## 🙋‍♂️ Ayo Bertanya, {nama}!")
    st.info(f"💡 Tidak perlu malu atau takut salah! Kamu bebas bertanya langsung kepada {st.session_state.guru_aktif['nama'].split(' ')[0]} lewat suara atau ketikan.")

    # Menampilkan Riwayat Q&A
    for idx, qa in enumerate(st.session_state.qa_history):
        with st.chat_message("user", avatar="👦"):
            st.write(f"**{nama}:** {qa['tanya']}")
        with st.chat_message("assistant", avatar="👩‍🏫"):
            st.write(qa['jawab_teks'])
            st.audio(qa['file_audio'], format="audio/mp3")

    # Pilihan Input Suara atau Teks menggunakan Tab
    tab_suara, tab_teks = st.tabs(["🎙️ Tanya Pakai Suara (Lebih Asyik!)", "⌨️ Ketik Pertanyaan"])
    
    with tab_suara:
        st.write("**Tekan ikon mikrofon di bawah ini dan mulailah bicara:**")
        pertanyaan_suara = st.audio_input("Rekam Suaramu di sini")
        
    with tab_teks:
        st.write("**Atau ketik pertanyaanmu di kolom ini:**")
        pertanyaan_teks = st.text_input("Ketik pertanyaan:", placeholder="Misal: Bu Guru, dari mana asalnya awan?")
    
    if st.button("Kirim Pertanyaan ke Guru 🚀", use_container_width=True):
        if pertanyaan_suara or pertanyaan_teks:
            with st.spinner("Guru sedang mendengarkan dan memikirkan jawaban terbaik..."):
                
                prompt_qa = f"""Kamu adalah Tutor AI ahli {mapel} bernama {st.session_state.guru_aktif['nama']}.
                Konteks materi saat ini: "{st.session_state.naskah_layar}"
                
                Keluarkan persis 3 bagian berikut secara ketat:
                ===TRANSKRIP===
                (Jika anak bertanya lewat suara, tulis ulang apa yang dia katakan di sini secara persis. Jika teks, cukup tulis ulang teksnya)
                ===TEKS===
                (Jawab dengan singkat, sangat jelas, memotivasi anak untuk terus berani bertanya. Sesuaikan dengan karaktermu. Gunakan emoji 🌟💡)
                ===SUARA===
                (Versi lisan dari TEKS di atas. DILARANG KERAS MENGGUNAKAN EMOJI SAMA SEKALI)
                """

                # Menyusun data yang akan dikirim ke Gemini (Teks / Audio)
                payload_qa = []
                if pertanyaan_suara:
                    audio_bytes = pertanyaan_suara.read()
                    # Menambahkan prompt dan part audio
                    payload_qa = [
                        prompt_qa + f"\n\nSiswa bernama {nama} ({jenjang_kelas}) bertanya MENGGUNAKAN SUARA (Audio terlampir):",
                        types.Part.from_bytes(data=audio_bytes, mime_type='audio/wav')
                    ]
                else:
                    payload_qa = [prompt_qa + f"\n\nSiswa bernama {nama} ({jenjang_kelas}) bertanya: '{pertanyaan_teks}'"]
                
                try:
                    response_qa = client_gemini.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=payload_qa
                    )
                    
                    full_qa_text = response_qa.text
                    tanya_transkrip = ""
                    jawab_teks = ""
                    jawab_suara = ""
                    
                    # Memecah respon AI
                    match_tr = re.search(r'===TRANSKRIP===(.*?)(?====TEKS===|$)', full_qa_text, re.DOTALL)
                    if match_tr: tanya_transkrip = match_tr.group(1).strip()
                    
                    match_t = re.search(r'===TEKS===(.*?)(?====SUARA===|$)', full_qa_text, re.DOTALL)
                    if match_t: jawab_teks = match_t.group(1).strip()
                    
                    match_s = re.search(r'===SUARA===(.*)', full_qa_text, re.DOTALL)
                    if match_s: 
                        jawab_suara = match_s.group(1).strip()
                        jawab_suara_bersih = re.sub(r'[*#_`>-]', '', jawab_suara)
                        
                        nama_file_dinamis = f"audio_qa_{int(time.time())}.mp3"
                        guru = st.session_state.guru_aktif
                        buat_suara_google(jawab_suara_bersih, nama_file_dinamis, guru['voice'], guru['pitch'], guru['rate'])
                        
                        st.session_state.qa_history.append({
                            "tanya": tanya_transkrip if tanya_transkrip else "Pertanyaan Suara",
                            "jawab_teks": jawab_teks,
                            "file_audio": nama_file_dinamis
                        })
                        
                        st.rerun()
                except Exception as e:
                    st.error(f"Gagal memproses pertanyaan: {e}")
        else:
            st.warning("Eits, kamu belum bertanya apa-apa! Ketik atau rekam suara dulu ya.")

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
