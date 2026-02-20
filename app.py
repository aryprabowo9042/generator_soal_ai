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

# --- 1. SETTINGS & UTILITIES ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah", layout="wide")

def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def clean_option(opt):
    if not opt or not isinstance(opt, str): return str(opt)
    cleaned = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', opt)
    cleaned = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', cleaned)
    return cleaned.strip()

def set_font(run, size=11, bold=False):
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    run.font.size = Pt(size)
    run.bold = bold

# --- 2. DOKUMEN GENERATORS ---

def create_header(doc, info):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run("PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{info.get('sekolah', '')}\n"); set_font(r, 14, True)
    r = p.add_run(f"{info.get('jenis_asesmen', '').upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {info.get('tahun', '')}\n"); set_font(r, 11, True)
    doc.add_paragraph("_" * 75)
    
    tbl = doc.add_table(3, 2); tbl.autofit = True
    rows = [
        (f"MATA PELAJARAN : {info.get('mapel', '')}", f"KELAS : {info.get('kelas', '')}"),
        (f"HARI/TANGGAL : .................", f"SEMESTER : {info.get('semester', '')}"),
        (f"GURU PENGAMPU : {info.get('guru', '')}", f"WAKTU : 90 Menit")
    ]
    for i, (left, right) in enumerate(rows):
        set_font(tbl.rows[i].cells[0].paragraphs[0].add_run(left), 10)
        set_font(tbl.rows[i].cells[1].paragraphs[0].add_run(right), 10)
    doc.add_paragraph()

def generate_naskah(data_soal, info):
    doc = Document(); create_header(doc, info)
    no = 1
    for tipe, quests in data_soal.items():
        if not isinstance(quests, list): continue
        doc.add_paragraph().add_run(f"\n{str(tipe).upper()}").bold = True
        for q in quests:
            if not isinstance(q, dict): continue
            doc.add_paragraph(f"{no}. {q.get('soal', '')}")
            if "Pilihan Ganda" in str(tipe):
                opsi = q.get('opsi', [])
                if isinstance(opsi, list):
                    for i, o in enumerate(opsi[:4]):
                        doc.add_paragraph(f"    {['A','B','C','D'][i]}. {clean_option(o)}")
            no += 1
    return doc

def generate_kisi_kunci(data_soal, info):
    doc = Document()
    doc.add_heading("KISI-KISI & KUNCI JAWABAN", 1)
    table = doc.add_table(1, 6); table.style = 'Table Grid'
    for i, h in enumerate(["No", "Indikator", "Bentuk", "Kunci/Pedoman", "Skor", "Level"]):
        table.rows[0].cells[i].text = h
    
    idx = 1
    for tipe, quests in data_soal.items():
        if not isinstance(quests, list): continue
        for q in quests:
            if not isinstance(q, dict): continue
            row = table.add_row().cells
            row[0].text = str(idx)
            row[1].text = str(q.get('indikator', '-'))
            row[2].text = str(tipe)
            row[3].text = str(q.get('kunci', q.get('pedoman', '-')))
            row[4].text = str(q.get('skor', 0))
            row[5].text = str(q.get('level', 'L2'))
            idx += 1
    return doc

def generate_kartu(data_soal, info):
    doc = Document()
    doc.add_heading("KARTU SOAL", 1)
    idx = 1
    for tipe, quests in data_soal.items():
        if not isinstance(quests, list): continue
        for q in quests:
            if not isinstance(q, dict): continue
            tbl = doc.add_table(4, 2); tbl.style = 'Table Grid'
            tbl.cell(0, 0).text = f"No Soal: {idx}"; tbl.cell(0, 1).text = f"Bentuk: {str(tipe)}"
            tbl.cell(1, 0).merge(tbl.cell(1, 1)).text = f"Indikator: {str(q.get('indikator', '-'))}"
            tbl.cell(2, 0).merge(tbl.cell(2, 1)).text = f"Soal: {str(q.get('soal', ''))}"
            tbl.cell(3, 0).text = f"Kunci: {str(q.get('kunci', '-'))}"; tbl.cell(3, 1).text = f"Skor: {str(q.get('skor', 0))}"
            doc.add_paragraph()
            idx += 1
    return doc

# --- 3. UI STREAMLIT ---
if 'preview_data' not in st.session_state: st.session_state.preview_data = None
if 'files' not in st.session_state: st.session_state.files = None

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru Pengampu", "Ary Prabowo")
    mapel = st.text_input("Mata Pelajaran", "Seni Budaya")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")

st.title("📝 Generator Administrasi Soal (Support File)")

jenis_asesmen = st.selectbox("Jenis Asesmen", [
    "Asesmen Sumatif Lingkup Materi", "Asesmen Sumatif Tengah Semester",
    "Asesmen Sumatif Akhir Semester", "Asesmen Formatif Lingkup Materi"
])

# FITUR UPLOAD FILE
uploaded_file = st.file_uploader("Unggah Materi (PDF/DOCX)", type=['pdf', 'docx'])
materi_input = st.text_area("Atau Ketik Materi di sini", height=100)

bentuk_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar/Salah", "Isian Singkat", "Uraian"], default=["Pilihan Ganda", "Uraian"])
conf = {b: st.number_input(f"Jumlah {b}", 1, 50, 5) for b in bentuk_soal}

if st.button("🚀 PROSES DATA"):
    if not api_key: st.error("Isi API Key!"); st.stop()
    
    # Ambil materi dari file atau input teks
    final_materi = materi_input
    if uploaded_file:
        with st.spinner("Membaca file..."):
            if uploaded_file.type == "application/pdf":
                final_materi = extract_text_from_pdf(uploaded_file)
            else:
                final_materi = extract_text_from_docx(uploaded_file)
    
    if not final_materi: st.error("Materi tidak ditemukan!"); st.stop()

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""Buat soal {mapel} untuk {jenis_asesmen}. Materi: {final_materi[:8000]}. 
        Jumlah: {json.dumps(conf)}. TOTAL SKOR 100.
        Berikan JSON murni: {{ "Tipe": [ {{ "soal": "isi", "opsi": ["A", "B", "C", "D"], "kunci": "A", "indikator": "...", "skor": 2, "level": "L2" }} ] }}"""
        
        with st.spinner("AI sedang memproses materi..."):
            res = model.generate_content(prompt)
            match = re.search(r'\{.*\}', res.text, re.DOTALL)
            if match:
                raw_data = json.loads(match.group())
                if isinstance(raw_data, dict):
                    st.session_state.preview_data = raw_data
                    info_dict = {'sekolah': sekolah, 'guru': guru, 'mapel': mapel, 'kelas': kelas, 'semester': semester, 'tahun': tahun, 'jenis_asesmen': jenis_asesmen}
                    st.session_state.files = {
                        'n': generate_naskah(raw_data, info_dict),
                        'k': generate_kisi_kunci(raw_data, info_dict),
                        's': generate_kartu(raw_data, info_dict)
                    }
                    st.success("Administrasi Berhasil Dibuat!")
            else:
                st.error("AI gagal menghasilkan format data yang benar.")
    except Exception as e:
        st.error(f"Kesalahan: {e}")

# --- 4. OUTPUT ---
if st.session_state.files and st.session_state.preview_data:
    st.divider()
    c1, c2, c3 = st.columns(3)
    def to_io(doc):
        io = BytesIO(); doc.save(io); return io.getvalue()

    c1.download_button("📝 Naskah Soal", to_io(st.session_state.files['n']), "Naskah.docx", "primary")
    c2.download_button("🔑 Kisi & Kunci", to_io(st.session_state.files['k']), "Kisi_Kunci.docx")
    c3.download_button("🗂️ Kartu Soal", to_io(st.session_state.files['s']), "Kartu_Soal.docx")

    st.divider()
    st.subheader("👁️ Preview")
    for tipe, qs in st.session_state.preview_data.items():
        if isinstance(qs, list):
            with st.expander(f"Bagian: {tipe}"):
                for i, q in enumerate(qs):
                    if isinstance(q, dict):
                        st.write(f"**{i+1}. {q.get('soal', '')}**")
