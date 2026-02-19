import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from io import BytesIO
import json
import re

# --- 1. SETTINGS & UTILITIES ---
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah", layout="wide")

def t(value):
    return str(value) if value is not None else ""

def clean_option(opt):
    cleaned = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', str(opt))
    cleaned = re.sub(r'^[A-Ea-e1-5]\.?\s*', '', cleaned)
    return cleaned.strip()

def set_font(run, size=11, bold=False):
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    run.font.size = Pt(size)
    run.bold = bold

# --- 2. DOKUMEN GENERATORS ---

def generate_naskah(data_soal, info):
    doc = Document()
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run(f"PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{t(info['sekolah'])}\n"); set_font(r, 14, True)
    r = p.add_run(f"{t(info['jenis_asesmen']).upper()}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {t(info['tahun'])}\n"); set_font(r, 11, True)
    doc.add_paragraph("_" * 75)
    
    tbl = doc.add_table(3, 2); tbl.autofit = True
    rows = [
        (f"MATA PELAJARAN : {info['mapel']}", f"KELAS : {info['kelas']}"),
        (f"HARI/TANGGAL : .................", f"SEMESTER : {info['semester']}"),
        (f"GURU PENGAMPU : {info['guru']}", f"WAKTU : 90 Menit")
    ]
    for i, (left, right) in enumerate(rows):
        set_font(tbl.rows[i].cells[0].paragraphs[0].add_run(left), 10)
        set_font(tbl.rows[i].cells[1].paragraphs[0].add_run(right), 10)

    no = 1
    for tipe, quests in data_soal.items():
        doc.add_paragraph().add_run(f"\n{tipe.upper()}").bold = True
        for q in quests:
            doc.add_paragraph(f"{no}. {q.get('soal')}")
            if "Pilihan Ganda" in tipe:
                for i, o in enumerate(q.get('opsi', [])[:4]):
                    doc.add_paragraph(f"    {['A','B','C','D'][i]}. {clean_option(o)}")
            no += 1
    return doc

def generate_kunci_kisi(data_soal, info):
    doc = Document()
    doc.add_heading(f"KUNCI JAWABAN & KISI-KISI", 0)
    table = doc.add_table(1, 5); table.style = 'Table Grid'
    hdr = table.rows[0].cells
    for i, txt in enumerate(["No", "Bentuk", "Indikator", "Kunci", "Skor"]): hdr[i].text = txt
    
    idx = 1
    for tipe, quests in data_soal.items():
        for q in quests:
            row = table.add_row().cells
            row[0].text = str(idx); row[1].text = tipe
            row[2].text = q.get('indikator', 'Menganalisis materi')
            row[3].text = str(q.get('kunci', q.get('pedoman', '-')))
            row[4].text = str(q.get('skor', 0))
            idx += 1
    return doc

# --- 3. UI STREAMLIT ---
if 'files' not in st.session_state: st.session_state.files = None
if 'preview_data' not in st.session_state: st.session_state.preview_data = None

with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    sekolah = st.text_input("Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Guru", "Ary Prabowo")
    mapel = st.text_input("Mapel", "Seni Budaya")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun", "2025/2026")

st.title("✅ Generator Administrasi Soal")

jenis_asesmen = st.selectbox("Jenis Asesmen", [
    "Asesmen Sumatif Lingkup Materi", "Asesmen Sumatif Tengah Semester",
    "Asesmen Sumatif Akhir Semester", "Asesmen Formatif Lingkup Materi"
])

pilihan_bentuk = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar/Salah", "Isian Singkat", "Uraian"], default=["Pilihan Ganda", "Uraian"])
conf = {b: st.number_input(f"Jumlah {b}", 1, 40, 5) for b in pilihan_bentuk}
materi = st.text_area("Materi / Kisi-kisi")

if st.button("🚀 PROSES DATA"):
    try:
        genai.configure(api_key=api_key)
        # SOLUSI ERROR 404: Cari model yang aktif
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        active_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else models[0]
        
        model = genai.GenerativeModel(active_model)
        prompt = f"Buat soal {mapel} dari materi {materi}. Bentuk: {json.dumps(conf)}. Berikan output JSON murni."
        
        with st.spinner(f"Menggunakan {active_model}..."):
            res = model.generate_content(prompt)
            data = json.loads(re.search(r'\{.*\}', res.text, re.DOTALL).group())
            st.session_state.preview_data = data
            
            info_data = {'sekolah': sekolah, 'guru': guru, 'mapel': mapel, 'kelas': kelas, 'semester': semester, 'tahun': tahun, 'jenis_asesmen': jenis_asesmen}
            st.session_state.files = {
                'n': generate_naskah(data, info_data),
                'k': generate_kunci_kisi(data, info_data)
            }
            st.success("Selesai!")
    except Exception as e:
        st.error(f"Terjadi Kesalahan: {e}")

# --- 4. DOWNLOAD & PREVIEW ---
if st.session_state.files:
    st.divider()
    c1, c2 = st.columns(2)
    def to_io(d):
        io = BytesIO(); d.save(io); return io.getvalue()
    
    c1.download_button("📥 Naskah Soal", to_io(st.session_state.files['n']), "Naskah.docx", "primary")
    c2.download_button("📥 Kunci & Kisi-kisi", to_io(st.session_state.files['k']), "Administrasi.docx")

    st.subheader("👁️ Preview Soal")
    st.info(f"**{jenis_asesmen}** | Guru: {guru}")
    for tipe, qs in st.session_state.preview_data.items():
        with st.expander(f"Bentuk {tipe}"):
            for i, q in enumerate(qs):
                st.write(f"**{i+1}. {q.get('soal')}**")
                st.caption(f"Kunci: {q.get('kunci', q.get('pedoman'))}")
