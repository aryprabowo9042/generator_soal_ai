import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from io import BytesIO
import json
import re
import PyPDF2

# --- 1. KONFIGURASI & UTILITAS ---
st.set_page_config(page_title="Generator Administrasi Soal SMP Muhammadiyah 1 Weleri", layout="wide")

def clean_option(opt):
    """Menghapus label ganda (A. A. -> Isi Jawaban)"""
    if not opt: return ""
    text = str(opt)
    text = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', text).strip()
    text = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', text).strip()
    return text

def set_font(run, size=11, bold=False):
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    run.font.size = Pt(size)
    run.bold = bold

# --- 2. GENERATOR DOKUMEN SESUAI TEMPLATE ---

def create_header(doc, info):
    """Header sesuai BENTUK FORMAT SOAL ATS GENAP.docx"""
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run("PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{info['sekolah']}\n"); set_font(r, 14, True)
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

def generate_naskah(data_soal, info):
    doc = Document(); create_header(doc, info)
    no = 1
    for tipe, quests in data_soal.items():
        if not isinstance(quests, list): continue
        doc.add_paragraph().add_run(f"\n{tipe.upper()}").bold = True
        for q in quests:
            if not isinstance(q, dict): continue
            doc.add_paragraph(f"{no}. {q.get('soal', '')}")
            if "Pilihan Ganda" in tipe:
                for i, o in enumerate(q.get('opsi', [])[:4]):
                    doc.add_paragraph(f"    {['A','B','C','D'][i]}. {clean_option(o)}")
            no += 1
    return doc

def generate_kisi_kisi(data_soal, info):
    """Sesuai KISI-KISI.docx"""
    doc = Document()
    doc.add_heading(f"KISI-KISI SOAL {info['jenis_asesmen']}", 1)
    p = doc.add_paragraph()
    p.add_run(f"Mata Pelajaran: {info['mapel']}\nKelas/Semester: {info['kelas']}/{info['semester']}")
    
    table = doc.add_table(1, 6); table.style = 'Table Grid'
    hdrs = ["No", "TP/KD", "Indikator Soal", "Level", "Bentuk Soal", "No Soal"]
    for i, h in enumerate(hdrs): table.rows[0].cells[i].text = h
    
    idx = 1
    for tipe, quests in data_soal.items():
        for q in quests:
            row = table.add_row().cells
            row[0].text = str(idx)
            row[2].text = q.get('indikator', '-')
            row[3].text = q.get('level', 'L2')
            row[4].text = tipe
            row[5].text = str(idx)
            idx += 1
    return doc

def generate_kartu_soal(data_soal, info):
    """Sesuai KARTU SOAL.docx"""
    doc = Document()
    doc.add_heading("KARTU SOAL", 1)
    idx = 1
    for tipe, quests in data_soal.items():
        for q in quests:
            tbl = doc.add_table(6, 2); tbl.style = 'Table Grid'
            tbl.cell(0, 0).text = "Nomor Soal"; tbl.cell(0, 1).text = str(idx)
            tbl.cell(1, 0).text = "Bentuk Soal"; tbl.cell(1, 1).text = tipe
            tbl.cell(2, 0).text = "Indikator Soal"; tbl.cell(2, 1).text = q.get('indikator', '-')
            tbl.cell(3, 0).text = "Butir Soal"; tbl.cell(3, 1).text = q.get('soal', '')
            
            # Kunci atau Pedoman Penskoran
            label = "Pedoman Penskoran" if "Uraian" in tipe else "Kunci Jawaban"
            tbl.cell(4, 0).text = label; tbl.cell(4, 1).text = str(q.get('kunci', q.get('pedoman', '-')))
            tbl.cell(5, 0).text = "Skor"; tbl.cell(5, 1).text = str(q.get('skor', 5))
            doc.add_paragraph()
            idx += 1
    return doc

# --- 3. UI & LOGIKA ---
with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru Pengampu", "Ary Prabowo")
    mapel = st.text_input("Mata Pelajaran", "Seni Budaya")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")

st.title("🚀 Smart Generator Administrasi Soal")

uploaded_file = st.file_uploader("Unggah Materi (PDF)", type=['pdf'])
bentuk_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Benar / Salah", "Uraian"], default=["Pilihan Ganda", "Uraian"])
conf = {b: st.number_input(f"Jumlah {b}", 1, 20, 5) for b in bentuk_soal}

if st.button("🚀 PROSES DATA"):
    if not api_key: st.error("Isi API Key!"); st.stop()
    
    try:
        genai.configure(api_key=api_key)
        # Ekstrak PDF
        materi = ""
        if uploaded_file:
            reader = PyPDF2.PdfReader(uploaded_file)
            materi = " ".join([p.extract_text() for p in reader.pages])
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""Buat soal {mapel} berdasarkan materi: {materi[:7000]}. 
        Jumlah: {json.dumps(conf)}. Format JSON murni tanpa label abjad di isi opsi. 
        Sertakan field: 'soal', 'opsi' (untuk PG), 'kunci', 'indikator', 'skor', 'pedoman' (untuk uraian), 'level' (LOTS/HOTS)."""
        
        with st.spinner("AI sedang menyusun administrasi sesuai template..."):
            res = model.generate_content(prompt)
            data = json.loads(re.search(r'\{.*\}', res.text, re.DOTALL).group())
            st.session_state.preview_data = data
            
            info = {'sekolah':sekolah, 'guru':guru, 'mapel':mapel, 'kelas':kelas, 'semester':semester, 'tahun':tahun, 'jenis_asesmen':"Asesmen Tengah Semester Genap"}
            st.session_state.files = {
                'n': generate_naskah(data, info),
                'k': generate_kisi_kisi(data, info),
                's': generate_kartu_soal(data, info)
            }
            st.success("Administrasi Berhasil Dibuat!")
    except Exception as e:
        st.error(f"Terjadi Kesalahan: {e}")

# --- 4. PREVIEW & DOWNLOAD ---
if st.session_state.get('files'):
    st.divider()
    cols = st.columns(3)
    def get_io(doc):
        io = BytesIO(); doc.save(io); return io.getvalue()

    cols[0].download_button("📝 Unduh Naskah", get_io(st.session_state.files['n']), "Naskah_Soal.docx", "primary")
    cols[1].download_button("🔑 Unduh Kisi-kisi", get_io(st.session_state.files['k']), "Kisi_Kisi.docx")
    cols[2].download_button("🗂️ Unduh Kartu Soal", get_io(st.session_state.files['s']), "Kartu_Soal.docx")

    st.subheader("👁️ Preview Soal & Pedoman Penskoran")
    for tipe, qs in st.session_state.preview_data.items():
        with st.expander(f"Bagian: {tipe}"):
            for i, q in enumerate(qs):
                st.write(f"**{i+1}. {q.get('soal')}**")
                if "Pilihan Ganda" in tipe:
                    st.caption(f"Kunci: {q.get('kunci')} | Indikator: {q.get('indikator')}")
                else:
                    st.info(f"Pedoman Penskoran: {q.get('pedoman', 'Jawaban benar skor penuh')}")
