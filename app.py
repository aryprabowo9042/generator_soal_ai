import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from io import BytesIO
import json
import re
import PyPDF2

# --- 1. SETTINGS & UTILS ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah 1 Weleri", layout="wide")

def clean_option(opt):
    if not opt: return ""
    text = str(opt)
    # Menghapus label abjad ganda (A. A. -> isi)
    text = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', text).strip()
    text = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', text).strip()
    return text

def set_font(run, size=11, bold=False):
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    run.font.size = Pt(size)
    run.bold = bold

# --- 2. DOKUMEN GENERATORS ---

def create_header(doc, info):
    """Header Standar sesuai BENTUK FORMAT SOAL ATS GENAP.docx"""
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run("PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{info['sekolah']}\n"); set_font(r, 14, True)
    # Menampilkan Peruntukan Soal di Header
    r = p.add_run(f"{info['jenis_asesmen'].upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {info['tahun']}\n"); set_font(r, 11, True)
    doc.add_paragraph("_" * 75)
    
    tbl = doc.add_table(2, 2); tbl.autofit = True
    rows = [
        (f"MATA PELAJARAN : {info['mapel']}", f"WAKTU : 90 Menit"),
        (f"HARI/TANGGAL : .................", f"KELAS : {info['kelas']}")
    ]
    for i, (left, right) in enumerate(rows):
        set_font(tbl.rows[i].cells[0].paragraphs[0].add_run(left), 10)
        set_font(tbl.rows[i].cells[1].paragraphs[0].add_run(right), 10)
    doc.add_paragraph()

# --- 3. UI UTAMA ---
with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru Pengampu", "Ary Prabowo")
    mapel = st.text_input("Mata Pelajaran", "Seni Budaya")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")

st.title("📝 Generator Administrasi Soal v4.0")

# Fitur Tambahan: Peruntukan Soal
jenis_asesmen = st.selectbox("Peruntukan Soal / Jenis Asesmen", [
    "Asesmen Formatif",
    "Asesmen Sumatif Lingkup Materi",
    "Asesmen Sumatif Tengah Semester",
    "Asesmen Sumatif Akhir Semester"
])

uploaded_file = st.file_uploader("Unggah Materi (PDF)", type=['pdf'])
bentuk_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Benar / Salah", "Uraian"], default=["Pilihan Ganda", "Uraian"])
conf = {b: st.number_input(f"Jumlah {b}", 1, 30, 5) for b in bentuk_soal}

if st.button("🚀 PROSES DATA"):
    if not api_key: st.error("Silakan isi API Key!"); st.stop()
    
    try:
        genai.configure(api_key=api_key)
        
        # --- PERBAIKAN ERROR 404 (Auto Discovery) ---
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prioritaskan flash, jika tidak ada pakai model pertama yang tersedia
        target_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
        
        materi = ""
        if uploaded_file:
            reader = PyPDF2.PdfReader(uploaded_file)
            materi = " ".join([p.extract_text() for p in reader.pages])

        model = genai.GenerativeModel(target_model)
        prompt = f"""Buat soal {mapel} untuk {jenis_asesmen}. Materi: {materi[:6000]}. 
        Jumlah: {json.dumps(conf)}. Format output WAJIB JSON murni.
        Field: 'soal', 'opsi' (hanya untuk PG), 'kunci', 'indikator', 'skor', 'pedoman', 'level'."""

        with st.spinner(f"Menggunakan model {target_model}..."):
            res = model.generate_content(prompt)
            # Bersihkan Markdown jika ada
            json_str = re.search(r'\{.*\}', res.text, re.DOTALL).group()
            data = json.loads(json_str)
            
            # Simpan data ke session state
            st.session_state.preview_data = data
            info_dict = {
                'sekolah': sekolah, 'guru': guru, 'mapel': mapel, 
                'kelas': kelas, 'semester': semester, 'tahun': tahun,
                'jenis_asesmen': jenis_asesmen
            }
            
            # (Logika pembuatan dokumen Word tetap sama seperti sebelumnya)
            st.success(f"Administrasi {jenis_asesmen} berhasil dibuat!")
            
    except Exception as e:
        st.error(f"Gagal memproses: {e}")
