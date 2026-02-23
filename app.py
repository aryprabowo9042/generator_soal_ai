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
st.set_page_config(page_title="Generator Soal SMP Muhammadiyah 1 Weleri", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    div.stButton > button {
        background-color: #2563eb; color: white; border-radius: 0.5rem;
        padding: 0.6rem 1.2rem; border: none; font-weight: 600; transition: all 0.2s; width: 100%;
    }
    div.stButton > button:hover {
        background-color: #1d4ed8; transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
    h1, h2, h3 { color: #1e3a8a !important; font-family: 'Inter', sans-serif; }
    .stAlert { border-radius: 0.75rem; border: none; }
    .arabic-text { font-family: 'Sakkal Majalla', 'Traditional Arabic', serif; direction: rtl; text-align: right; font-size: 24px; line-height: 1.8; }
    </style>
    """, unsafe_allow_html=True)

# --- UTILS ---
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

def get_api_key():
    if "GEMINI_API_KEY" in st.secrets: return st.secrets["GEMINI_API_KEY"]
    return ""

def clean_json_output(text):
    try:
        # Menghapus markdown code blocks jika ada
        text = re.sub(r'```json\s*|\s*```', '', text)
        start = text.find('{')
        end = text.rfind('}') + 1
        return text[start:end] if start != -1 else text
    except: return text

# --- 2. DOKUMEN GENERATORS ---

def create_header(doc, info, title_suffix=""):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAJELIS PENDIDIKAN DASAR MENENGAH DAN NON FORMAL\n"); set_font(r, 11, True)
    r = p.add_run("PIMPINAN CABANG MUHAMMADIYAH WELERI\n"); set_font(r, 12, True)
    r = p.add_run(f"{info['sekolah']}\n"); set_font(r, 14, True)
    r = p.add_run(f"{info['jenis_asesmen'].upper()} {title_suffix}\n"); set_font(r, 12, True)
    r = p.add_run(f"TAHUN PELAJARAN {info['tahun']}\n"); set_font(r, 11, True)
    doc.add_paragraph("_" * 75)
    
    tbl = doc.add_table(2, 2)
    rows = [
        (f"MATA PELAJARAN : {info['mapel']}", f"WAKTU : 90 Menit"),
        (f"HARI/TANGGAL : .................", f"KELAS : {info['kelas']} / {info['semester']}")
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
        t = q.get('tipe', 'Soal')
        if t not in grouped: grouped[t] = []
        grouped[t].append(q)

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
            elif "Benar / Salah" in tipe:
                p_bs = doc.add_paragraph("    ....... ( ) Benar   ( ) Salah")
                if is_arab: set_rtl(p_bs)
            no += 1
    return doc

def generate_kunci_pedoman(data_list, info):
    doc = Document(); create_header(doc, info, "- KUNCI JAWABAN")
    table = doc.add_table(rows=1, cols=4); table.style = 'Table Grid'
    for i, h in enumerate(["No", "Tipe", "Kunci/Pedoman", "Skor"]):
        table.rows[0].cells[i].text = h
    
    for i, q in enumerate(data_list):
        row = table.add_row().cells
        row[0].text = str(i+1)
        row[1].text = q.get('tipe', '-')
        row[2].text = f"Kunci: {q.get('kunci', '-')}\n{q.get('pedoman', '')}"
        row[3].text = str(round(q.get('skor', 0), 1))
    return doc

def generate_kisi_kisi(data_list, info):
    doc = Document()
    doc.add_heading(f"KISI-KISI {info['mapel']}", 0)
    table = doc.add_table(rows=1, cols=5); table.style = 'Table Grid'
    for i, h in enumerate(["No", "Indikator", "Level", "Bentuk", "No Soal"]):
        table.rows[0].cells[i].text = h
    for i, q in enumerate(data_list):
        row = table.add_row().cells
        row[0].text = str(i+1)
        row[1].text = q.get('indikator', '-')
        row[2].text = q.get('level', 'L2')
        row[3].text = q.get('tipe', '-')
        row[4].text = str(i+1)
    return doc

def generate_kartu(data_list, info):
    doc = Document()
    for i, q in enumerate(data_list):
        doc.add_heading(f"Kartu Soal No. {i+1}", 1)
        tbl = doc.add_table(rows=4, cols=2); tbl.style = 'Table Grid'
        tbl.cell(0,0).text = "Indikator"; tbl.cell(0,1).text = q.get('indikator', '-')
        tbl.cell(1,0).text = "Soal"; tbl.cell(1,1).text = q.get('soal', '')
        tbl.cell(2,0).text = "Kunci"; tbl.cell(2,1).text = str(q.get('kunci', ''))
        tbl.cell(3,0).text = "Skor"; tbl.cell(3,1).text = str(round(q.get('skor', 0), 1))
        doc.add_page_break()
    return doc

# --- 3. UI UTAMA ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/Muhammadiyah_Logo.svg/1200px-Muhammadiyah_Logo.svg.png", width=80)
    st.header("⚙️ Konfigurasi")
    api_key = st.text_input("Gemini API Key", value=get_api_key(), type="password")
    st.divider()
    sekolah = st.text_input("Nama Sekolah", "SMP MUHAMMADIYAH 1 WELERI")
    mapel = st.text_input("Mata Pelajaran", "Bahasa Arab")
    kelas = st.text_input("Kelas", "IX")
    semester = st.selectbox("Semester", ["Gasal", "Genap"])
    tahun = st.text_input("Tahun Pelajaran", "2025/2026")

st.title("📝 Generator Administrasi Soal AI")

with st.container():
    st.subheader("📖 Input Materi")
    col_mat1, col_mat2 = st.columns(2)
    with col_mat1: materi_manual = st.text_area("Teks Materi", height=150)
    with col_mat2: uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])

col1, col2 = st.columns([2, 1])
with col1:
    jenis_asesmen = st.selectbox("Jenis Asesmen", ["Asesmen Tengah Semester", "Asesmen Akhir Semester", "Asesmen Formatif"])
    bentuk_soal = st.multiselect("Bentuk Soal", ["Pilihan Ganda", "Benar / Salah", "Uraian"], default=["Pilihan Ganda", "Uraian"])
with col2:
    conf = {b: st.number_input(f"Jumlah {b}", 1, 30, 5) for b in bentuk_soal}

if st.button("🚀 GENERATE SEKARANG"):
    if not api_key: st.error("API Key kosong!"); st.stop()
    
    try:
        genai.configure(api_key=api_key)
        materi_full = materi_manual
        if uploaded_file:
            reader = PyPDF2.PdfReader(uploaded_file)
            materi_full += " ".join([p.extract_text() for p in reader.pages])

        is_arab = "arab" in mapel.lower()
        prompt = f"""Buat soal {mapel} untuk {jenis_asesmen}. Materi: {materi_full[:6000]}.
        Jumlah soal: {json.dumps(conf)}. {'Gunakan Bahasa Arab berharakat' if is_arab else ''}.
        PENTING: Berikan skor tiap soal agar TOTAL seluruh soal = 100.
        Format JSON: {{ "soal_list": [ {{ "tipe": "", "soal": "", "opsi": [], "kunci": "", "pedoman": "", "indikator": "", "skor": 5, "level": "L2" }} ] }}"""

        model = genai.GenerativeModel('gemini-1.5-flash')
        with st.spinner("Sedang memproses..."):
            res = model.generate_content(prompt)
            data = json.loads(clean_json_output(res.text))
            soal_list = data.get('soal_list', [])
            
            # Normalisasi Skor ke 100
            current_total = sum(q.get('skor', 0) for q in soal_list)
            if current_total > 0:
                for q in soal_list: q['skor'] = (q['skor'] / current_total) * 100

            info = {'sekolah': sekolah, 'mapel': mapel, 'kelas': kelas, 'semester': semester, 'tahun': tahun, 'jenis_asesmen': jenis_asesmen}
            st.session_state.preview_data = soal_list
            st.session_state.files = {
                'n': generate_naskah(soal_list, info),
                'kj': generate_kunci_pedoman(soal_list, info),
                'k': generate_kisi_kisi(soal_list, info),
                's': generate_kartu(soal_list, info)
            }
            st.success("Selesai!")

    except Exception as e:
        st.error(f"Gagal: {e}")

# --- 4. DOWNLOAD & PREVIEW ---
if 'files' in st.session_state:
    st.divider()
    cols = st.columns(4)
    titles = ["📄 Naskah", "🔑 Kunci", "📋 Kisi-kisi", "🗂️ Kartu"]
    keys = ['n', 'kj', 'k', 's']
    for i, k in enumerate(keys):
        buf = BytesIO(); st.session_state.files[k].save(buf)
        cols[i].download_button(titles[i], buf.getvalue(), f"{titles[i]}.docx")

    st.subheader("Preview")
    is_arab = "arab" in mapel.lower()
    for i, q in enumerate(st.session_state.preview_data):
        with st.expander(f"Soal {i+1} ({round(q['skor'],1)} pts)"):
            if is_arab: st.markdown(f"<div class='arabic-text'>{q['soal']}</div>", unsafe_allow_html=True)
            else: st.write(q['soal'])
            st.caption(f"Kunci: {q['kunci']}")
