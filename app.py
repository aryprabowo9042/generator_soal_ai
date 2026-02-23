import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO
import json
import re
import PyPDF2

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Generator Soal SMPM 1 Weleri", layout="wide")

# Persistent Session State untuk API Key dan Data
if "api_key_saved" not in st.session_state:
    st.session_state.api_key_saved = ""
if "files" not in st.session_state:
    st.session_state.files = None

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    div.stButton > button {
        background-color: #2563eb; color: white; border-radius: 0.5rem;
        padding: 0.6rem 1.2rem; font-weight: 600; width: 100%;
    }
    .arabic-text { font-family: 'Sakkal Majalla', 'Traditional Arabic', serif; direction: rtl; text-align: right; font-size: 24px; line-height: 1.8; }
    </style>
    """, unsafe_allow_html=True)

# --- UTILS RTL & FONT ---
def set_rtl(paragraph):
    pPr = paragraph._element.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    bidi.set(qn('w:val'), '1')
    pPr.append(bidi)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

def set_font(run, size=11, bold=False, is_arabic=False):
    if is_arabic:
        run.font.name = 'Traditional Arabic'
        run._element.rPr.rFonts.set(qn('w:ascii'), 'Traditional Arabic')
        run._element.rPr.rFonts.set(qn('w:hAnsi'), 'Traditional Arabic')
        run._element.rPr.rFonts.set(qn('w:cs'), 'Traditional Arabic')
        run.font.size = Pt(size + 5)
    else:
        run.font.name = 'Times New Roman'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
        run.font.size = Pt(size)
    run.bold = bold

def clean_json_output(text):
    text = re.sub(r'```json\s*|\s*```', '', text)
    start = text.find('{')
    end = text.rfind('}') + 1
    return text[start:end] if start != -1 else text

# --- 2. DOKUMEN GENERATORS ---

def create_header(doc, info, title_suffix=""):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run("PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{info['sekolah']}\n"); set_font(r, 14, True)
    r = p.add_run(f"{info['jenis_asesmen'].upper()} {title_suffix}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {info['tahun']}\n"); set_font(r, 11, True)
    doc.add_paragraph("_" * 75)
    
    tbl = doc.add_table(3, 2)
    rows = [
        (f"MATA PELAJARAN : {info['mapel']}", f"WAKTU : 90 Menit"),
        (f"HARI/TANGGAL : .................", f"KELAS : {info['kelas']} / {info['semester']}"),
        (f"GURU PENGAMPU : {info['guru']}", "")
    ]
    for i, (left, right) in enumerate(rows):
        set_font(tbl.rows[i].cells[0].paragraphs[0].add_run(left), 10)
        set_font(tbl.rows[i].cells[1].paragraphs[0].add_run(right), 10)
    doc.add_paragraph()

def generate_naskah(data_list, info):
    doc = Document(); create_header(doc, info)
    is_arab = "arab" in info['mapel'].lower()
    no = 1
    grouped = {}
    for q in data_list:
        tipe = q.get('tipe', 'Uraian')
        if tipe not in grouped: grouped[tipe] = []
        grouped[tipe].append(q)

    for tipe, quests in grouped.items():
        p_tipe = doc.add_paragraph()
        r_tipe = p_tipe.add_run(f"\n{tipe.upper()}")
        set_font(r_tipe, 11, True)
        for q in quests:
            p_soal = doc.add_paragraph()
            if is_arab: set_rtl(p_soal)
            run_no = p_soal.add_run(f"{no}. ")
            set_font(run_no, 11)
            run_text = p_soal.add_run(q.get('soal', ''))
            set_font(run_text, 12, is_arabic=is_arab)
            if "Pilihan Ganda" in tipe:
                opsi = q.get('opsi', [])
                labels = ['أ', 'ب', 'ج', 'د'] if is_arab else ['A', 'B', 'C', 'D']
                for i, o in enumerate(opsi[:4]):
                    p_opt = doc.add_paragraph()
                    if is_arab: set_rtl(p_opt)
                    run_opt = p_opt.add_run(f"    {labels[i]}. {o}")
                    set_font(run_opt, 11, is_arabic=is_arab)
            no += 1
    return doc

def generate_kunci(data_list, info):
    doc = Document(); create_header(doc, info, "- KUNCI JAWABAN")
    table = doc.add_table(rows=1, cols=4); table.style = 'Table Grid'
    for i, h in enumerate(["No", "Tipe", "Kunci/Pedoman", "Skor"]):
        table.rows[0].cells[i].text = h
    for i, q in enumerate(data_list):
        row = table.add_row().cells
        row[0].text = str(i+1); row[1].text = q.get('tipe', '-'); row[2].text = f"{q.get('kunci', '-')}\n{q.get('pedoman', '')}"; row[3].text = str(round(q.get('skor', 0), 1))
    return doc

def generate_kartu(data_list, info):
    doc = Document()
    is_arab = "arab" in info['mapel'].lower()
    for i, q in enumerate(data_list):
        doc.add_heading(f"KARTU SOAL NOMOR {i+1}", 1)
        table = doc.add_table(rows=5, cols=2); table.style = 'Table Grid'
        cells = [("Mata Pelajaran", info['mapel']), ("Kelas/Semester", f"{info['kelas']}/{info['semester']}"), ("Indikator Soal", q.get('indikator', '-')), ("Butir Soal", q.get('soal', '')), ("Kunci Jawaban", q.get('kunci', '-'))]
        for idx, (label, val) in enumerate(cells):
            table.cell(idx, 0).text = label
            p = table.cell(idx, 1).paragraphs[0]
            if is_arab and idx >= 3: set_rtl(p)
            run = p.add_run(str(val))
            set_font(run, 11, is_arabic=(is_arab and idx >= 3))
        doc.add_page_break()
    return doc

# --- 3. UI UTAMA ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/Muhammadiyah_Logo.svg/1200px-Muhammadiyah_Logo.svg.png", width=60)
    st.header("⚙️ Konfigurasi")
    
    # Simpan API key ke session state saat diketik
    api_key_input = st.text_input("Gemini API Key", value=st.session_state.api_key_saved, type="password")
    if api_key_input != st.session_state.api_key_saved:
        st.session_state.api_key_saved = api_key_input
        st.rerun()

    st.divider()
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    guru = st.text_input("Nama Guru Pengampu", "Ary Prabowo")
    mapel = st.text_input("Mata Pelajaran", "Bahasa Arab")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")

st.title("📝 Generator Administrasi Soal v6.7")

col_m1, col_m2 = st.columns(2)
with col_m1: materi_manual = st.text_area("Input Teks Materi", height=150)
with col_m2: uploaded_file = st.file_uploader("Upload PDF Materi", type=['pdf'])

col_b1, col_b2 = st.columns([2, 1])
with col_b1:
    jenis_asesmen = st.selectbox("Jenis Asesmen", ["Asesmen Tengah Semester", "Asesmen Akhir Semester", "Asesmen Formatif"])
    bentuk_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar / Salah", "Isian Singkat", "Uraian"], default=["Pilihan Ganda", "Uraian"])
with col_b2:
    conf = {b: st.number_input(f"Jumlah {b}", 1, 30, 5) for b in bentuk_soal}

if st.button("🚀 GENERATE SEMUA DOKUMEN"):
    if not st.session_state.api_key_saved:
        st.error("Silakan isi API Key di Sidebar!"); st.stop()
    
    try:
        genai.configure(api_key=st.session_state.api_key_saved)
        materi_full = materi_manual
        if uploaded_file:
            reader = PyPDF2.PdfReader(uploaded_file)
            materi_full += " ".join([p.extract_text() for p in reader.pages])

        is_arab = "arab" in mapel.lower()
        prompt = f"""Buat soal {mapel} untuk {jenis_asesmen}. Materi: {materi_full[:6000]}. Jumlah: {json.dumps(conf)}.
        {'Gunakan Bahasa Arab berharakat' if is_arab else ''}. Output JSON murni:
        {{ "soal_list": [ {{ "tipe": "", "soal": "", "opsi": [], "kunci": "", "pedoman": "", "indikator": "", "skor": 5 }} ] }}"""

        model = genai.GenerativeModel('gemini-1.5-flash')
        with st.spinner("AI sedang merancang administrasi soal..."):
            res = model.generate_content(prompt)
            data = json.loads(clean_json_output(res.text))
            soal_list = data.get('soal_list', [])
            
            # Normalisasi skor
            total = sum(q.get('skor', 0) for q in soal_list)
            if total > 0:
                for q in soal_list: q['skor'] = (q['skor']/total) * 100

            info = {'sekolah': sekolah, 'guru': guru, 'mapel': mapel, 'kelas': kelas, 'semester': semester, 'tahun': tahun, 'jenis_asesmen': jenis_asesmen}
            
            st.session_state.preview_data = soal_list
            st.session_state.files = {
                'n': generate_naskah(soal_list, info),
                'k': generate_kunci(soal_list, info),
                'ks': generate_kartu(soal_list, info)
            }
            st.success("Dokumen Berhasil Dibuat!")
    except Exception as e:
        st.error(f"Gagal: {e}")

# --- 4. DOWNLOAD ---
if st.session_state.files:
    st.divider()
    c1, c2, c3 = st.columns(3)
    def to_io(doc):
        io = BytesIO(); doc.save(io); return io.getvalue()

    c1.download_button("📥 Naskah Soal", to_io(st.session_state.files['n']), "Naskah_Soal.docx")
    c2.download_button("📥 Kunci Jawaban", to_io(st.session_state.files['k']), "Kunci_Jawaban.docx")
    c3.download_button("📥 Kartu Soal", to_io(st.session_state.files['ks']), "Kartu_Soal.docx")

    st.subheader("Preview Soal")
    is_arab = "arab" in mapel.lower()
    for i, q in enumerate(st.session_state.preview_data):
        with st.expander(f"Soal {i+1} - {q.get('tipe')}"):
            if is_arab: st.markdown(f"<div class='arabic-text'>{q['soal']}</div>", unsafe_allow_html=True)
            else: st.write(q['soal'])
