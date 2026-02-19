import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from io import BytesIO
import json
import re

# --- 1. SETTINGS ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah", layout="wide")

def clean_option(opt):
    cleaned = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', str(opt))
    return re.sub(r'^[A-Ea-e1-5]\.?\s*', '', cleaned).strip()

def set_font(run, size=11, bold=False):
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    run.font.size = Pt(size)
    run.bold = bold

# --- 2. DOKUMEN GENERATORS (NASKA, KISI, KARTU, KUNCI) ---
def generate_all_docs(data_soal, info):
    # Naskah Soal
    d_naskah = Document()
    # (isi naskah soal seperti sebelumnya)
    
    # Kunci & Kisi-Kisi
    d_kunci = Document()
    d_kunci.add_heading(f"KUNCI JAWABAN & KISI-KISI {info['mapel']}", 0)
    # (tabel kisi-kisi dan kunci)

    # Kartu Soal
    d_kartu = Document()
    d_kartu.add_heading("KARTU SOAL", 0)
    # (format kartu soal per nomor)

    return d_naskah, d_kunci, d_kartu

# --- 3. UI ---
# Pastikan session state selalu siap
if 'preview_data' not in st.session_state: st.session_state.preview_data = None
if 'files' not in st.session_state: st.session_state.files = None

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    sekolah = st.text_input("Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru", "Ary Prabowo")
    mapel = st.text_input("Mapel", "Seni Budaya")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun", "2025/2026")

st.title("✅ Generator Soal & Administrasi Lengkap")

jenis_asesmen = st.selectbox("Jenis Asesmen", [
    "Asesmen Sumatif Lingkup Materi", "Asesmen Sumatif Tengah Semester",
    "Asesmen Sumatif Akhir Semester", "Asesmen Formatif Lingkup Materi"
])

bentuk_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar/Salah", "Isian Singkat", "Uraian"], default=["Pilihan Ganda", "Uraian"])
conf = {b: st.number_input(f"Jumlah {b}", 1, 50, 5) for b in bentuk_soal}
materi = st.text_area("Materi / Kisi-kisi", height=150)

if st.button("🚀 PROSES DATA"):
    if not api_key: st.error("Masukkan API Key!"); st.stop()
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"Buat soal {mapel} untuk {jenis_asesmen}. Materi: {materi}. Jumlah: {json.dumps(conf)}. Berikan output JSON murni."
        
        with st.spinner("AI sedang bekerja..."):
            res = model.generate_content(prompt)
            match = re.search(r'\{.*\}', res.text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                st.session_state.preview_data = data
                
                info_data = {'sekolah': sekolah, 'guru': guru, 'mapel': mapel, 'kelas': kelas, 'semester': semester, 'tahun': tahun, 'jenis_asesmen': jenis_asesmen}
                
                # Generate semua dokumen
                n, k, s = generate_all_docs(data, info_data)
                
                # Simpan ke session state agar tidak hilang
                st.session_state.files = {'n': n, 'k': k, 's': s}
                st.success("Data Berhasil Diolah!")
            else:
                st.error("Gagal mengambil data JSON. Coba lagi.")
    except Exception as e:
        st.error(f"Terjadi Kesalahan: {e}")

# --- 4. TAMPILAN DOWNLOAD & PREVIEW (DILUAR TOMBOL PROSES) ---
if st.session_state.preview_data and st.session_state.files:
    st.divider()
    st.subheader("📥 Unduh Dokumen Administrasi")
    col1, col2, col3 = st.columns(3)
    
    def to_io(doc):
        io = BytesIO(); doc.save(io); return io.getvalue()

    col1.download_button("📝 Naskah Soal", to_io(st.session_state.files['n']), "Naskah.docx", "primary")
    col2.download_button("🔑 Kunci & Kisi-Kisi", to_io(st.session_state.files['k']), "Kunci_dan_Kisi.docx")
    col3.download_button("🗂️ Kartu Soal", to_io(st.session_state.files['s']), "Kartu_Soal.docx")

    st.divider()
    st.subheader("👁️ Preview Soal")
    for tipe, qs in st.session_state.preview_data.items():
        with st.expander(f"Bentuk: {tipe}"):
            for i, q in enumerate(qs):
                st.write(f"**{i+1}. {q.get('soal')}**")
                if "Pilihan Ganda" in tipe:
                    for opt in q.get('opsi', []): st.write(f"- {clean_option(opt)}")
                st.caption(f"Kunci: {q.get('kunci', q.get('pedoman'))}")
